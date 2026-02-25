import os
import json
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

def get_logging_config():
    """Reads logging configuration from package.json"""
    default_config = {
        "level": "INFO",
        "max_bytes": 10485760, # 10MB
        "backup_count": 5
    }

    try:
        package_json_path = SERVER_DIR.parent / "package.json"
        if package_json_path.exists():
            with open(package_json_path, "r", encoding="utf-8") as f:
                package_data = json.load(f)
                logging_config = package_data.get("logging", {})

                # Merge with defaults
                config = default_config.copy()
                config.update(logging_config)
                return config
    except Exception as e:
        print(f"Warning: Failed to read package.json logging config: {e}")

    return default_config

LOG_CONFIG = get_logging_config()
