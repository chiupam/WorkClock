import sqlite3
import time
from functools import wraps
from typing import Tuple, Dict

from fastapi import Request
from fastapi.responses import RedirectResponse

from app import USER_DB_FILE, logger

# 管理员超时时间（秒）
ADMIN_TIMEOUT = 3600  # 60分钟

def is_valid_open_id(open_id: str) -> Tuple[bool, Dict]:
    """
    检查open_id是否在数据库中有效，并返回用户信息
    返回: (是否有效, 用户信息)
    """
    try:
        conn = sqlite3.connect(USER_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE open_id = ?", (open_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # 返回用户信息字典
            user_info = dict(zip(
                ["id", "username", "user_id", "department_name", 
                 "department_id", "position", "open_id", "first_login_time", "last_activity"],
                result
            ))
            return True, user_info
        return False, {}
    except Exception as e:
        logger.error(f"验证open_id时出错: {str(e)}")
        return False, {}

def admin_required(func):
    """
    管理员权限验证装饰器
    验证用户是否为管理员以及最后活跃时间是否在5分钟内
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # 获取open_id cookie
        open_id = request.cookies.get("open_id")
        
        if not open_id:
            # 未登录，重定向到首页
            return RedirectResponse(url="/", status_code=303)
        
        try:
            # 连接数据库
            conn = sqlite3.connect(USER_DB_FILE)
            cursor = conn.cursor()
            
            # 查询管理员信息
            cursor.execute(
                "SELECT last_activity FROM users WHERE open_id = ? AND user_id = 'admin'", 
                (open_id,)
            )
            admin = cursor.fetchone()
            
            # 检查是否管理员
            if not admin:
                conn.close()
                # 不是管理员，重定向到首页并清除cookie
                response = RedirectResponse(url="/", status_code=303)
                response.delete_cookie(key="open_id", path="/")
                return response
            
            # 检查活跃时间是否在5分钟内
            current_time = int(time.time())
            if current_time - admin[0] > ADMIN_TIMEOUT:
                conn.close()
                # 超时，重定向到首页并清除cookie
                response = RedirectResponse(url="/", status_code=303)
                response.delete_cookie(key="open_id", path="/")
                return response
                
            # 更新管理员最后活跃时间
            cursor.execute(
                "UPDATE users SET last_activity = ? WHERE open_id = ?",
                (current_time, open_id)
            )
            conn.commit()
            conn.close()
            
            # 执行原函数
            return await func(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"管理员验证出错: {str(e)}")
            response = RedirectResponse(url="/", status_code=303)
            response.delete_cookie(key="open_id", path="/")
            return response
    
    return wrapper

# def user_required(func):
#     """
#     用户权限验证装饰器
#     验证用户是否登录
#     """
#     @wraps(func)
#     async def wrapper(request: Request, *args, **kwargs):
#         # 获取open_id cookie
#         open_id = request.cookies.get("open_id")
        
#         if not open_id:
#             # 未登录，重定向到首页
#             return RedirectResponse(url="/", status_code=303)
        
#         # 检查open_id是否有效
#         is_valid, user_info = is_valid_open_id(open_id)
        
#         if not is_valid:
#             # 无效用户，清除cookie并重定向
#             response = RedirectResponse(url="/", status_code=303)
#             response.delete_cookie(key="open_id")
#             return response
        
#         # 更新用户最后活跃时间
#         try:
#             current_time = int(time.time())
#             conn = sqlite3.connect(USER_DB_FILE)
#             cursor = conn.cursor()
#             cursor.execute(
#                 "UPDATE users SET last_activity = ? WHERE open_id = ?",
#                 (current_time, open_id)
#             )
#             conn.commit()
#             conn.close()
#         except Exception as e:
#             logger.error(f"更新用户活跃时间出错: {str(e)}")
        
#         # 执行原函数，并传递用户信息
#         return await func(request, user_info=user_info, *args, **kwargs)
    
#     return wrapper
