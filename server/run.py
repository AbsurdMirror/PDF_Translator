import uvicorn
import os
import sys

# 将当前目录添加到 python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # 使用 reload=True 在开发模式下运行
    uvicorn.run("app.main:app", host="localhost", port=3002, reload=True, app_dir="server")
