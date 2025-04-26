import logging

from app import create_app

# 设置 Werkzeug 的日志级别为 INFO，记录请求和操作信息
logging.getLogger('werkzeug').setLevel(logging.INFO)

# 设置根日志级别为 INFO
logging.getLogger().setLevel(logging.INFO)

# 配置应用程序的主要日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # 改为 INFO 级别，记录重要操作信息

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
    