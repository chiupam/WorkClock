import logging

from app import create_app

# 设置 Werkzeug 的日志级别为 DEBUG，显示所有访问日志
logging.getLogger('werkzeug').setLevel(logging.DEBUG)

# 设置根日志级别为 DEBUG
logging.getLogger().setLevel(logging.DEBUG)

# 配置应用程序的主要日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 改为 DEBUG 级别，显示所有日志信息

try:
    app = create_app()
    
    if __name__ == '__main__':
        app.run(
            debug=True, 
            host='0.0.0.0', 
            port=9051
        )
except Exception as e:
    logger.error(f"启动失败: {str(e)}")
    raise e
    