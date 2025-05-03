import datetime

from fastapi import APIRouter, Request

from app.auth.dependencies import admin_required
from app.routes.admin.utils import get_admin_stats, get_admin_name, templates

# 创建路由器
router = APIRouter()

@router.get("/statistics")
@admin_required
async def admin_statistics_page(request: Request):
    """
    管理员考勤统计页面
    """
    
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回考勤统计页面
    return templates.TemplateResponse(
        "admin/statistics.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "考勤统计",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ) 