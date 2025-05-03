import datetime
import httpx
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import USER_DB_FILE, logger
from app.auth.dependencies import admin_required
from app.routes.admin.utils import get_admin_stats, update_admin_active_time, get_admin_name, templates, DEPARTMENTS
from app.auth.utils import get_mobile_user_agent
from app.utils.host import build_api_url

# 创建路由器
router = APIRouter()

@router.get("/dashboard")
@admin_required
async def admin_dashboard(request: Request):
    """
    管理员仪表盘页面
    """
    
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回管理员仪表盘
    return templates.TemplateResponse(
        "admin/dashboard.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "管理员仪表盘",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@router.get("/stats-data")
@admin_required
async def get_stats_data(request: Request):
    """
    获取最新统计数据的API
    """
    try:
        # 获取基本统计信息
        stats = await get_admin_stats()
        return JSONResponse({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取统计数据失败: {str(e)}"
        }, status_code=500)

@router.get("/users")
@admin_required
async def admin_users_page(request: Request):
    """
    管理员用户管理页面
    """
    
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回用户管理页面
    return templates.TemplateResponse(
        "admin/users.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "用户管理",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@router.get("/users-api")
@admin_required
async def get_users_api(request: Request):
    """
    获取用户列表API
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(USER_DB_FILE)
        cursor = conn.cursor()
        
        # 查询所有普通用户
        cursor.execute(
            "SELECT id, username, user_id, department_name, department_id, position, first_login_time, last_activity FROM users WHERE user_id != 'admin'"
        )
        users = cursor.fetchall()
        
        # 格式化用户数据
        formatted_users = []
        for user in users:
            first_login = user[6] if user[6] else 0
            last_activity = user[7] if user[7] else 0
            
            formatted_users.append({
                "id": user[0],
                "username": user[1],
                "user_id": user[2],
                "department_name": user[3],
                "department_id": user[4],
                "position": user[5],
                "first_login": first_login,
                "last_activity": last_activity
            })
        
        # 关闭连接
        conn.close()
        
        return JSONResponse({
            "success": True,
            "users": formatted_users
        })
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取用户列表失败: {str(e)}"
        }, status_code=500)

