import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_sse import sse
from flask_socketio import SocketIO

from config import Config

db = SQLAlchemy()
socketio = SocketIO()


def create_app(config_class=Config):
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    app.config.from_object(config_class)
    
    # 确保设置了 SECRET_KEY
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-key-123'
    
    # 禁用 remember cookie
    app.config['REMEMBER_COOKIE_ENABLED'] = False
    
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 确保 instance 目录存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    with app.app_context():
        # 使用try-except捕获表已存在的错误
        try:
            db.create_all()
            if 'sign' in app.config.get('SQLALCHEMY_BINDS', {}):
                db.create_all(bind_key='sign')
            if 'logs' in app.config.get('SQLALCHEMY_BINDS', {}):
                db.create_all(bind_key='logs')
        except Exception as e:
            app.logger.warning(f"创建数据库表时出现警告 (可能表已存在): {str(e)}")
    
    from app.routes import main, register_system_socket
    app.register_blueprint(main)
    app.register_blueprint(sse, url_prefix='/stream')
    
    # 注册WebSocket处理器
    register_system_socket(socketio)
    
    # 初始化APScheduler
    from app.scheduler import init_scheduler
    init_scheduler(app)
    
    @app.after_request
    def add_header(response):
        """
        添加响应头
        :param response: 响应对象
        :return: 响应对象
        """
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    return app 