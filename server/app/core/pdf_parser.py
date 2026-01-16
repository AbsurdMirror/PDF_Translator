# -*- coding: utf-8 -*-
import os
import json
import time
import threading
from typing import Dict, List, Optional, Callable
from alibabacloud_docmind_api20220711.client import Client as docmind_api20220711Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_docmind_api20220711 import models as docmind_api20220711_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredClient

import logging

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self, 
                 task_id: str,
                 file_path: str,
                 output_path: str,
                 endpoint: str = "docmind-api.cn-hangzhou.aliyuncs.com", 
                 access_key_id: Optional[str] = None, 
                 access_key_secret: Optional[str] = None, 
                 debug: bool = False, 
                 debug_output_path: str = "debug.log", 
                 layout_step_size: int = 10,
                 on_update: Optional[Callable] = None,
                 on_data: Optional[Callable] = None,
                 on_finish: Optional[Callable] = None):
        """
        初始化PDF解析器
        
        Args:
            file_path (str): PDF文件路径
            output_path (str): 输出结果路径
            endpoint (str): API端点地址
            access_key_id (str, optional): 阿里云 AccessKey ID
            access_key_secret (str, optional): 阿里云 AccessKey Secret
            debug (bool): 是否开启调试模式
            debug_output_path (str): 调试信息输出路径
            layout_step_size (int): 增量获取结果的步长
            on_update (callable, optional): 状态更新回调, signature: (task_id, old_status, new_status, processing)
            on_data (callable, optional): 数据更新回调, signature: (task_id, new_layouts)
            on_finish (callable, optional): 任务结束回调, signature: (task_id, status, result_info)
        """
        self.file_path = file_path
        self.output_path = output_path
        self.endpoint = endpoint
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.debug = debug
        self.debug_output_path = debug_output_path
        self.layout_step_size = layout_step_size
        
        # 回调函数
        self._on_update_callback = on_update
        self._on_data_callback = on_data
        self._on_finish_callback = on_finish
        
        # 初始化客户端
        self.client = self._init_client()
        
        # 单任务状态管理
        self.task_id = task_id
        self.task_status = "idle"  # idle, init, processing, success, fail
        self.total_layout_num = 0       # 从服务端获取的总解析成功数量
        self.processed_layout_num = 0   # 本地已处理（获取）的数量
        self.all_layouts = []           # 存储所有获取到的布局
        
        # 线程控制
        self._stop_event = threading.Event()

    def run(self, interval=5, stop_event: Optional[threading.Event] = None):
        """
        同步运行任务解析流程（阻塞直到完成或停止）
        注意：此方法会阻塞当前线程，请确保在独立的子线程中调用
        
        Args:
            interval (int): 轮询间隔（秒）
            stop_event (threading.Event, optional): 外部传入的停止事件，用于从外部中断任务
        """
        self._stop_event.clear()
        
        try:
            # 直接执行主逻辑，不创建新线程
            self._run_task_sync(interval, stop_event)
        except KeyboardInterrupt:
            logger.info(f"任务 {self.task_id} 收到键盘中断，正在停止...")
            self.stop()
            # 再次抛出异常，以便上层也能捕获（如果是主线程直接运行）
            raise

    def stop(self):
        """发送停止信号"""
        self._stop_event.set()
        logger.info("任务已收到停止信号")

    def _init_client(self):
        """初始化API客户端"""
        config = open_api_models.Config(endpoint=self.endpoint)
        if self.access_key_id and self.access_key_secret:
            config.access_key_id = self.access_key_id
            config.access_key_secret = self.access_key_secret
            config.type = "access_key"
        else:
            cred = CredClient()
            try:
                config.access_key_id = cred.get_credential().get_access_key_id()
                config.access_key_secret = cred.get_credential().get_access_key_secret()
            except Exception:
                pass
        return docmind_api20220711Client(config)

    def _run_task_sync(self, interval, external_stop_event=None):
        """任务主流程（同步阻塞）"""
        # 1. 提交任务
        task_id = self._submit_job()
        if not task_id:
            # 提交失败，触发回调（如果需要）或直接结束
            if self._on_finish_callback:
                self._on_finish_callback(None, "fail", {"error": "Submit failed"})
            return

        self.task_id = task_id
        self.task_status = "init"
        
        # 2. 轮询状态与结果
        while not self._stop_event.is_set():
            # 检查外部停止信号
            if external_stop_event and external_stop_event.is_set():
                logger.info(f"任务 {task_id} 检测到外部停止信号，正在停止...")
                self.stop()
                break

            try:
                finished = self._update_and_fetch()
                if finished:
                    break
            except Exception as e:
                logger.error(f"轮询过程出错: {e}")
                
            # 使用 wait 代替 sleep，支持响应 stop()
            self._stop_event.wait(interval)

    def _submit_job(self) -> Optional[str]:
        """提交PDF解析任务"""
        try:
            file_name = os.path.basename(self.file_path)
            extension = file_name.split('.')[-1] if '.' in file_name else None
            
            request = docmind_api20220711_models.SubmitDocParserJobAdvanceRequest(
                file_url_object=open(self.file_path, "rb"),
                file_name=file_name,
                file_name_extension=extension,
                llm_enhancement=True,
                enhancement_mode="VLM",
            )
            runtime = util_models.RuntimeOptions()
            
            response = self.client.submit_doc_parser_job_advance(request, runtime)
            self._log_http_debug("submit_doc_parser_job_advance", request, response)
            
            task_id = response.body.data.id
            logger.info(f"任务已提交: {file_name}, ID: {task_id}")
            return task_id
            
        except Exception as error:
            logger.error(f"提交任务失败 {self.file_path}: {error}")
            self._log_http_debug("submit_doc_parser_job_advance", request if 'request' in locals() else None, error=error)
            return None

    def _update_and_fetch(self) -> bool:
        """更新状态并增量获取结果，返回是否完成"""
        task_id = self.task_id
        if not task_id: return True

        # 1. 查询状态
        status, num_successful, processing = self._check_status(task_id)
        
        if num_successful >= self.total_layout_num:
            self.total_layout_num = num_successful
        
        current_status = self.task_status
        # 状态变化或处理进度变化时触发回调
        if status != current_status or status == 'processing':
            self.task_status = status
            if self._on_update_callback:
                self._on_update_callback(task_id, current_status, status, processing)

        # 2. 增量获取结果
        while True:
            if self.processed_layout_num >= self.total_layout_num:
                break
            start_num = self.processed_layout_num
            step = self.layout_step_size
        
            layouts = self._get_result(task_id, start_num, step)
            logger.debug(f"processed_layout_num: {self.processed_layout_num}, total_layout_num: {self.total_layout_num}")

            if not layouts: break
            
            self.processed_layout_num += len(layouts)
            self.all_layouts.extend(layouts)
            
            if self._on_data_callback:
                self._on_data_callback(task_id, layouts)
            
            if len(layouts) < step: break

        # 3. 检查完成
        is_success = (self.task_status == 'success' and self.processed_layout_num >= self.total_layout_num)
        is_fail = (self.task_status == 'fail')
        
        if is_success:
            logger.info(f"任务 {task_id} 完成，共获取 {self.processed_layout_num} 个布局")
            if self._on_finish_callback:
                self._on_finish_callback(task_id, "success", {
                    "status": "success",
                    "output_path": self.output_path,
                    "total_layouts": self.processed_layout_num
                })
            return True
        elif is_fail:
            logger.error(f"任务 {task_id} 失败")
            if self._on_finish_callback:
                self._on_finish_callback(task_id, "fail", {"error": "Task failed"})
            return True
            
        return False

    def _check_status(self, task_id: str):
        """内部查询状态"""
        try:
            request = docmind_api20220711_models.QueryDocParserStatusRequest(id=task_id)
            response = self.client.query_doc_parser_status(request)
            self._log_http_debug("query_doc_parser_status", request, response)
            
            data = response.body.data
            status = data.status if data else "fail"
            num = getattr(data, 'number_of_successful_parsing', 0) if data else 0
            processing = getattr(data, 'processing', 0.0) if data else 0.0
            
            if status not in ["init", "processing", "success", "fail"]:
                status = "fail"
            return status, num, processing
        except Exception as e:
            self._log_http_debug("query_doc_parser_status", None, error=e)
            return "fail", 0, 0.0

    def _get_result(self, task_id: str, start_num: int, step: int) -> List[dict]:
        """内部获取结果"""
        try:
            request = docmind_api20220711_models.GetDocParserResultRequest(
                id=task_id, layout_step_size=step, layout_num=start_num
            )
            response = self.client.get_doc_parser_result(request)
            self._log_http_debug("get_doc_parser_result", request, response)
            return response.body.data['layouts'] if (response.body.data and response.body.data['layouts']) else []
        except Exception as e:
            self._log_http_debug("get_doc_parser_result", request if 'request' in locals() else None, error=e)
            return []

    def _log_http_debug(self, action: str, req: any, resp: any = None, error: any = None):
        """记录调试日志"""
        if not self.debug: return
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            # 简化版日志记录，只记录关键信息避免过大
            content = f"[{timestamp}] {action} "
            if error: content += f"ERROR: {error}"
            elif resp: content += "SUCCESS"
            
            with open(self.debug_output_path, 'a', encoding='utf-8') as f:
                f.write(content + "\n")
        except Exception as e: 
            logger.error(f"Error logging debug: {e}")
