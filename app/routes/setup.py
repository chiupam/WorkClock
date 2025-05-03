import datetime
import os
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app import SET_DB_FILE
from app.routes.admin.system import trigger_restart_after_setup
from config import Settings
from config import settings

# 创建路由器
router = APIRouter(tags=["系统设置"])

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """
    系统初始化设置页面
    """
    
    # 如果系统已初始化，重定向到首页
    if settings.IS_INITIALIZED:
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse(
        "setup.html", 
        {"request": request}
    )

@router.post("/setup")
async def process_setup(request: Request):
    """
    处理系统初始化设置
    """
    
    # 如果系统已初始化，返回错误
    if settings.IS_INITIALIZED:
        return {"success": False, "message": "系统已经初始化"}
    
    try:
        # 获取提交的数据
        data = await request.json()
        
        # 验证必填字段
        required_fields = ["api_host", "admin_password", "admin_password_confirm", "fuck_password"]
        for field in required_fields:
            if field not in data or not data[field]:
                return {"success": False, "message": f"缺少必填字段: {field}"}
        
        # 验证密码
        if data["admin_password"] != data["admin_password_confirm"]:
            return {"success": False, "message": "两次输入的管理员密码不一致"}
        
        if len(data["admin_password"]) < 6:
            return {"success": False, "message": "管理员密码长度不能少于6个字符"}
        
        # 确保数据目录存在
        os.makedirs("data", exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        
        # 更新设置
        current_time = datetime.datetime.now().timestamp()
        
        # 只处理允许的字段
        allowed_fields = ["api_host", "admin_password", "fuck_password"]
        for key in allowed_fields:
            if key in data:
                cursor.execute(
                    "INSERT OR REPLACE INTO system_settings (setting_key, setting_value, updated_at, is_initialized) VALUES (?, ?, ?, 1)",
                    (key, data[key], current_time)
                )
        
        conn.commit()
        conn.close()
        
        # 创建标记文件，表示需要重启
        try:
            with open("data/needs_restart", "w") as f:
                f.write(f"Initial setup completed at: {datetime.datetime.now().isoformat()}")
        except Exception:
            pass  # 忽略标记文件创建失败的情况
        
        # 触发系统重启
        restart_result = await trigger_restart_after_setup()
        
        # 返回成功消息
        if restart_result["success"]:
            is_ready = restart_result.get("is_ready", False)
            if is_ready:
                return {"success": True, "message": "系统初始化成功！服务已就绪，即将刷新页面..."}
            else:
                return {"success": True, "message": "系统初始化成功！服务正在启动中，请稍候..."}
        else:
            return {"success": True, "message": f"系统初始化成功！但重启可能需要手动操作: {restart_result['message']}"}
    except Exception as e:
        return {"success": False, "message": f"系统初始化失败: {str(e)}"}

 