from sqlalchemy import Column, Integer, String, DateTime, Float
from ..core.database import Base
from datetime import datetime

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    filename = Column(String)
    file_path = Column(String)  # 原始文件存储路径
    status = Column(String, default="pending")
    parse_progress = Column(Integer, default=0)
    translate_progress = Column(Integer, default=0)
    message = Column(String, nullable=True)
    source_lang = Column(String, default="English")
    target_lang = Column(String, default="Chinese")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class Config(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, index=True)
    aliyun_access_key_id = Column(String, default="")
    aliyun_access_key_secret = Column(String, default="")
    aliyun_region = Column(String, default="")
    aliyun_endpoint = Column(String, default="https://docmind-api.cn-hangzhou.aliyuncs.com")
    llm_api_key = Column(String, default="")
    llm_model = Column(String, default="")
    llm_endpoint = Column(String, default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    translation_engine = Column(String, default="llm")  # llm or aliyun
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
