import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    # 获取当前文件所在目录的绝对路径
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # 主数据库配置（用户token等）
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')

    # 操作日志数据库配置
    SQLALCHEMY_BINDS = {
        'logs': 'sqlite:///' + os.path.join(basedir, 'instance', 'logs.db'),
        'sign': 'sqlite:///' + os.path.join(basedir, 'instance', 'sign.db'),
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 从环境变量获取密钥，如果没有则使用默认值
    SECRET_KEY = os.environ.get('SECRET_KEY', 'abcdef123456!@#$%^')
    
    # 从环境变量获取管理员账号密码
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '1qaz2wsx3edc')
    
    # 从环境变量获取fast密码
    FUCK_PASSWORD = os.environ.get('FUCK_PASSWORD', 'fuckdaka')
    
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    
    # 配置要监视的文件类型
    EXTRA_FILES = ['.py', '.html', '.css', '.js']
    
    # 从环境变量获取为开发环境
    DEVELOPMENT = os.environ.get('DEVELOPMENT', "true").lower() == "true"
    if DEVELOPMENT:
        print("请注意: 当前为开发环境, 使用模拟接口获取数据")
        HOST = "http://127.0.0.1:9051"
    else:
        HOST = os.environ.get('HOST', "")
