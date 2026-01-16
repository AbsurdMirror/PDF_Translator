import os
from pathlib import Path

# 获取 server 目录的绝对路径 (server/app/core/../../)
SERVER_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = SERVER_DIR / "data"
DB_DIR = DATA_DIR / "db"
TASKS_DIR = DATA_DIR / "tasks"
LOG_DIR = SERVER_DIR / "log"

# 数据库连接 URL
DB_URL = f"sqlite:///{DB_DIR}/sql_app.db"

def init_directories():
    """初始化必要的目录"""
    DATA_DIR.mkdir(exist_ok=True)
    DB_DIR.mkdir(exist_ok=True)
    TASKS_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
