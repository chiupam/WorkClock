import os
import secrets
import time
from typing import Optional, ClassVar

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 先加载.env文件，确保环境变量可用（仅用于非关键配置）
load_dotenv()

# 启动时间
START_TIME = time.time()

# 从数据库获取设置的函数，移至此文件避免循环导入
def get_setting_from_db(key, default=None):
    """
    从数据库获取设置值
    """
    try:
        import sqlite3
        import os
        
        # 确保数据目录存在
        if not os.path.exists("data"):
            return default
        
        # 数据库文件
        db_file = os.path.join("data", "set.db")
        
        # 如果数据库文件不存在，返回默认值
        if not os.path.exists(db_file):
            return default
        
        # 连接数据库
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 查询设置值
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        
        # 返回查询结果
        if result and result[0]:
            return result[0]
        return default
    except Exception:
        # 出现任何错误，返回默认值
        return default

class Settings(BaseSettings):
    # 环境配置
    APP_ENV: str = os.getenv("APP_ENV", "development")  # 默认为开发环境
    
    # 应用配置
    APP_NAME: str = "考勤系统"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "一个简单的考勤系统后端API"
    # 应用启动时间
    START_TIME: float = START_TIME
        
    # API服务器配置 - 从数据库获取
    API_HOST: Optional[str] = None
    API_URL: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: Optional[str] = "INFO"  # 默认INFO级别
    
    # 管理员配置
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: Optional[str] = None  # 从数据库获取
    # fuckdaka
    FUCK_PASSWORD: Optional[str] = None  # 从数据库获取
    
    # 系统设置状态
    IS_INITIALIZED: bool = False
    
    # CORS配置
    CORS_ORIGINS: list = ["*"]
    
    # 静态文件和模板配置
    STATIC_DIR: str = "app/static"
    TEMPLATES_DIR: str = "app/templates"
    
    # Cookie密钥，用于管理员验证
    COOKIE_SECRET: str = os.getenv("COOKIE_SECRET", secrets.token_hex(16))

    # 定义打卡时间
    MORNING_TIMES: ClassVar = [
        ["08:44", "08:48", "08:52"],  # 第一个用户
        ["08:45", "08:49", "08:53"],  # 第二个用户
        ["08:46", "08:50", "08:54"]   # 第三个用户
    ]

    AFTERNOON_TIMES: ClassVar = [
        ["17:03", "17:15", "17:31"],  # 第一个用户
        ["17:04", "17:16", "17:32"],  # 第二个用户
        ["17:05", "17:17", "17:33"]   # 第三个用户
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 允许额外的字段

    # 自定义初始化，设置依赖于其他配置的值
    def __init__(self, **data):
        super().__init__(**data)
        
        # 从数据库获取API_HOST（不再使用环境变量）
        self.API_HOST = get_setting_from_db("api_host")
        
        # 从数据库获取管理员密码（不再使用环境变量）
        self.ADMIN_PASSWORD = get_setting_from_db("admin_password")
        
        # 从数据库获取FUCKDAKA密码（不再使用环境变量）
        self.FUCK_PASSWORD = get_setting_from_db("fuck_password")
        
        # 检查必要设置是否完成初始化
        self.IS_INITIALIZED = self._check_initialization()
        
        # 设置日志级别 - 无论环境都使用INFO级别，简化逻辑
        self.LOG_LEVEL = "INFO"
        
        # 设置API_URL - 简化URL构建逻辑
        if self.API_HOST:
            api_host = self.API_HOST.strip()
            # 如果已包含协议前缀，直接使用
            if api_host.startswith(("http://", "https://")):
                self.API_URL = api_host
            # 对于包含zhcj的域名，使用https
            elif "zhcj" in api_host:
                self.API_URL = f"https://{api_host}"
            # 其他情况默认使用http
            else:
                self.API_URL = f"http://{api_host}"
        else:
            self.API_URL = None

    def _check_initialization(self):
        """检查系统是否已经初始化"""
        # 检查从数据库读取的关键配置是否已设置
        return bool(self.API_HOST and self.ADMIN_PASSWORD and self.FUCK_PASSWORD)

# 创建配置实例
settings = Settings()
