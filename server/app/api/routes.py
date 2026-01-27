from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, Response, FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import time
import random
import yaml
from pathlib import Path
from datetime import datetime

from ..models.schemas import (
    TranslationConfig, 
    TaskResponse, 
    ProgressResponse, 
    TaskListResponse,
    TranslationTask,
    SystemConfig,
    TaskResultUpdate
)
from ..models.sql_models import Task, Config
from ..core.database import get_db
from ..core.config import TASKS_DIR
from ..core.task_manager import task_manager

import logging
logger = logging.getLogger(__name__)

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
        logger.error(f"Upload error: {e}")
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

@router.get("/task/{task_id}/figures/{filename}")
async def get_task_figure(task_id: str, filename: str):
    task_dir = TASKS_DIR / task_id
    file_path = task_dir / "figures" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
        
    return FileResponse(file_path)

@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    task_dir = TASKS_DIR / task_id
    yaml_path = task_dir / "parse_result.yaml"

    logger.info(f"Reading yaml file: {yaml_path}")
    logger.info(f"File exists: {yaml_path.exists()}")

    if not yaml_path.exists():
        # 如果文件不存在，可能是还在处理中或者任务失败，或者只是没有yaml文件
        # 这里返回一个空列表或者特定的错误信息
        # 为了前端友好，这里返回空列表，但也可以根据实际情况调整
        logger.warning(f"Result file not found: {yaml_path}")
        return []

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        layouts = data.get("layouts", [])
        result = []
        for idx, item in enumerate(layouts):
            result.append({
                "index": idx,
                "type": item.get("type"),
                "subType": item.get("subType"),
                "markdownContent": item.get("markdownContent"),
                "pageNum": item.get("pageNum")
            })
            
        return result
    except Exception as e:
        logger.error(f"Error reading yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="解析结果读取失败")

@router.post("/task/{task_id}/result/update")
async def update_task_result(task_id: str, update_data: TaskResultUpdate):
    task_dir = TASKS_DIR / task_id
    yaml_path = task_dir / "parse_result.yaml"
    
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
        
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        layouts = data.get("layouts", [])
        if update_data.index < 0 or update_data.index >= len(layouts):
             raise HTTPException(status_code=400, detail="Invalid index")
             
        layouts[update_data.index]["markdownContent"] = update_data.markdownContent
        
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update result")

@router.get("/task/{task_id}/source")
async def download_source_file(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    file_path = Path(task.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
        
    return Response(
        content=file_path.read_bytes(),
        media_type="application/pdf",
        headers={
            'Content-Disposition': f'attachment; filename="{task.filename}"'
        }
    )

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
