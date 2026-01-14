# -*- coding: utf-8 -*-
import threading
import os
import json
import logging
import yaml
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from ..core.database import SessionLocal
from ..models.sql_models import Task, Config
from ..core.pdf_parser import PDFParser

logger = logging.getLogger(__name__)

class TaskManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TaskManager, cls).__new__(cls)
                    cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        # 创建线程池，最大并发数设为2
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PDFWorker")
        self.active_tasks = {}
        self.initialized = True

    def submit_task(self, task_id: str):
        """提交任务到线程池"""
        if task_id in self.active_tasks and not self.active_tasks[task_id].done():
            logger.warning(f"Task {task_id} is already running")
            return
            
        future = self.executor.submit(self._execute_task, task_id)
        self.active_tasks[task_id] = future
        logger.info(f"Task {task_id} submitted to pool")
    
    def _execute_task(self, task_id: str):
        """任务执行逻辑"""
        logger.info(f"Starting execution for task {task_id}")
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return
            
            # 获取配置
            config = db.query(Config).first()
            if not config or not config.aliyun_access_key_id or not config.aliyun_access_key_secret:
                task.status = "failed"
                task.message = "系统配置缺失 (请在设置页面配置阿里云AccessKey)"
                db.commit()
                return

            # 更新状态为处理中
            task.status = "processing"
            task.message = "正在初始化解析器..."
            task.progress = 5
            db.commit()

            # 准备解析器变量
            # 注意：这里我们通过闭包在回调中使用 db 和 task
            # 因为是同步执行，不会有并发修改同一个 session 的问题
            
            def on_update(tid, old_status, new_status, processing):
                try:
                    if new_status == 'processing':
                        task.status = 'processing'
                        progress_val = float(processing)
                        progress_val = progress_val / 100.0
                        
                        # 阶段1：云端解析 (5% - 85%)
                        current_p = 5 + int(progress_val * 80)
                        task.progress = min(85, current_p)
                        task.message = f"云端解析中... {processing}%"
                        
                    elif new_status == 'success':
                        # 阶段2：准备拉取 (85%)
                        if task.progress < 85:
                            task.progress = 85
                        task.message = "云端解析完成，正在拉取结果..."
                        
                    elif new_status == 'fail':
                        task.status = 'failed'
                        task.message = "云端解析失败"
                    
                    db.commit()
                except Exception as e:
                    logger.error(f"Error updating status callback: {e}")

            def on_data(tid, new_layouts):
                try:
                    # 阶段3：拉取并保存结果 (85% - 95%)
                    if parser.total_layout_num > 0 and task.progress >= 85:
                        ratio = parser.processed_layout_num / parser.total_layout_num
                        percent = 85 + int(ratio * 10)
                        task.progress = min(95, percent)
                        task.message = f"正在保存结果 {parser.processed_layout_num}/{parser.total_layout_num} 页"
                        db.commit()
                except Exception as e:
                    logger.error(f"Error updating data callback: {e}")

            # 准备输出路径
            output_dir = os.path.dirname(task.file_path)
            output_filename = os.path.splitext(os.path.basename(task.file_path))[0] + "_result.yaml"
            output_path = os.path.join(output_dir, output_filename)

            # 处理 Endpoint，去除协议头
            endpoint = config.aliyun_endpoint or "docmind-api.cn-hangzhou.aliyuncs.com"
            if endpoint.startswith("https://"):
                endpoint = endpoint[8:]
            elif endpoint.startswith("http://"):
                endpoint = endpoint[7:]

            # 初始化解析器
            parser = PDFParser(
                task_id=task_id,
                file_path=task.file_path,
                output_path=output_path,
                access_key_id=config.aliyun_access_key_id,
                access_key_secret=config.aliyun_access_key_secret,
                endpoint=endpoint,
                on_update=on_update,
                on_data=on_data
            )

            # 运行解析
            logger.info(f"Running parser for {task_id}")
            parser.run()

            # 检查最终状态
            if parser.task_status == 'success':
                # 保存结果到文件
                result_data = {
                    "task_id": task_id,
                    "layouts": parser.all_layouts,
                    "total": parser.total_layout_num
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(result_data, f, allow_unicode=True, sort_keys=False)
                
                task.status = "completed"
                task.progress = 100
                task.message = "解析完成"
                db.commit()
                logger.info(f"Task {task_id} completed successfully")
            else:
                task.status = "failed"
                # 如果 message 还没被设置成错误信息
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
            except:
                pass
        finally:
            db.close()
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

# 全局单例
task_manager = TaskManager()
