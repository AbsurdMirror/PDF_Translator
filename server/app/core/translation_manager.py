# -*- coding: utf-8 -*-
import os
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from ..core.database import SessionLocal
from ..models.sql_models import Task, Config
from ..core.layout_translator import LayoutTranslator

logger = logging.getLogger(__name__)


class TranslationManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TranslationManager, cls).__new__(cls)
                    cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="TranslateWorker")
        self.active_tasks = {}
        self.stop_event = threading.Event()
        self.initialized = True

    def submit_task(self, task_id: str):
        if self.stop_event.is_set():
            logger.warning(f"Cannot submit task {task_id}: manager is stopping")
            return

        if task_id in self.active_tasks and not self.active_tasks[task_id].done():
            logger.warning(f"Task {task_id} is already running")
            return

        future = self.executor.submit(self._execute_task, task_id)
        self.active_tasks[task_id] = future
        logger.info(f"Task {task_id} submitted to pool")

    def stop_all(self):
        """Stops all running translation tasks."""
        logger.info("Stopping all translation tasks...")
        self.stop_event.set()
        try:
            # cancel_futures is available in Python 3.9+
            self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            self.executor.shutdown(wait=False)

        # Clear active tasks tracking
        self.active_tasks.clear()

    def _execute_task(self, task_id: str):
        if self.stop_event.is_set():
            logger.info(f"Task {task_id} skipped due to shutdown")
            return

        logger.info(f"Starting translation for task {task_id}")
        db = SessionLocal()
        task: Optional[Task] = None
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return

            if (task.parse_progress or 0) < 100:
                logger.warning(f"Task {task_id} parse not finished: parse_progress={task.parse_progress}")
                task.status = "failed"
                task.message = "解析未完成，无法开始翻译"
                db.commit()
                return

            config = db.query(Config).first()
            if not config:
                logger.warning(f"Task {task_id} missing config")
                task.status = "failed"
                task.message = "系统配置缺失"
                db.commit()
                return

            translation_engine = config.translation_engine or "llm"
            if translation_engine == "llm":
                if not config.llm_api_key:
                    logger.warning(f"Task {task_id} missing LLM config")
                    task.status = "failed"
                    task.message = "系统配置缺失 (请在设置页面配置 LLM API Key)"
                    db.commit()
                    return
            elif translation_engine == "aliyun":
                if not config.aliyun_access_key_id or not config.aliyun_access_key_secret:
                    logger.warning(f"Task {task_id} missing Aliyun MT config")
                    task.status = "failed"
                    task.message = "系统配置缺失 (请在设置页面配置阿里云 Access Key)"
                    db.commit()
                    return

            output_dir = os.path.dirname(task.file_path)
            yaml_path = os.path.join(output_dir, "parse_result.yaml")
            if not os.path.exists(yaml_path):
                logger.warning(f"Task {task_id} parse_result.yaml not found: {yaml_path}")
                task.status = "failed"
                task.message = "未找到解析结果 parse_result.yaml"
                db.commit()
                return

            task.status = "processing"
            task.translate_progress = 0
            task.message = "正在加载解析结果..."
            db.commit()

            data, layouts = self._load_yaml_layouts(yaml_path)
            total = len(layouts)
            logger.info(f"Task {task_id} loaded layouts: total={total}, yaml={yaml_path}")

            source_lang = self._normalize_lang(task.source_lang or "English")
            target_lang = self._normalize_lang(task.target_lang or "Chinese")

            model = config.llm_model or "qwen-mt-flash"
            base_url = config.llm_endpoint or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            logger.info(
                f"Task {task_id} translation config: engine={translation_engine}, model={model}, base_url={base_url}, source_lang={source_lang}, target_lang={target_lang}"
            )

            translator = LayoutTranslator(
                api_key=config.llm_api_key,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model,
                base_url=base_url,
                translation_engine=translation_engine,
                aliyun_access_key_id=config.aliyun_access_key_id,
                aliyun_access_key_secret=config.aliyun_access_key_secret,
                debug_output_path=os.path.join(output_dir, "layout_translator_debug.log"),
                debug=True
            )

            def on_item(idx: int, result: str, skipped: bool):
                try:
                    if total > 0:
                        progress = int(((idx + 1) / total) * 100)
                    else:
                        progress = 100

                    task.translate_progress = min(100, max(0, progress))
                    if skipped:
                        task.message = f"已跳过 {idx + 1}/{total}"
                    else:
                        task.message = f"翻译中 {idx + 1}/{total}"
                    db.commit()

                    self._save_yaml_layouts(yaml_path, data, layouts)
                except Exception as e:
                    logger.error(f"Error in translation callback for task {task_id}: {e}")

            translation_ok = True
            finish_info: Dict[str, Any] = {}

            def on_finish(cb_task_id: Optional[str], status: str, info: Dict[str, Any]):
                nonlocal translation_ok, finish_info
                finish_info = info or {}
                if status == "stopped":
                    translation_ok = False
                    logger.info(f"Task {task_id} translation stopped")
                    task.status = "failed" # or specific status if supported
                    task.message = "任务已停止"
                    db.commit()
                elif status != "success":
                    translation_ok = False
                    err = finish_info.get("error") or "翻译失败"
                    logger.error(f"Task {task_id} translation finished with failure: {err}")
                    task.status = "failed"
                    task.message = str(err)
                    db.commit()
                else:
                    logger.info(f"Task {task_id} translation finished successfully: {finish_info}")

            translator.translate_layouts(layouts, task_id=task_id, on_item=on_item, on_finish=on_finish, stop_event=self.stop_event)
            self._save_yaml_layouts(yaml_path, data, layouts)

            if not translation_ok:
                logger.error(f"Task {task_id} translation failed: {finish_info}")
                return

            task.status = "completed"
            task.translate_progress = 100
            task.message = "翻译完成"
            db.commit()
            logger.info(f"Task {task_id} translation completed")
        except Exception as e:
            logger.error(f"Translation execution exception for {task_id}: {e}", exc_info=True)
            try:
                if task is not None:
                    task.status = "failed"
                    task.message = f"内部错误: {str(e)}"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def _normalize_lang(self, lang: str) -> str:
        val = (lang or "").strip()
        if val == "":
            return "auto"

        low = val.lower().replace("_", "-")
        if low in {"auto"}:
            return "auto"
        if low in {"zh", "zh-cn", "zh-hans", "chinese", "中文"}:
            return "Chinese"
        if low in {"en", "en-us", "english"}:
            return "English"
        return val

    def _load_yaml_layouts(self, yaml_path: str) -> Tuple[Union[Dict, List], List[Dict[str, Any]]]:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict):
            layouts = data.get("layouts", [])
            if layouts is None:
                layouts = []
            if not isinstance(layouts, list):
                raise ValueError("YAML 的 layouts 字段不是数组")
            return data, layouts

        if isinstance(data, list):
            return data, data

        raise ValueError("YAML 根节点必须是 dict 或 list")

    def _save_yaml_layouts(self, yaml_path: str, data: Union[Dict, List], layouts: List[Dict[str, Any]]) -> None:
        if isinstance(data, dict):
            data["layouts"] = layouts
            to_write: Union[Dict, List] = data
        else:
            to_write = layouts

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(to_write, f, allow_unicode=True, sort_keys=False)


translation_manager = TranslationManager()
