# -*- coding: utf-8 -*-
import threading
import os
import logging
import yaml
import requests
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor

from ..core.database import SessionLocal
from ..models.sql_models import Task, Config
from ..core.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class PDFParseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(PDFParseManager, cls).__new__(cls)
                    cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PDFParseWorker")
        self.active_tasks = {}
        self.active_parsers = {}
        self.initialized = True
        self.stop_requested = False

    def submit_task(self, task_id: str):
        if self.stop_requested:
            logger.warning(f"Cannot submit task {task_id}: manager is stopping")
            return

        if task_id in self.active_tasks and not self.active_tasks[task_id].done():
            logger.warning(f"Task {task_id} is already running")
            return

        future = self.executor.submit(self._execute_task, task_id)
        self.active_tasks[task_id] = future
        logger.info(f"Task {task_id} submitted to pool")

    def stop_all(self):
        """Stops all running PDF parse tasks."""
        self.stop_requested = True
        logger.info("Stopping all PDF parse tasks...")
        for task_id, parser in list(self.active_parsers.items()):
            try:
                parser.stop()
            except Exception as e:
                logger.error(f"Error stopping parser {task_id}: {e}")

        try:
             # cancel_futures is available in Python 3.9+
             self.executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
             self.executor.shutdown(wait=False)

        self.active_tasks.clear()
        self.active_parsers.clear()

    def _execute_task(self, task_id: str):
        if self.stop_requested:
            logger.info(f"Task {task_id} skipped due to shutdown")
            return

        logger.info(f"Starting execution for task {task_id}")
        db = SessionLocal()
        task = None
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return

            config = db.query(Config).first()
            if not config or not config.aliyun_access_key_id or not config.aliyun_access_key_secret:
                logger.warning(f"Task {task_id} missing Aliyun AccessKey config")
                task.status = "failed"
                task.message = "系统配置缺失 (请在设置页面配置阿里云AccessKey)"
                db.commit()
                return

            task.status = "processing"
            task.message = "正在初始化解析器..."
            task.parse_progress = 0
            db.commit()

            output_dir = os.path.dirname(task.file_path)
            output_filename = "parse_result.yaml"
            output_path = os.path.join(output_dir, output_filename)
            figures_dir = os.path.join(output_dir, "figures")
            logger.info(
                f"Task {task_id} parse paths: file={task.file_path}, output={output_path}, figures_dir={figures_dir}"
            )

            def on_update(tid, old_status, new_status, processing):
                try:
                    logger.debug(
                        f"Task {tid} parser status update: {old_status} -> {new_status}, processing={processing}"
                    )
                    if new_status == "processing":
                        task.status = "processing"
                        cloud_percent = float(processing)
                        task.parse_progress = min(85, max(0, int(cloud_percent * 0.85)))
                        task.message = f"云端解析中... {processing}%"
                    elif new_status == "success":
                        if task.parse_progress < 85:
                            task.parse_progress = 85
                        task.message = "云端解析完成，正在拉取结果..."
                    elif new_status == "fail":
                        task.status = "failed"
                        task.message = "云端解析失败"

                    db.commit()
                except Exception as e:
                    logger.error(f"Error updating status callback: {e}", exc_info=True)

            def on_data(tid, new_layouts):
                try:
                    logger.debug(f"Task {tid} received layouts: count={len(new_layouts or [])}")
                    if not os.path.exists(figures_dir):
                        os.makedirs(figures_dir, exist_ok=True)

                    for layout in new_layouts:
                        if layout.get("type") == "figure":
                            content = layout.get("markdownContent", "")
                            if not content:
                                continue

                            matches = re.findall(r"!\[(.*?)\]\((.*?)\)", content)
                            for filename, url in matches:
                                if url.startswith("http"):
                                    try:
                                        safe_filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                                        if not safe_filename:
                                            safe_filename = (
                                                f"figure_{int(time.time() * 1000)}_{random.randint(0, 1000)}.png"
                                            )

                                        local_path = os.path.join(figures_dir, safe_filename)
                                        resp = requests.get(url, stream=True, timeout=30)
                                        if resp.status_code == 200:
                                            with open(local_path, "wb") as f:
                                                for chunk in resp.iter_content(1024):
                                                    f.write(chunk)

                                            rel_path = f"/api/task/{task_id}/figures/{safe_filename}"
                                            layout["markdownContent"] = layout["markdownContent"].replace(url, rel_path)
                                            logger.info(f"Downloaded figure {safe_filename} for task {tid}")
                                        else:
                                            logger.warning(
                                                f"Failed to download figure {url}: status {resp.status_code}"
                                            )
                                    except Exception as e:
                                        logger.error(f"Error downloading figure {url}: {e}", exc_info=True)

                    if parser.total_layout_num > 0 and task.parse_progress >= 85:
                        ratio = parser.processed_layout_num / parser.total_layout_num
                        percent = 85 + int(ratio * 15)
                        task.parse_progress = min(100, max(85, percent))
                        task.message = f"正在保存结果 {parser.processed_layout_num}/{parser.total_layout_num} 页"
                        db.commit()

                    result_data = {
                        "task_id": task_id,
                        "layouts": parser.all_layouts,
                        "total": parser.total_layout_num,
                    }
                    with open(output_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump(result_data, f, allow_unicode=True, sort_keys=False)
                    logger.debug(
                        f"Task {tid} wrote parse_result.yaml: output={output_path}, total_layouts={parser.total_layout_num}, processed={parser.processed_layout_num}"
                    )
                except Exception as e:
                    logger.error(f"Error updating data callback: {e}", exc_info=True)

            endpoint = config.aliyun_endpoint or "docmind-api.cn-hangzhou.aliyuncs.com"
            if endpoint.startswith("https://"):
                endpoint = endpoint[8:]
            elif endpoint.startswith("http://"):
                endpoint = endpoint[7:]
            logger.info(f"Task {task_id} parser endpoint: {endpoint}")

            parser = PDFParser(
                task_id=task_id,
                file_path=task.file_path,
                output_path=output_path,
                access_key_id=config.aliyun_access_key_id,
                access_key_secret=config.aliyun_access_key_secret,
                endpoint=endpoint,
                on_update=on_update,
                on_data=on_data,
                debug_output_path=os.path.join(output_dir, "pdf_parser_debug.log"),
                debug=True
            )

            self.active_parsers[task_id] = parser

            logger.info(f"Running parser for {task_id}")
            try:
                parser.run()
            finally:
                if task_id in self.active_parsers:
                    del self.active_parsers[task_id]

            logger.info(
                f"Task {task_id} parser run finished: status={parser.task_status}, total={parser.total_layout_num}, processed={parser.processed_layout_num}"
            )

            if parser.task_status == "success":
                result_data = {
                    "task_id": task_id,
                    "layouts": parser.all_layouts,
                    "total": parser.total_layout_num,
                }
                with open(output_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(result_data, f, allow_unicode=True, sort_keys=False)

                task.status = "completed"
                task.parse_progress = 100
                task.message = "解析完成"
                db.commit()
                logger.info(f"Task {task_id} completed successfully")
            else:
                task.status = "failed"
                if task.message == "正在云端解析中..." or not task.message:
                    task.message = "解析失败"
                db.commit()
                logger.error(f"Task {task_id} failed with status {parser.task_status}")
        except Exception as e:
            logger.error(f"Task execution exception for {task_id}: {e}", exc_info=True)
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


pdf_parse_manager = PDFParseManager()
