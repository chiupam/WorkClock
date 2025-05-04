from fastapi import APIRouter

from app.routes.admin import dashboard, settings, logs, schedules, statistics, privilege, system, terminal

# 创建主路由器
router = APIRouter(tags=["管理员"])

# 包含各个模块的路由
router.include_router(dashboard.router)
router.include_router(settings.router)
router.include_router(logs.router)
router.include_router(schedules.router)
router.include_router(statistics.router)
router.include_router(privilege.router)
router.include_router(system.router) 
router.include_router(terminal.router) 