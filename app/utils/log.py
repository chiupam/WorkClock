import datetime
import sqlite3
from app import SIGN_DB_FILE, LOG_DB_FILE, logger

async def log_sign_activity(username: str, sign_type: str, 
                     status: bool = False, message: str = "", 
                     ip_address: str = ""):
    """
    记录签到活动到sign.db数据库
    
    参数:
        username: 用户名
        sign_type: 签到类型（上班打卡/下班打卡）
        status: 打卡状态（成功/失败）
        message: 返回的消息或备注
        ip_address: 客户端IP地址
    """
    try:
        conn = sqlite3.connect(SIGN_DB_FILE)
        cursor = conn.cursor()
        
        sign_time = datetime.datetime.now().timestamp()
        status_text = "成功" if status else "失败"
        
        cursor.execute(
            '''
            INSERT INTO sign_logs 
            (username, sign_time, sign_type, status, remark, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (username, sign_time, sign_type, status_text, message, ip_address)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"签到日志已记录: 用户 {username} {sign_type} {status_text}")
        return True
    except Exception as e:
        logger.error(f"记录签到日志失败: {str(e)}")
        return False

# 操作类型常量
class LogType:
    LOGIN = "LOGIN"           # 登录操作
    VIEW = "VIEW"             # 查看操作
    EDIT = "EDIT"             # 编辑操作
    CONFIG = "CONFIG"         # 配置操作
    SIGN = "SIGN"             # 签到操作
    CRON = "CRON"             # 定时任务操作
    ADMIN = "ADMIN"           # 管理员操作
    SYSTEM = "SYSTEM"         # 系统操作

# 操作日志记录函数
async def log_operation(username: str, 
                  operation_type: str, 
                  operation_detail: str, 
                  ip_address: str = "", 
                  status: bool = True, 
                  remarks: str = ""):
    """
    记录用户操作到log.db数据库
    
    参数:
        username: 用户名
        operation_type: 操作类型，使用LogType中的常量
        operation_detail: 操作详情
        ip_address: 客户端IP地址
        status: 操作状态（成功/失败）
        remarks: 备注信息
    """
    try:
        conn = sqlite3.connect(LOG_DB_FILE)
        cursor = conn.cursor()
        
        operation_time = datetime.datetime.now().timestamp()
        status_text = "成功" if status else "失败"
        
        cursor.execute(
            '''
            INSERT INTO operation_logs 
            (username, operation_time, operation_type, operation_detail, ip_address, status, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (username, operation_time, operation_type, operation_detail, ip_address, status_text, remarks)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"操作日志已记录: 用户 {username} - {operation_type} - {operation_detail} - {status_text}")
        return True
    except Exception as e:
        logger.error(f"记录操作日志失败: {str(e)}")
        return False

# 登录日志记录函数 - 使用现有login_logs表
async def log_login(user_id: str, 
              username: str, 
              ip_address: str = "", 
              status: bool = True):
    """
    记录用户登录日志到login_logs表
    
    参数:
        user_id: 用户ID
        username: 用户名
        ip_address: 客户端IP地址
        status: 登录状态（成功/失败）
    """
    try:
        conn = sqlite3.connect(LOG_DB_FILE)
        cursor = conn.cursor()
        
        login_time = datetime.datetime.now().timestamp()
        status_text = "成功" if status else "失败"
        
        cursor.execute(
            '''
            INSERT INTO login_logs 
            (user_id, username, login_time, ip_address, status)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (user_id, username, login_time, ip_address, status_text)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"登录日志已记录: 用户 {username}({user_id}) {status_text}")
        return True
    except Exception as e:
        logger.error(f"记录登录日志失败: {str(e)}")
        return False 