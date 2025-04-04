from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()


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
    
    # 确保 instance 目录存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    with app.app_context():
        # 导入所有模型
        from app.models import PermanentToken, SignLog, Logs  # 确保导入所有模型
        
        # 创建主数据库的表
        db.create_all()
        
        # 创建日志数据库的表
        if 'logs' in app.config['SQLALCHEMY_BINDS']:
            db.create_all(bind_key='logs')
    
    from app.routes import main
    app.register_blueprint(main)
    
    return app 