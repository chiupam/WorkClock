import datetime
import logging
import os
import sqlite3

from .. import SIGN_DB_FILE, LOG_DB_FILE, SET_DB_FILE, USER_DB_FILE, CRON_DB_FILE

logger = logging.getLogger(__name__)

def initialize_database():
    """初始化所有数据库：创建data目录和相关表"""
    # 确保data目录存在
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 初始化用户数据库
    initialize_user_db()
    
    # 初始化签到日志数据库
    initialize_sign_db()
    
    # 初始化日志数据库
    initialize_log_db()
    
    # 初始化设置数据库
    initialize_settings_db()
    
    # 初始化定时任务数据库
    initialize_cron_db()
    
    return True

def initialize_user_db():
    """初始化用户数据库"""
    # 数据库文件路径

    try:
        # 连接数据库
        conn = sqlite3.connect(USER_DB_FILE)
        cursor = conn.cursor()
        
        # 创建users表（如果不存在）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            user_id TEXT,
            department_name TEXT,
            department_id TEXT,
            position TEXT,
            open_id TEXT,
            first_login_time INTEGER DEFAULT 0,
            last_activity INTEGER DEFAULT 0,
            deleted INTEGER DEFAULT 0
        )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON users (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_open_id ON users (open_id)')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"用户数据库初始化失败: {str(e)}")
        return False

def initialize_sign_db():
    """初始化签到日志数据库"""
    
    try:
        # 连接数据库
        conn = sqlite3.connect(SIGN_DB_FILE)
        cursor = conn.cursor()
        
        # 创建sign_logs表（如果不存在）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sign_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            sign_time REAL NOT NULL,
            sign_type TEXT,
            status TEXT,
            remark TEXT,
            ip_address TEXT DEFAULT '',
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sign_time ON sign_logs (sign_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_username ON sign_logs (username)')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"签到日志数据库初始化失败: {str(e)}")
        return False

def initialize_log_db():
    """初始化日志数据库"""
    try:
        # 连接数据库
        conn = sqlite3.connect(LOG_DB_FILE)
        cursor = conn.cursor()
        
        # 创建login_logs表（如果不存在）- 保留原有表结构
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT,
            login_time REAL NOT NULL,
            ip_address TEXT,
            status TEXT
        )
        ''')
        
        # 创建operation_logs表 - 记录各种操作日志
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,        -- 用户名
            operation_time REAL NOT NULL,  -- 操作时间戳
            operation_type TEXT NOT NULL,  -- 操作类型：LOGIN, VIEW, EDIT, CONFIG, SIGN等
            operation_detail TEXT,         -- 操作详情
            ip_address TEXT,               -- 操作IP
            status TEXT,                   -- 操作状态：成功/失败
            remarks TEXT,                  -- 备注信息
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_time ON operation_logs (operation_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_username ON operation_logs (username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_type ON operation_logs (operation_type)')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"日志数据库初始化失败: {str(e)}")
        return False

def initialize_settings_db():
    """初始化设置数据库"""
    # 数据库文件路径

    try:
        # 连接数据库
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        
        # 创建system_settings表（如果不存在）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            description TEXT,
            updated_at REAL,
            is_initialized BOOLEAN DEFAULT 0
        )
        ''')
        
        # 只插入必要的设置项
        required_settings = [
            ('api_host', '', 'API主机地址', datetime.datetime.now().timestamp(), 0),
            ('admin_password', '', '管理员密码', datetime.datetime.now().timestamp(), 0),
            ('fuck_password', '', 'FuckDaka密码', datetime.datetime.now().timestamp(), 0)
        ]
        
        cursor.executemany('''
        INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description, updated_at, is_initialized)
        VALUES (?, ?, ?, ?, ?)
        ''', required_settings)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"设置数据库初始化失败: {str(e)}")
        return False

def initialize_cron_db():
    """初始化定时任务数据库"""
    # 数据库文件路径
    
    try:
        # 连接数据库
        conn = sqlite3.connect(CRON_DB_FILE)
        cursor = conn.cursor()
            
        # 创建schedules表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            morning BOOLEAN NOT NULL DEFAULT 0,
            afternoon BOOLEAN NOT NULL DEFAULT 0,
            schedule_index INTEGER NOT NULL DEFAULT 0,
            morning_time TEXT,
            afternoon_time TEXT,
            morning_selecte TEXT,
            afternoon_selecte TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON schedules (user_id)')
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"定时任务数据库初始化失败: {str(e)}")
        return False

def reset_cron_db():
    """完全重置cron.db数据库（删除并重新创建）"""
    db_file = "cron.db"
    
    try:
        # 如果数据库文件存在，删除它
        if os.path.exists(db_file):
            # 尝试创建备份
            backup_file = f"{db_file}.bak"
            try:
                import shutil
                shutil.copy2(db_file, backup_file)
                logger.info(f"已备份旧数据库到 {backup_file}")
            except Exception as e:
                logger.warning(f"备份数据库失败: {str(e)}")
                
            # 删除原文件
            os.remove(db_file)
            logger.info(f"已删除旧的数据库文件: {db_file}")
        
        # 重新初始化
        return initialize_cron_db()
    except Exception as e:
        logger.error(f"重置cron数据库失败: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database() 