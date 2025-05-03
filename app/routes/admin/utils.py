import datetime
import sqlite3

from fastapi.templating import Jinja2Templates

from app import USER_DB_FILE, SET_DB_FILE

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")

# 部门信息常量（仅后端可见）
DEPARTMENTS = {
    "3": "院领导",
    "7": "政治部",
    "11": "办公室",
    "10": "综合业务部",
    "8": "第一检察部",
    "9": "第二检察部",
    "4": "第三检察部",
    "5": "第四检察部",
    "12": "第五检察部",
    "15": "未成年人检察组",
    "6": "待入职人员",
    "13": "检委办",
    "2": "系统管理员",
    "1": "测试部门",
    "14": "退休离职人员"
}

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
        
        # 获取系统名称设置
        conn_set = sqlite3.connect(SET_DB_FILE)
        cursor_set = conn_set.cursor()
        
        cursor_set.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'system_name'")
        result = cursor_set.fetchone()
        system_name = result[0] if result else "考勤管理系统"
        
        conn_set.close()
        
        from config import settings
        
        # 返回统计信息
        return {
            "total_users": total_users,
            "active_users_today": active_users_today,
            "active_users_week": active_users_week,
            "active_users_month": active_users_month,
            "today_logins": today_logins,
            "system_name": system_name,
            "system_version": settings.APP_VERSION,
            "system_start_time": datetime.datetime.fromtimestamp(settings.START_TIME).strftime("%Y-%m-%d %H:%M:%S") if hasattr(settings, "START_TIME") else "未知"
        }
    except Exception as e:
        # 发生错误，返回默认值
        from config import settings
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