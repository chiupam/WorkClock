# 空的初始化文件，使app目录成为一个Python包 

import logging
import os

# 配置基本日志（详细配置会在加载配置后进行）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 设置第三方库的日志级别
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# 设置模块日志
logger = logging.getLogger(__name__)

# 定义数据库文件常量
USER_DB_FILE = "data/user.db" # 用户信息数据库
SIGN_DB_FILE = "data/sign.db" # 签到日志数据库
LOG_DB_FILE = "data/log.db"
SET_DB_FILE = "data/set.db"
CRON_DB_FILE = "data/cron.db"

# 确保data目录存在
data_dir = "data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# 导入数据库初始化模块并执行初始化
from app.utils.db_init import initialize_database

# 初始化数据库
initialize_database()

# 输出初始化消息
logger.info("应用初始化完成")
