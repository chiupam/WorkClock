from datetime import datetime

from app import db


class PermanentToken(db.Model):
    """用户设备绑定表 - 使用默认数据库"""
    __tablename__ = 'app'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    user_name = db.Column(db.String(50))
    dep_id = db.Column(db.Integer)
    position = db.Column(db.String(50))
    dep_name = db.Column(db.String(50))
    open_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class SignLog(db.Model):
    """打卡日志表 - 使用logs数据库"""
    __bind_key__ = 'sign'
    __tablename__ = 'sign'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    dep_id = db.Column(db.Integer, nullable=False)
    dep_name = db.Column(db.String(50), nullable=False)
    sign_type = db.Column(db.String(10), nullable=False)
    sign_result = db.Column(db.String(50), nullable=False)
    sign_time = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f'<SignLog {self.user_name} {self.sign_time.strftime("%Y-%m-%d %H:%M:%S")}>'


class Logs(db.Model):
    """日志表 - 使用logs数据库"""
    __bind_key__ = 'logs'
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), nullable=False)
    dep_name = db.Column(db.String(50), nullable=False)
    operation = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    ip_address = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Logs {self.user_name} {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}>'


class ScheduledTask(db.Model):
    """定时任务表 - 使用默认数据库"""
    __tablename__ = 'scheduled_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    dep_id = db.Column(db.Integer, nullable=False)
    dep_name = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    schedule_morning = db.Column(db.Boolean, default=False)  # 早上多个时间点
    schedule_afternoon = db.Column(db.Boolean, default=False)  # 下午多个时间点
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<ScheduledTask {self.user_name} {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}>'


class TaskLog(db.Model):
    """定时任务日志表 - 使用logs数据库"""
    __bind_key__ = 'logs'
    __tablename__ = 'task_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(50), nullable=False)
    dep_id = db.Column(db.Integer, nullable=False)
    dep_name = db.Column(db.String(50), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)  # morning, afternoon
    task_time = db.Column(db.String(10), nullable=False)  # 格式: HH:MM
    status = db.Column(db.String(20), nullable=False)  # scheduled, running, success, failed
    message = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<TaskLog {self.user_name} {self.task_type} {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}>'
    