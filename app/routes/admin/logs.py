import datetime
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import LOG_DB_FILE, SIGN_DB_FILE, logger
from app.auth.dependencies import admin_required
from app.routes.admin.utils import get_admin_stats, get_admin_name, templates
from app.utils.log import LogType

# 创建路由器
router = APIRouter()

@router.get("/logs")
@admin_required
async def admin_logs_page(request: Request):
    """
    管理员日志查看页面
    """
    
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回日志查看页面
    return templates.TemplateResponse(
        "admin/logs.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "系统日志",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "log_types": vars(LogType)  # 把LogType中的所有常量传到前端
        }
    )

@router.get("/sign-logs-api")
@admin_required
async def get_sign_logs_api(request: Request, page: int = 1, limit: int = 50, username: str = None, date_from: str = None, date_to: str = None, sign_type: str = None, status: str = None):
    """
    获取签到日志API
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(SIGN_DB_FILE)
        cursor = conn.cursor()
        
        # 构建查询条件
        query = "SELECT * FROM sign_logs WHERE 1=1"
        params = []
        
        if username and username.strip():
            query += " AND username LIKE ?"
            params.append(f"%{username}%")
        
        if date_from:
            try:
                from_timestamp = datetime.datetime.strptime(date_from, "%Y-%m-%d").timestamp()
                query += " AND sign_time >= ?"
                params.append(from_timestamp)
            except ValueError:
                pass
        
        if date_to:
            try:
                # 设置为当天的结束时间
                to_date = datetime.datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                to_timestamp = to_date.timestamp()
                query += " AND sign_time <= ?"
                params.append(to_timestamp)
            except ValueError:
                pass
        
        if sign_type and sign_type != "all":
            query += " AND sign_type = ?"
            params.append(sign_type)
            
        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        
        # 获取总记录数
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 添加排序和分页
        query += " ORDER BY sign_time DESC LIMIT ? OFFSET ?"
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # 获取列名
        column_names = [description[0] for description in cursor.description]
        
        # 格式化日志数据
        formatted_logs = []
        for log in logs:
            log_dict = dict(zip(column_names, log))
            
            # 转换时间戳为可读时间
            if "sign_time" in log_dict and log_dict["sign_time"]:
                log_dict["sign_time_formatted"] = datetime.datetime.fromtimestamp(
                    log_dict["sign_time"]
                ).strftime("%Y-%m-%d %H:%M:%S")
            
            formatted_logs.append(log_dict)
        
        # 关闭连接
        conn.close()
        
        return JSONResponse({
            "success": True,
            "logs": formatted_logs,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit
        })
    except Exception as e:
        logger.error(f"获取签到日志失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取签到日志失败: {str(e)}"
        }, status_code=500)

@router.get("/operation-logs-api")
@admin_required
async def get_operation_logs_api(request: Request, page: int = 1, limit: int = 50, username: str = None, date_from: str = None, date_to: str = None, operation_type: str = None, status: str = None):
    """
    获取操作日志API
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(LOG_DB_FILE)
        cursor = conn.cursor()
        
        # 构建查询条件
        query = "SELECT * FROM operation_logs WHERE 1=1"
        params = []
        
        if username and username.strip():
            query += " AND username LIKE ?"
            params.append(f"%{username}%")
        
        if date_from:
            try:
                from_timestamp = datetime.datetime.strptime(date_from, "%Y-%m-%d").timestamp()
                query += " AND operation_time >= ?"
                params.append(from_timestamp)
            except ValueError:
                pass
        
        if date_to:
            try:
                # 设置为当天的结束时间
                to_date = datetime.datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                to_timestamp = to_date.timestamp()
                query += " AND operation_time <= ?"
                params.append(to_timestamp)
            except ValueError:
                pass
        
        if operation_type and operation_type != "all":
            query += " AND operation_type = ?"
            params.append(operation_type)
            
        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        
        # 获取总记录数
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 添加排序和分页
        query += " ORDER BY operation_time DESC LIMIT ? OFFSET ?"
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # 获取列名
        column_names = [description[0] for description in cursor.description]
        
        # 格式化日志数据
        formatted_logs = []
        for log in logs:
            log_dict = dict(zip(column_names, log))
            
            # 转换时间戳为可读时间
            if "operation_time" in log_dict and log_dict["operation_time"]:
                log_dict["operation_time_formatted"] = datetime.datetime.fromtimestamp(
                    log_dict["operation_time"]
                ).strftime("%Y-%m-%d %H:%M:%S")
            
            formatted_logs.append(log_dict)
        
        # 关闭连接
        conn.close()
        
        return JSONResponse({
            "success": True,
            "logs": formatted_logs,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit
        })
    except Exception as e:
        logger.error(f"获取操作日志失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取操作日志失败: {str(e)}"
        }, status_code=500)

@router.get("/login-logs-api")
@admin_required
async def get_login_logs_api(request: Request, page: int = 1, limit: int = 50, username: str = None, user_id: str = None, date_from: str = None, date_to: str = None, status: str = None):
    """
    获取登录日志API
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(LOG_DB_FILE)
        cursor = conn.cursor()
        
        # 构建查询条件
        query = "SELECT * FROM login_logs WHERE 1=1"
        params = []
        
        if username and username.strip():
            query += " AND username LIKE ?"
            params.append(f"%{username}%")
            
        if user_id and user_id.strip():
            query += " AND user_id LIKE ?"
            params.append(f"%{user_id}%")
        
        if date_from:
            try:
                from_timestamp = datetime.datetime.strptime(date_from, "%Y-%m-%d").timestamp()
                query += " AND login_time >= ?"
                params.append(from_timestamp)
            except ValueError:
                pass
        
        if date_to:
            try:
                # 设置为当天的结束时间
                to_date = datetime.datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                to_timestamp = to_date.timestamp()
                query += " AND login_time <= ?"
                params.append(to_timestamp)
            except ValueError:
                pass
            
        if status and status != "all":
            query += " AND status = ?"
            params.append(status)
        
        # 获取总记录数
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # 添加排序和分页
        query += " ORDER BY login_time DESC LIMIT ? OFFSET ?"
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # 获取列名
        column_names = [description[0] for description in cursor.description]
        
        # 格式化日志数据
        formatted_logs = []
        for log in logs:
            log_dict = dict(zip(column_names, log))
            
            # 转换时间戳为可读时间
            if "login_time" in log_dict and log_dict["login_time"]:
                log_dict["login_time_formatted"] = datetime.datetime.fromtimestamp(
                    log_dict["login_time"]
                ).strftime("%Y-%m-%d %H:%M:%S")
            
            formatted_logs.append(log_dict)
        
        # 关闭连接
        conn.close()
        
        return JSONResponse({
            "success": True,
            "logs": formatted_logs,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit
        })
    except Exception as e:
        logger.error(f"获取登录日志失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取登录日志失败: {str(e)}"
        }, status_code=500) 