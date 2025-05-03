import logging
import os
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app import logger
from app.auth import routes as auth_routes
from app.routes import crontab
from app.routes import index, sign, statistics
from app.routes.admin import router as admin_router
from app.routes.setup import router as setup_router
from app.utils.db_init import initialize_database
from config import Settings

logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.ERROR)

settings = Settings()

# 创建自定义中间件类
class AdminPathMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 如果路径以/admin开头，标记为admin路径
        if request.url.path.startswith("/admin"):
            request.state.is_admin_path = True
            
            # 处理请求
            try:
                response = await call_next(request)
                
                # 检查是否发生了重定向到根路由
                if (response.status_code in (302, 303, 307, 308) and 
                    str(response.headers.get("location", "")).rstrip("/") == ""):
                    # 检查是否删除了open_id cookie
                    cookie_header = response.headers.get("Set-Cookie", "")
                    if "open_id=; " in cookie_header or "open_id=;" in cookie_header:
                        # 有删除cookie的操作，允许重定向
                        return response
                    else:
                        # 没有删除cookie，删除cookie
                        response = RedirectResponse(url="/", status_code=303)
                        response.delete_cookie(key="open_id", path="/")
                        return response
                return response
            except Exception as e:
                logger.error(f"AdminPathMiddleware出错: {str(e)}", exc_info=True)
                raise
        else:
            request.state.is_admin_path = False
            return await call_next(request)

# 定义处理时间中间件
class ProcessTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.APP_NAME + "API",
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION
)

# 添加自定义中间件
app.add_middleware(AdminPathMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加处理时间中间件
app.add_middleware(ProcessTimeMiddleware)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 包含路由
app.include_router(index.router)  # 根路由
app.include_router(auth_routes.router, prefix="/auth", tags=["认证"])
app.include_router(admin_router, prefix="/admin", tags=["管理员"])
app.include_router(sign.router, tags=["打卡"])  # 打卡路由
app.include_router(statistics.router, prefix="/stats", tags=["统计"])  # 统计路由
app.include_router(crontab.router, prefix="/schedules", tags=["定时"])  # 定时打卡路由
app.include_router(setup_router, tags=["系统初始化"])  # 初始化路由

# 初始化数据库
@app.on_event("startup")
async def startup_db_client():
    try:
        # 确保data目录存在
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        # 初始化所有数据库
        initialize_database()
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
 