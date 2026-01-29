import asyncio
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
from ..models.schemas import TranslationTask, TranslationConfig

# 模拟数据库
class MockDB:
    def __init__(self):
        self.translation_tasks: List[TranslationTask] = [
            TranslationTask(
                taskId='task_001',
                filename='示例文档.pdf',
                status='completed',
                parseProgress=100,
                translateProgress=100,
                createTime='2024-01-15 10:30:00',
                message='翻译完成'
            ),
            TranslationTask(
                taskId='task_002',
                filename='技术手册.pdf',
                status='translating',
                parseProgress=100,
                translateProgress=65,
                createTime='2024-01-15 11:45:00',
                message='正在翻译第13页，共20页'
            )
        ]
        
        self.translation_config = TranslationConfig(
            sourceLang='auto',
            targetLang='zh-CN',
            pageRange='all',
            quality='standard'
        )

    def add_task(self, filename: str) -> str:
        task_id = f"task_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        new_task = TranslationTask(
            taskId=task_id,
            filename=filename,
            status='pending',
            parseProgress=0,
            translateProgress=0,
            createTime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            message='等待开始...'
        )
        self.translation_tasks.insert(0, new_task)
        return task_id

    def get_task(self, task_id: str) -> Optional[TranslationTask]:
        for task in self.translation_tasks:
            if task.taskId == task_id:
                return task
        return None

    def update_config(self, config: TranslationConfig):
        self.translation_config = config

    async def simulate_translation(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return

        task.status = 'translating'
        task.message = '开始翻译'
        task.translateProgress = 0

        while task.translateProgress < 100:
            await asyncio.sleep(1)  # 模拟耗时
            increment = random.randint(5, 15)
            task.translateProgress = min(100, task.translateProgress + increment)
            
            if task.translateProgress < 100:
                task.message = f'正在翻译... {task.translateProgress}%'
            else:
                task.status = 'completed'
                task.message = '翻译完成'
                
db = MockDB()
