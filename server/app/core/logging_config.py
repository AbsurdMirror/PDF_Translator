import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .config import LOG_DIR, LOG_CONFIG

def setup_logging():
    """配置日志系统，使用轮转日志文件"""
    
    # 确保日志目录存在
    LOG_DIR.mkdir(exist_ok=True)
    
    # 日志文件名固定为 server.log
    log_file = LOG_DIR / "server.log"
    
    # 定义日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 获取配置
    log_level_str = LOG_CONFIG.get("level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    max_bytes = LOG_CONFIG.get("max_bytes", 10485760)
    backup_count = LOG_CONFIG.get("backup_count", 5)

    # 配置根日志记录器
    handlers = [
        # 轮转文件处理器
        RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        ),
        # 控制台处理器
        logging.StreamHandler(sys.stdout)
    ]

    # 使用 force=True 确保覆盖之前的配置 (如 uvicorn 默认配置)
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )
    
    # 获取 logger 并记录启动信息
    logger = logging.getLogger("app")
    logger.info(f"Logging initialized. Level: {log_level_str}, Log file: {log_file}")

    # 确保 uvicorn 日志也输出到这些 handler
    # 强制 uvicorn 日志传播到根 logger
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        log = logging.getLogger(logger_name)
        log.handlers = []  # 移除 uvicorn 默认的 handler
        log.propagate = True
    
    # 调整第三方库的日志级别
    # 如果全局不是 DEBUG，则抑制 noisy libraries
    if log_level > logging.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        # alibabacloud libraries can be verbose
        logging.getLogger("alibabacloud").setLevel(logging.WARNING)
    
    return logger
