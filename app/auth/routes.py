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

from config import settings

# 创建路由器
router = APIRouter(tags=["认证"])

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")

class UserLogin(BaseModel):
    phone: str
    password: str

async def handle_admin_login(request: Request, password: str):
    """
    处理管理员登录
    
    :param phone: 管理员账号
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
            await log_login("admin", "管理员",request.client.host, False)
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

        cookie = await wx_login(headers, api_request_data)
        if not cookie:
            # 记录登录失败日志
            await log_login("unknown", phone, request.client.host, False)
            await log_operation(phone, LogType.LOGIN, "用户登录失败：API返回失败", request.client.host, False)
            
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "登录失败"}
            )
        
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
        
        # 登录成功，保存用户信息到本地数据库（不包含账号密码）
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
async def login(
    request: Request,
    user_login: UserLogin
):
    """
    用户登录 - 区分普通用户和管理员
    使用JSON方式提交登录请求
    """
    login_phone = user_login.phone
    login_password = user_login.password

    # 检查是否是管理员登录尝试
    if login_phone == "admin":
        return await handle_admin_login(request, login_password)
    
    # 普通用户登录
    return await handle_user_login(request, login_phone, login_password)

@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    用户登出
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
    微信登录
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
        logger.error(f"获取用户信息时发生异常: {str(e)}")
        return None


async def get_user_info(headers: dict):
    """
    获取用户信息
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
                user_info = {}
                for field in fields:
                    user_info[field] = api_data.get(field, "")
                return user_info
            else:
                logger.error(f"API请求成功但返回失败状态: {api_data.get('message', '未知错误')}")
                return None
    except Exception as e:
        logger.error(f"获取用户信息时发生异常: {str(e)}")
        return None