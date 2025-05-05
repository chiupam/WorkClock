import datetime
import re
import httpx
import sqlite3
from fastapi.templating import Jinja2Templates

from app import USER_DB_FILE, SET_DB_FILE, logger
from config import settings

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")

async def update_admin_active_time(open_id: str):
    """
    更新管理员活跃时间
    """
    conn = sqlite3.connect(USER_DB_FILE)
    cursor = conn.cursor()
    
    # 更新管理员活跃时间    
    cursor.execute("UPDATE users SET last_activity = ? WHERE open_id = ?", (datetime.datetime.now().timestamp(), open_id))
    conn.commit()
    conn.close()

async def get_admin_stats():
    """
    获取系统基本统计信息
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(USER_DB_FILE)
        cursor = conn.cursor()
        
        # 统计总用户数
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id != 'admin'")
        total_users = cursor.fetchone()[0]
        
        # 统计今日活跃用户
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity >= ? AND user_id != 'admin'", (today_start,))
        active_users_today = cursor.fetchone()[0]
        
        # 统计本周活跃用户
        week_start = (datetime.datetime.now() - datetime.timedelta(days=datetime.datetime.now().weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity >= ? AND user_id != 'admin'", (week_start,))
        active_users_week = cursor.fetchone()[0]
        
        # 统计本月活跃用户
        month_start = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity >= ? AND user_id != 'admin'", (month_start,))
        active_users_month = cursor.fetchone()[0]
        
        # 关闭连接
        conn.close()
        
        # 获取登录日志信息
        from app import LOG_DB_FILE
        conn_log = sqlite3.connect(LOG_DB_FILE)
        cursor_log = conn_log.cursor()
        
        # 获取今日登录次数
        cursor_log.execute("SELECT COUNT(*) FROM login_logs WHERE login_time >= ?", (today_start,))
        today_logins = cursor_log.fetchone()[0]
        
        conn_log.close()
        
        # 获取系统设置信息
        conn_set = sqlite3.connect(SET_DB_FILE)
        cursor_set = conn_set.cursor()
        
        # 获取系统名称
        cursor_set.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'system_name'")
        result = cursor_set.fetchone()
        system_name = result[0] if result else "考勤管理系统"
        
        # 获取系统版本号
        cursor_set.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'app_version'")
        result = cursor_set.fetchone()
        app_version = result[0] if result else settings.APP_VERSION
        
        conn_set.close()

        # 返回统计信息
        return {
            "total_users": total_users,
            "active_users_today": active_users_today,
            "active_users_week": active_users_week,
            "active_users_month": active_users_month,
            "today_logins": today_logins,
            "system_name": system_name,
            "system_version": app_version,
            "system_start_time": datetime.datetime.fromtimestamp(settings.START_TIME).strftime("%Y-%m-%d %H:%M:%S") if hasattr(settings, "START_TIME") else "未知"
        }
    except Exception as e:
        # 发生错误，返回默认值
        return {
            "total_users": 0,
            "active_users_today": 0,
            "active_users_week": 0,
            "active_users_month": 0,
            "today_logins": 0,
            "system_name": "考勤管理系统",
            "system_version": settings.APP_VERSION,
            "system_start_time": "未知",
            "error": str(e)
        }

async def get_admin_name(open_id: str) -> str:
    """
    查询管理员名称
    """
    conn = sqlite3.connect(USER_DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username FROM users WHERE open_id = ? AND user_id = 'admin'", 
        (open_id,)
    )
    admin_info = cursor.fetchone()
    conn.close()
    
    return admin_info[0] if admin_info else "管理员" 

async def get_latest_github_tag() -> str:
    def convert_git_url_to_api_tags_url(git_url: str) -> str:
        """从 GitHub 的 .git 地址中提取用户和仓库，并生成 API tags 地址"""
        match = re.match(r'https://github\.com/([^/]+)/([^/]+?)(\.git)?$', git_url)
        if match:
            user, repo = match.group(1), match.group(2)
            return f"https://api.github.com/repos/{user}/{repo}/tags"
        raise ValueError("无效的 GitHub 仓库地址格式")
    
    url = convert_git_url_to_api_tags_url(settings.GIT_REPO)
    headers = {"Accept": "application/vnd.github.v3+json"}
    app_version = settings.APP_VERSION

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            tags = response.json()

            if isinstance(tags, list) and tags:
                app_version = tags[0].get("name", app_version)
                
                # 将获取到的版本号保存到数据库
                try:
                    conn = sqlite3.connect(SET_DB_FILE)
                    cursor = conn.cursor()
                    
                    # 检查表中是否已存在app_version键
                    cursor.execute("SELECT COUNT(*) FROM system_settings WHERE setting_key = 'app_version'")
                    exists = cursor.fetchone()[0] > 0
                    
                    if exists:
                        # 更新现有记录
                        cursor.execute("UPDATE system_settings SET setting_value = ? WHERE setting_key = 'app_version'", 
                                      (app_version,))
                    else:
                        # 插入新记录
                        cursor.execute("INSERT INTO system_settings (setting_key, setting_value) VALUES (?, ?)", 
                                      ('app_version', app_version))
                    
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"保存系统版本到数据库时出错: {str(e)}")
            else:
                logger.error("获取 GitHub 标签失败（返回为空或格式错误），使用默认标签")
                
                # 尝试从数据库获取之前保存的版本号
                try:
                    conn = sqlite3.connect(SET_DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'app_version'")
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result and result[0]:
                        app_version = result[0]
                except Exception as e:
                    logger.error(f"从数据库获取系统版本时出错: {str(e)}")

    except httpx.TimeoutException:
        logger.error("请求 GitHub 标签时发生超时")
        # 尝试从数据库获取之前保存的版本号
        try:
            conn = sqlite3.connect(SET_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'app_version'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                app_version = result[0]
        except Exception as e:
            logger.error(f"从数据库获取系统版本时出错: {str(e)}")

    except httpx.RequestError as exc:
        logger.error(f"请求 GitHub 标签时发生网络错误: {exc!r}")
        # 尝试从数据库获取之前保存的版本号
        try:
            conn = sqlite3.connect(SET_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'app_version'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                app_version = result[0]
        except Exception as e:
            logger.error(f"从数据库获取系统版本时出错: {str(e)}")

    except httpx.HTTPStatusError as exc:
        logger.error(f"GitHub 返回错误响应: {exc.response.status_code} - {exc.response.text}")
        # 尝试从数据库获取之前保存的版本号
        try:
            conn = sqlite3.connect(SET_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'app_version'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                app_version = result[0]
        except Exception as e:
            logger.error(f"从数据库获取系统版本时出错: {str(e)}")

    return app_version
    