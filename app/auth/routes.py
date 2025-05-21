import httpx
import sqlite3
import time
from fastapi import APIRouter, Response, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import logger, USER_DB_FILE as DB_FILE, SET_DB_FILE
from app.auth.utils import random_open_id, get_mobile_user_agent
from app.utils.host import build_api_url
from app.utils.log import log_login, log_operation, LogType
from app.routes.admin.privilege import DEPARTMENTS

from config import settings

# 创建路由器
router = APIRouter(tags=["认证"])

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")


class UserLogin(BaseModel):
    """用户登录请求体模型"""
    phone: str
    password: str


async def handle_admin_login(request: Request, password: str):
    """
    处理管理员登录
    
    :param request: 请求对象
    :param password: 管理员密码
    :return: 登录结果响应
    """
    try:
        # 从数据库获取管理员密码
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'admin_password'")
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "系统尚未初始化，请先完成初始化设置"}
            )
            
        admin_password = result[0]
        
        # 验证管理员密码
        if password != admin_password:
            logger.warning("管理员登录失败: 密码错误")
            
            # 记录登录失败日志
            await log_login("admin", "管理员", request.client.host, False)
            await log_operation("管理员", LogType.LOGIN, "管理员登录失败：密码错误", request.client.host, False)
            
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "管理员密码错误"}
            )
        
        # 生成openid，作为会话标识
        generated_open_id = random_open_id()
        current_time = int(time.time())

        # 保存管理员会话到数据库
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 检查管理员用户是否存在
        cursor.execute("SELECT * FROM users WHERE user_id = 'admin'")
        admin_user = cursor.fetchone()
        
        if admin_user:
            # 更新管理员openid和活跃时间
            cursor.execute(
                "UPDATE users SET open_id = ?, last_activity = ? WHERE user_id = 'admin'",
                (generated_open_id, current_time)
            )
        else:
            # 创建管理员用户
            cursor.execute(
                """INSERT INTO users 
                   (username, user_id, department_name, department_id, position, open_id, first_login_time, last_activity) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("管理员", "admin", "系统管理", "0", "管理员", generated_open_id, current_time, current_time)
            )
        
        conn.commit()
        conn.close()
        
        # 记录登录日志
        try:
            await log_login("admin", "管理员", request.client.host, True)
            await log_operation("管理员", LogType.LOGIN, "管理员登录成功", request.client.host, True)
        except Exception as e:
            logger.error(f"记录登录日志失败: {str(e)}")
        
        # 创建重定向响应对象
        redirect_response = RedirectResponse(
            url="/admin/dashboard",
            status_code=303  # 303 See Other 适合POST后重定向
        )
        
        # 在重定向响应上设置cookie
        redirect_response.set_cookie(
            key="open_id", 
            value=generated_open_id, 
            httponly=True, 
            path="/"
        )
        
        return redirect_response
        
    except Exception as e:
        logger.error(f"管理员登录错误: {str(e)}")
        # 记录错误日志
        await log_operation("管理员", LogType.LOGIN, f"管理员登录出错: {str(e)}", request.client.host, False)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"登录失败: {str(e)}"}
        )
    

async def handle_special_login(request: Request, phone: str, password: str):
    """
    处理特殊打卡用户登录
    
    :param request: 请求对象
    :param phone: 用户标识符，格式为 depid@userid@username 或 depid/userid/username
    :param password: 特殊打卡密码
    :return: 登录结果响应
    """
    try:
        # 从数据库中获取特殊打卡登录密码
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'fuck_password'")
        result = cursor.fetchone()
        conn.close()

        if not result:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "系统尚未初始化，请先完成初始化设置"}
            )
        
        special_password = result[0]

        if password != special_password:
            # 记录登录失败日志
            await log_login("unknown", phone, request.client.host, False)
            await log_operation(phone, LogType.LOGIN, "特殊打卡登录失败：密码错误", request.client.host, False)
            
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "特殊打卡登录密码错误，请咨询系统管理员"}
            )
        
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}

        # 从phone中获取 DepID 、 UserID 、 UserName
        separator = "@" if "@" in phone else "/"
        parts = phone.split(separator)
        dep_id = parts[0]
        user_id = parts[1]
        user_name = parts[2] if len(parts) > 2 else None
        position = "未知职位"

        # 验证用户信息
        async with httpx.AsyncClient() as client:
            api_url = build_api_url("/Apps/getUserInfoList")
            api_request_data = {
                "unitcode": settings.UNIT_CODE,
                "depid": dep_id,
            }
            api_response = await client.post(api_url, headers=headers, json=api_request_data)
            result = next((item for item in api_response.json() if item["userid"] == int(user_id)), None)

            if not result:
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "message": "用户不存在"}
                )
            
            if result.get("username", user_name) != user_name:
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "message": "当前部门不存在该用户"}
                )
            user_name = result.get("username", user_name)
            
        department_name = DEPARTMENTS.get(dep_id, "未知部门")

        # 生成openid，作为会话标识
        generated_open_id = random_open_id()

        # 更新数据库
        await database_operations(user_id, user_name, department_name, dep_id, position, generated_open_id)
        
        # 记录登录日志
        await log_login(user_id, user_name, request.client.host, True)
        await log_operation(user_name, LogType.LOGIN, "特殊打卡用户登录成功", request.client.host, True)
        
        # 创建重定向响应对象
        redirect_response = RedirectResponse(
            url="/",
            status_code=303  # 303 See Other 适合POST后重定向
        )
        
        # 在重定向响应上设置cookie
        redirect_response.set_cookie(
            key="open_id", 
            value=generated_open_id, 
            httponly=True, 
            path="/"
        )

        # 返回重定向响应
        return redirect_response
        
    except Exception as e:
        error_msg = f"特殊打卡登录出错: {str(e)}"
        logger.error(error_msg)
        
        # 记录错误日志
        await log_operation(phone, LogType.LOGIN, error_msg, request.client.host if request.client else "", False)
        
        # 返回错误响应
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": error_msg}
        )


async def handle_user_login(request: Request, phone: str, password: str):
    """
    处理普通用户登录
    
    :param request: 请求对象
    :param phone: 用户手机号
    :param password: 用户密码
    :return: 登录结果响应
    """
    try:
        # 普通用户登录，发送请求到外部API
        generated_open_id = random_open_id()
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}
        
        # 构建请求数据
        api_request_data = {
            "UserCccount": phone,
            "Password": password,
            "OpenID": generated_open_id
        }

        # 微信登录API请求
        cookie = await wx_login(headers, api_request_data)
        if not cookie:
            # 记录登录失败日志
            await log_login("unknown", phone, request.client.host, False)
            await log_operation(phone, LogType.LOGIN, "用户登录失败：API返回失败", request.client.host, False)
            
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "登录失败"}
            )
        
        # 获取用户信息
        headers["Cookie"] = cookie
        user_info = await get_user_info(headers)
        if not user_info:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "登录失败"}
            )
        
        # 获取用户的详细信息
        user_id = user_info.get("UserID", "")
        username = user_info.get("UserName", "")
        department_id = user_info.get("DepID", "")
        position = user_info.get("Position", "")
        department_name = user_info.get("DepName", "")

        # 更新数据库
        await database_operations(user_id, username, department_name, department_id, position, generated_open_id)

        # 记录登录日志
        await log_login(user_id, username, request.client.host, True)
        await log_operation(username, LogType.LOGIN, "用户登录成功", request.client.host, True)
        
        # 创建重定向响应对象
        redirect_response = RedirectResponse(
            url="/",
            status_code=303  # 303 See Other 适合POST后重定向
        )
        
        # 在重定向响应上设置cookie
        redirect_response.set_cookie(
            key="open_id", 
            value=generated_open_id, 
            httponly=True, 
            path="/"
        )

        # 返回重定向响应
        return redirect_response
    
    except Exception as e:
        error_msg = f"无法连接到API服务器: {str(e)}"
        logger.error(error_msg)
        
        # 记录错误日志
        await log_operation(phone, LogType.LOGIN, f"用户登录出错: {error_msg}", request.client.host if request.client else "", False)
        
        # 返回错误响应
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": error_msg}
        )


@router.post("/login")
async def login(request: Request, user_login: UserLogin):
    """
    用户登录 - 区分普通用户、特殊打卡用户和管理员
    使用JSON方式提交登录请求
    
    :param request: 请求对象
    :param user_login: 用户登录信息
    :return: 登录结果响应
    """
    login_phone = user_login.phone
    login_password = user_login.password

    # 检查是否是管理员登录尝试
    if login_phone == "admin":
        return await handle_admin_login(request, login_password)
    
    # 检查是否是特殊打卡登录尝试
    if "@" in login_phone or "/" in login_phone:
        return await handle_special_login(request, login_phone, login_password)
    
    # 普通用户登录
    return await handle_user_login(request, login_phone, login_password)


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    用户登出
    
    :param request: 请求对象
    :param response: 响应对象
    :return: 登出结果响应
    """
    # 获取openid
    open_id = request.cookies.get("open_id")
    
    if open_id:
        try:
            # 尝试获取用户信息
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE open_id = ?", (open_id,))
            user = cursor.fetchone()
            
            if user:
                username = user['username']
                user_id = user['user_id']
                
                # 记录登出日志
                await log_operation(username, LogType.LOGIN, "用户登出", request.client.host, True)
                
                # 将用户的open_id标记为空，而不是删除用户记录
                cursor.execute("UPDATE users SET open_id = NULL WHERE open_id = ?", (open_id,))
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"退出登录时发生错误: {str(e)}")
    
    # 创建重定向响应对象
    redirect_response = RedirectResponse(url="/", status_code=303)
    
    # 清除cookies
    redirect_response.delete_cookie(key="open_id")
    redirect_response.delete_cookie(key="user_data")
    
    return redirect_response


async def wx_login(headers: dict, data: dict):
    """
    微信登录API请求
    
    :param headers: 请求头
    :param data: 请求数据
    :return: 微信登录成功后的Cookie或None
    """
    try:
        async with httpx.AsyncClient() as client:
            api_url = build_api_url("/Apps/wxLogin")
            api_response = await client.post(api_url, headers=headers, json=data)
            api_data = api_response.json()
            
            if api_data.get("success", False):
                return api_response.headers.get("Set-Cookie", {})
            else:
                return None
    except Exception as e:
        logger.error(f"微信登录API请求异常: {str(e)}")
        return None


async def get_user_info(headers: dict):
    """
    获取用户信息API请求
    
    :param headers: 请求头
    :return: 用户信息字典或None
    """
    try:
        async with httpx.AsyncClient() as client:
            api_url = build_api_url("/Apps/AppIndex")
            params = {'UnitCode': settings.UNIT_CODE}
            api_response = await client.get(api_url, headers=headers, params=params)
            api_data = api_response.json()
            
            if api_data.get("success", False):
                api_data = api_data.get("data", {})
                fields = ["UserID", "UserName", "DepID", "Position", "DepName"]
                user_info = {field: api_data.get(field, "") for field in fields}
                return user_info
            else:
                logger.error(f"API请求成功但返回失败状态: {api_data.get('message', '未知错误')}")
                return None
    except Exception as e:
        logger.error(f"获取用户信息时发生异常: {str(e)}")
        return None
    

async def database_operations(user_id: str, username: str, department_name: str, department_id: str, position: str, generated_open_id: str):
    """
    数据库用户信息操作
    
    :param user_id: 用户ID
    :param username: 用户名
    :param department_name: 部门名称
    :param department_id: 部门ID
    :param position: 职位
    :param generated_open_id: 生成的OpenID
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    # 先使用user_id查找用户
    cursor.execute("SELECT id, open_id, deleted FROM users WHERE user_id = ? AND deleted = 0", (user_id,))
    user = cursor.fetchone()
    
    if user:
        # 用户存在，更新信息
        cursor.execute(
            """UPDATE users SET 
               username = ?, department_name = ?, department_id = ?, 
               position = ?, open_id = ?, last_activity = ? 
               WHERE user_id = ? AND deleted = 0""",
            (username, department_name, department_id, position, 
             generated_open_id, current_time, user_id)
        )
    else:
        # 查找被标记为删除的同一用户
        cursor.execute("SELECT id FROM users WHERE user_id = ? AND deleted = 1", (user_id,))
        deleted_user = cursor.fetchone()
        
        if deleted_user:
            # 恢复已删除的用户
            cursor.execute(
                """UPDATE users SET 
                   username = ?, department_name = ?, department_id = ?, 
                   position = ?, open_id = ?, last_activity = ?, deleted = 0
                   WHERE user_id = ? AND deleted = 1""",
                (username, department_name, department_id, position, 
                 generated_open_id, current_time, user_id)
            )
        else:
            # 创建新用户
            cursor.execute(
                """INSERT INTO users 
                   (username, user_id, department_name, department_id, position, 
                    open_id, first_login_time, last_activity, deleted) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (username, user_id, department_name, department_id, position,
                 generated_open_id, current_time, current_time, 0)
            )
    
    conn.commit()
    conn.close()
