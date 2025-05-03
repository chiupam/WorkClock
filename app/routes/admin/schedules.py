import ast
import datetime
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import CRON_DB_FILE, USER_DB_FILE, logger
from app.auth.dependencies import admin_required
from app.routes.admin.utils import get_admin_stats, get_admin_name, templates

# 创建路由器
router = APIRouter()

@router.get("/schedules")
@admin_required
async def admin_schedules_page(request: Request):
    """
    管理员定时任务管理页面
    """
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回定时任务管理页面
    return templates.TemplateResponse(
        "admin/schedules.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "定时任务管理",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@router.get("/schedules-api")
@admin_required
async def get_schedules_api(request: Request):
    """
    获取定时任务列表API
    """
    try:
        # 连接cron.db数据库
        conn = sqlite3.connect(CRON_DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询所有定时任务
        cursor.execute(
            """
            SELECT s.id, s.user_id, s.username, s.morning, s.afternoon, 
                   s.schedule_index, s.created_at, s.morning_time, s.afternoon_time,
                   s.morning_selecte, s.afternoon_selecte
            FROM schedules s
            ORDER BY s.created_at DESC
            """
        )
        
        schedules = cursor.fetchall()
        
        # 格式化定时任务数据
        formatted_schedules = []
        for schedule in schedules:
            index = schedule['schedule_index']
            
            # 查询用户详细信息
            user_conn = sqlite3.connect(USER_DB_FILE)
            user_conn.row_factory = sqlite3.Row
            user_cursor = user_conn.cursor()
            user_cursor.execute(
                "SELECT department_name, position FROM users WHERE user_id = ?", 
                (schedule['user_id'],)
            )
            user_info = user_cursor.fetchone()
            user_conn.close()
            
            department = user_info['department_name'] if user_info else "未知"
            position = user_info['position'] if user_info else "未知"
            
            # 解析选择状态数组
            morning_selections = []
            afternoon_selections = []
            
            if schedule['morning_selecte']:
                try:
                    morning_selections = ast.literal_eval(schedule['morning_selecte'])
                except:
                    morning_selections = [0, 0, 0]
            else:
                morning_selections = [0, 0, 0]
            
            if schedule['afternoon_selecte']:
                try:
                    afternoon_selections = ast.literal_eval(schedule['afternoon_selecte'])
                except:
                    afternoon_selections = [0, 0, 0]
            else:
                afternoon_selections = [0, 0, 0]
            
            # 获取选择的时间
            active_morning_times = []
            active_afternoon_times = []
            
            if schedule['morning_time']:
                try:
                    active_morning_times = ast.literal_eval(schedule['morning_time'])
                except:
                    active_morning_times = []
                    
            if schedule['afternoon_time']:
                try:
                    active_afternoon_times = ast.literal_eval(schedule['afternoon_time'])
                except:
                    active_afternoon_times = []
            
            formatted_schedules.append({
                "id": schedule['id'],
                "user_id": schedule['user_id'],
                "username": schedule['username'],
                "department": department,
                "position": position,
                "morning": schedule['morning'] == 1,
                "afternoon": schedule['afternoon'] == 1,
                "morning_times": active_morning_times,
                "afternoon_times": active_afternoon_times,
                "schedule_index": schedule['schedule_index'],
                "morning_selections": morning_selections,
                "afternoon_selections": afternoon_selections,
                "created_at": schedule['created_at']
            })
        
        # 关闭连接
        conn.close()
        
        return JSONResponse({
            "success": True,
            "schedules": formatted_schedules,
            "total": len(formatted_schedules)
        })
    except Exception as e:
        logger.error(f"获取定时任务列表失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取定时任务列表失败: {str(e)}"
        }, status_code=500)

@router.delete("/schedules/{schedule_id}")
@admin_required
async def delete_schedule_api(request: Request, schedule_id: int):
    """
    删除定时任务API
    """
    try:
        # 连接cron.db数据库
        conn = sqlite3.connect(CRON_DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取定时任务信息
        cursor.execute("SELECT user_id FROM schedules WHERE id = ?", (schedule_id,))
        schedule = cursor.fetchone()
        
        if not schedule:
            return JSONResponse({
                "success": False,
                "message": "定时任务不存在"
            }, status_code=404)
        
        user_id = schedule['user_id']
        
        # 删除定时任务
        cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()
        
        # 删除APScheduler中的任务
        from app.routes.crontab import remove_schedule_jobs
        remove_schedule_jobs(user_id)
        
        # 关闭连接
        conn.close()
        
        return JSONResponse({
            "success": True,
            "message": "定时任务已删除"
        })
    except Exception as e:
        logger.error(f"删除定时任务失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"删除定时任务失败: {str(e)}"
        }, status_code=500) 