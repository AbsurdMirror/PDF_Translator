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
        self.initialized = True

    def submit_task(self, task_id: str):
        if task_id in self.active_tasks and not self.active_tasks[task_id].done():
            logger.warning(f"Task {task_id} is already running")
            return

        future = self.executor.submit(self._execute_task, task_id)
        self.active_tasks[task_id] = future
        logger.info(f"Task {task_id} submitted to pool")

    def _execute_task(self, task_id: str):
        logger.info(f"Starting execution for task {task_id}")
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return

            config = db.query(Config).first()
            if not config or not config.aliyun_access_key_id or not config.aliyun_access_key_secret:
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

            def on_update(tid, old_status, new_status, processing):
                try:
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
                    logger.error(f"Error updating status callback: {e}")

            def on_data(tid, new_layouts):
                try:
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
                                        logger.error(f"Error downloading figure {url}: {e}")

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
                except Exception as e:
                    logger.error(f"Error updating data callback: {e}")

            endpoint = config.aliyun_endpoint or "docmind-api.cn-hangzhou.aliyuncs.com"
            if endpoint.startswith("https://"):
                endpoint = endpoint[8:]
            elif endpoint.startswith("http://"):
                endpoint = endpoint[7:]

            parser = PDFParser(
                task_id=task_id,
                file_path=task.file_path,
                output_path=output_path,
                access_key_id=config.aliyun_access_key_id,
                access_key_secret=config.aliyun_access_key_secret,
                endpoint=endpoint,
                on_update=on_update,
                on_data=on_data,
            )

            logger.info(f"Running parser for {task_id}")
            parser.run()

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

