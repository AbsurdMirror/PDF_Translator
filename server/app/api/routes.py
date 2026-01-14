from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import time
import random
from pathlib import Path
from datetime import datetime

from ..models.schemas import (
    TranslationConfig, 
    TaskResponse, 
    ProgressResponse, 
    TaskListResponse,
    TranslationTask,
    SystemConfig
)
from ..models.sql_models import Task, Config
from ..core.database import get_db
from ..core.config import TASKS_DIR
from ..core.task_manager import task_manager

router = APIRouter()

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # 生成任务 ID
        task_id = f"task_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        # 创建任务目录
        task_dir = TASKS_DIR / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = task_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 创建数据库记录
        new_task = Task(
            task_id=task_id,
            filename=file.filename,
            file_path=str(file_path),
            status="pending",
            progress=0,
            message="等待开始...",
            created_at=datetime.now()
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        
        # 提交任务到任务池
        task_manager.submit_task(task_id)
        
        return {"taskId": task_id, "status": "pending"}
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{task_id}")
async def get_progress(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "progress": task.progress,
        "status": task.status,
        "message": task.message or ""
    }

@router.get("/translations")
async def get_translations(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    
    # 转换为前端需要的格式
    result = []
    for task in tasks:
        result.append({
            "taskId": task.task_id,
            "filename": task.filename,
            "status": task.status,
            "progress": task.progress,
            "createTime": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "message": task.message
        })
        
    return {"tasks": result}

@router.get("/download/{task_id}")
async def download_translation(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="翻译未完成")
        
    # TODO: 实现真实的文件下载逻辑
    # 目前先返回一个简单的模拟响应，或者返回原始文件（如果需要测试）
    mock_content = f"这是翻译后的PDF内容\n任务ID: {task.task_id}\n文件名: {task.filename}"
    
    headers = {
        'Content-Disposition': f'attachment; filename="{task.filename.replace(".pdf", "_translated.pdf")}"'
    }
    return Response(content=mock_content, media_type="application/pdf", headers=headers)

@router.get("/config", response_model=SystemConfig)
async def get_config(db: Session = Depends(get_db)):
    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
        db.commit()
        db.refresh(config)
    
    return {
        "aliyunAccessKeyId": config.aliyun_access_key_id,
        "aliyunAccessKeySecret": config.aliyun_access_key_secret,
        "aliyunRegion": config.aliyun_region,
        "aliyunEndpoint": config.aliyun_endpoint,
        "llmApiKey": config.llm_api_key,
        "llmModel": config.llm_model,
        "llmEndpoint": config.llm_endpoint
    }

@router.post("/config", response_model=SystemConfig)
async def update_config(config_in: SystemConfig, db: Session = Depends(get_db)):
    config = db.query(Config).first()
    if not config:
        config = Config()
        db.add(config)
    
    config.aliyun_access_key_id = config_in.aliyunAccessKeyId
    config.aliyun_access_key_secret = config_in.aliyunAccessKeySecret
    config.aliyun_region = config_in.aliyunRegion
    config.aliyun_endpoint = config_in.aliyunEndpoint
    config.llm_api_key = config_in.llmApiKey
    config.llm_model = config_in.llmModel
    config.llm_endpoint = config_in.llmEndpoint
    
    db.commit()
    db.refresh(config)
    
    return {
        "aliyunAccessKeyId": config.aliyun_access_key_id,
        "aliyunAccessKeySecret": config.aliyun_access_key_secret,
        "aliyunRegion": config.aliyun_region,
        "aliyunEndpoint": config.aliyun_endpoint,
        "llmApiKey": config.llm_api_key,
        "llmModel": config.llm_model,
        "llmEndpoint": config.llm_endpoint
    }
