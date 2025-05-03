import logging
import sys

import uvicorn
from dotenv import load_dotenv

from config import settings

# 配置日志级别 - 禁用httpcore和httpx的DEBUG日志
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

if __name__ == "__main__":
    # 加载.env文件中的环境变量
    load_dotenv()

    host = "0.0.0.0"
    port = 8000
    reload = True
    log_level = settings.LOG_LEVEL.lower()

    try:        
        uvicorn.run("app.main:app", host=host, port=port, reload=reload, log_level=log_level)
    except ValueError as e:
        print(f"错误: {str(e)}")
        sys.exit(1) 