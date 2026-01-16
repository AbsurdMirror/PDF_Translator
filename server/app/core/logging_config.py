import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from .config import LOG_DIR

def setup_logging():
    """配置日志系统，每次启动生成新的日志文件"""
    
    # 确保日志目录存在
    LOG_DIR.mkdir(exist_ok=True)
    
    # 生成日志文件名：server_YYYY-MM-DD_HH-MM-SS.log
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = LOG_DIR / f"server_{timestamp}.log"
    
    # 定义日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 文件处理器：写入日志文件，编码为 utf-8
            logging.FileHandler(log_file, encoding='utf-8'),
            # 控制台处理器：输出到标准输出
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 获取 logger 并记录启动信息
    logger = logging.getLogger("app")
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    # 调整第三方库的日志级别，避免刷屏
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return logger
