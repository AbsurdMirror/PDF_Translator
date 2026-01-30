from pydantic import BaseModel
from typing import List, Optional

class TranslationConfig(BaseModel):
    sourceLang: str
    targetLang: str
    pageRange: str
    quality: str

class TranslationTask(BaseModel):
    taskId: str
    filename: str
    status: str
    parseProgress: int
    translateProgress: int
    createTime: str
    message: Optional[str] = None

class TaskResponse(BaseModel):
    taskId: str
    status: str

class ProgressResponse(BaseModel):
    parseProgress: int
    translateProgress: int
    status: str
    message: str

class TaskListResponse(BaseModel):
    tasks: List[TranslationTask]

class SystemConfig(BaseModel):
    aliyunAccessKeyId: str = ""
    aliyunAccessKeySecret: str = ""
    aliyunRegion: str = ""
    aliyunEndpoint: str = "https://docmind-api.cn-hangzhou.aliyuncs.com"
    llmApiKey: str = ""
    llmModel: str = ""
    llmEndpoint: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

class TaskResultUpdate(BaseModel):
    index: int
    markdownContent: str

class TranslationSubmit(BaseModel):
    taskId: str
