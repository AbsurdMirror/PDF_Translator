from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from sqlalchemy import text
from .api.routes import router as api_router
from .core.config import init_directories
from .core.database import engine, Base
from .core.logging_config import setup_logging
from .core.pdf_parse_manager import pdf_parse_manager
from .core.translation_manager import translation_manager
from .models import sql_models # 确保模型被导入以便 create_all 能找到

# 初始化日志配置
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("Initializing directories...")
    init_directories()
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Checking database schema...")
    with engine.connect() as conn:
        try:
            # Check if column exists in configs table
            # SQLite specific check
            result = conn.execute(text("PRAGMA table_info(configs)"))
            columns = [row.name for row in result.fetchall()]
            if "translation_engine" not in columns:
                logger.info("Adding missing column 'translation_engine' to 'configs' table")
                conn.execute(text("ALTER TABLE configs ADD COLUMN translation_engine VARCHAR DEFAULT 'llm'"))
                conn.commit()
        except Exception as e:
            logger.warning(f"Schema check failed: {e}")

    logger.info("lifespan startup complete")
    
    yield
    # 关闭时执行 (如果有需要清理的资源)
    logger.info("Shutting down application...")

    logger.info("Stopping PDF Parse Manager...")
    pdf_parse_manager.stop_all()

    logger.info("Stopping Translation Manager...")
    translation_manager.stop_all()

app = FastAPI(title="PDF Translator API", lifespan=lifespan)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")

logger.info("Application started successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=3002, reload=True)
