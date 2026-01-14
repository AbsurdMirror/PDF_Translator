from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api.routes import router as api_router
from .core.config import init_directories
from .core.database import engine, Base
from .models import sql_models # 确保模型被导入以便 create_all 能找到

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("Initializing directories...")
    init_directories()
    
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    yield
    # 关闭时执行 (如果有需要清理的资源)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=3002, reload=True)
