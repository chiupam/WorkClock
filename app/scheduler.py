import atexit
import logging
import os
import random
import requests
import signal
import socket
import tempfile
import time
from datetime import datetime
from flask import current_app
from flask_apscheduler import APScheduler

# 以下导入在函数内使用，避免循环引用
from app import create_app
from app import db
from app.models import ScheduledTask, TaskLog

# 注意：fast_sign和add_sign_log依赖于app上下文，需要在函数内导入

# 创建APScheduler实例
scheduler = APScheduler()

# 设置日志器
logger = logging.getLogger(__name__)
# 设置日志级别为INFO，记录任务执行信息
logger.setLevel(logging.INFO)

# 全局变量，用于确保调度器只初始化一次
_scheduler_initialized = False
_scheduler_pid_file = os.path.join(tempfile.gettempdir(), 'workclock_scheduler.pid')
_is_master_process = False
_lock_refresh_interval = 60  # 锁刷新间隔（秒）
_last_lock_refresh = 0

def acquire_scheduler_lock() -> bool:
    """
    尝试获取调度器进程锁
    :return: 是否成功获取锁
    """
    global _is_master_process, _last_lock_refresh
    
    try:
        # 检查pid文件是否存在
        if os.path.exists(_scheduler_pid_file):
            with open(_scheduler_pid_file, 'r') as f:
                pid_data = f.read().strip().split(':')
                if len(pid_data) >= 2:
                    pid = pid_data[0]
                    hostname = pid_data[1]
                    timestamp = float(pid_data[2]) if len(pid_data) > 2 else 0
                    
                    # 检查时间戳是否已过期（5分钟超时）
                    if time.time() - timestamp < 300:
                        # 检查进程是否存在
                        try:
                            pid = int(pid)
                            # 检查进程是否在同一主机上
                            current_hostname = socket.gethostname()
                            if hostname != current_hostname:
                                # logger.info(f"调度器已由主机 {hostname} 的进程 {pid} 运行，当前进程不会启动调度器")
                                return False
                            
                            # 使用Linux方式检查进程是否存在
                            os.kill(pid, 0)
                            # 进程存在，我们不是主进程
                            # logger.info(f"调度器已由进程 {pid} 运行，当前进程不会启动调度器")
                            return False
                        except (ValueError, OSError, ProcessLookupError):
                            # 进程不存在，继续尝试获取锁
                            pass
        
        # 获取当前进程ID并写入文件
        current_pid = os.getpid()
        current_hostname = socket.gethostname()
        current_time = time.time()
        _last_lock_refresh = current_time
        
        with open(_scheduler_pid_file, 'w') as f:
            f.write(f"{current_pid}:{current_hostname}:{current_time}")
        
        # 添加退出处理程序
        def cleanup_pid_file():
            try:
                if os.path.exists(_scheduler_pid_file):
                    with open(_scheduler_pid_file, 'r') as f:
                        pid_data = f.read().strip().split(':')
                        if len(pid_data) >= 2 and pid_data[0] == str(current_pid) and pid_data[1] == current_hostname:
                            os.remove(_scheduler_pid_file)
                            logger.info("调度器进程锁已释放")
            except Exception as e:
                logger.error(f"清理调度器进程锁失败: {str(e)}")
        
        # 注册退出函数
        atexit.register(cleanup_pid_file)
        
        # 注册信号处理
        def handle_exit_signal(signum, frame):
            cleanup_pid_file()
            # 重新发送信号
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
        
        # 注册终止信号的处理函数
        signal.signal(signal.SIGTERM, handle_exit_signal)
        signal.signal(signal.SIGQUIT, handle_exit_signal)
        
        # 成功获取锁
        _is_master_process = True
        logger.info(f"当前进程 {current_pid} 已成为调度器主进程")
        return True
        
    except Exception as e:
        logger.error(f"获取调度器进程锁失败: {str(e)}")
        return False

def refresh_scheduler_lock():
    """
    刷新调度器进程锁，防止锁超时
    """
    global _last_lock_refresh, _is_master_process
    
    # 只有主进程需要刷新锁
    if not _is_master_process:
        return
        
    # 检查是否需要刷新锁
    current_time = time.time()
    if current_time - _last_lock_refresh < _lock_refresh_interval:
        return
        
    try:
        # 检查锁是否仍然属于我们
        if os.path.exists(_scheduler_pid_file):
            with open(_scheduler_pid_file, 'r') as f:
                pid_data = f.read().strip().split(':')
                if len(pid_data) >= 2:
                    pid = pid_data[0]
                    hostname = pid_data[1]
                    
                    # 验证锁是否仍然属于当前进程
                    if pid == str(os.getpid()) and hostname == socket.gethostname():
                        # 更新时间戳
                        _last_lock_refresh = current_time
                        with open(_scheduler_pid_file, 'w') as f:
                            f.write(f"{pid}:{hostname}:{current_time}")
                    else:
                        # 锁已被其他进程获取
                        logger.warning(f"调度器锁已被进程 {pid} 获取，当前进程不再是主进程")
                        _is_master_process = False
    except Exception as e:
        logger.error(f"刷新调度器进程锁失败: {str(e)}")

def check_sign_time(hour, minute) -> bool:
    """
    检查当前时间是否在允许打卡的时间段内
    :param hour: 小时
    :param minute: 分钟
    :return: 是否允许打卡
    """
    # 上班时间: 7:00-9:00 (包含9:00), 下班时间: 17:00-23:59 (包含17:00)
    if 7 <= hour < 9 or (hour == 9 and minute == 0):
        # 上班打卡时间段
        return True
    elif 17 <= hour <= 23:
        # 下班打卡时间段
        return True
    
    # 不在允许打卡的时间段内
    return False


def check_working_day(user_id) -> bool:
    """
    检查今天是否是工作日
    :param user_id: 用户ID
    :return: 是否是工作日
    """
    try:
        now = datetime.now()
        params = {
            "AttType": "1", 
            "UnitCode": "530114", 
            "userid": user_id, 
            "Mid": "134",
            "year": f"{now.year}年", 
            "month": f"{str(now.month).zfill(2)}月"
        }
        
        # 定义默认User-Agent
        default_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
        
        response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/GetYueTjList",
            headers={'User-Agent': default_ua},
            params=params,
            json={},
            allow_redirects=False
        )
        response.raise_for_status()
        # 检查今天是否是工作日
        working = bool(response.json()[now.day - 1]['isworkingday'])
        return working
    except Exception as e:
        logger.error(f"检查工作日状态失败: {str(e)}")
        # 如果无法确定，默认为工作日以确保不会错过打卡
        return True


def check_attendance_status(user_id, task_type) -> bool:
    """
    检查用户当前的打卡状态
    :param user_id: 用户ID
    :param task_type: 任务类型 (morning/afternoon)
    :return: 是否需要打卡 (True表示需要打卡，False表示已打卡或其他原因不需要打卡)
    """
    try:
        params = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}
        
        # 定义默认User-Agent
        default_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
        
        response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/GetAttCheckinoutList",
            params=params,
            headers={'User-Agent': default_ua},
            allow_redirects=False
        )
        response.raise_for_status()
        
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 过滤出当天的记录
        today_records = []
        for record in response.json():
            timestamp = int(record['clockTime'].replace('/Date(', '').replace(')/', ''))
            record_date = datetime.fromtimestamp(timestamp / 1000)
            if record_date.date() == today.date():
                today_records.append(record)
        
        # 分离上班下班记录
        clock_in = next((record for record in today_records if record['clockType'] == 1), None)
        clock_out = next((record for record in today_records if record['clockType'] == 2), None)
        
        # 根据任务类型判断是否需要打卡
        if task_type == "morning" and not clock_in:
            return True  # 上午需要打卡
        elif task_type == "afternoon" and not clock_out:
            return True  # 下午需要打卡
        else:
            return False  # 已完成相应时段的打卡
            
    except Exception as e:
        logger.error(f"检查打卡状态失败: {str(e)}")
        # 如果无法确定，默认为需要打卡
        return True


def scheduled_sign(user_id, dep_id, user_name, dep_name):
    """
    执行定时打卡
    :param user_id: 用户ID
    :param dep_id: 部门ID
    :param user_name: 用户名
    :param dep_name: 部门名称
    """
    try:
        # 使用logger记录日志
        logger.info(f"执行定时打卡任务: 用户 {user_name}({user_id})")
        
        # 创建一个新的应用实例并明确使用其上下文
        app = create_app()
        with app.app_context():
            # 在这里导入，避免循环引用
            from app.routes import fast_sign, add_sign_log
            
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            
            # 确定任务类型
            task_type = "morning" if hour < 12 else "afternoon"
            task_time = f"{hour:02d}:{minute:02d}"
            
            # 记录任务开始执行
            task_log = TaskLog(
                user_id=user_id,
                user_name=user_name,
                dep_id=dep_id,
                dep_name=dep_name,
                task_type=task_type,
                task_time=task_time,
                status="running"
            )
            db.session.add(task_log)
            db.session.commit()
            
            # 检查今天是否是工作日
            if not check_working_day(user_id):
                logger.info(f"今天是非工作日，跳过定时打卡")
                add_sign_log(user_id, user_name, dep_id, dep_name, "定时", "非工作日")
                
                # 更新任务状态
                task_log.status = "skipped"
                task_log.message = "今天是非工作日"
                db.session.commit()
                return
            
            # 检查是否可以打卡
            if not check_sign_time(hour, minute):
                logger.info(f"当前时间不在打卡时间段内，跳过定时打卡")
                add_sign_log(user_id, user_name, dep_id, dep_name, "定时", "时间段不允许")
                
                # 更新任务状态
                task_log.status = "failed"
                task_log.message = "当前时间不在打卡时间段内"
                db.session.commit()
                return
            
            # 检查是否已经打过卡
            if not check_attendance_status(user_id, task_type):
                logger.info(f"用户已完成该时段打卡，跳过定时打卡")
                add_sign_log(user_id, user_name, dep_id, dep_name, "定时", "已完成打卡")
                
                # 更新任务状态
                task_log.status = "skipped"
                task_log.message = "用户已完成该时段打卡"
                db.session.commit()
                return
            
            # 添加随机等待时间(0-40秒)，使打卡时间更自然
            wait_seconds = random.randint(0, 40)
            logger.info(f"随机等待{wait_seconds}秒后执行打卡")
            time.sleep(wait_seconds)
            
            # 执行打卡
            result = fast_sign(user_id, dep_id)
            
            # 记录打卡日志
            sign_type = "上班" if hour < 12 else "下班"
            if result.get("success", False):
                add_sign_log(user_id, user_name, dep_id, dep_name, f"定时{sign_type}", "成功")
                logger.info(f"定时{sign_type}打卡成功: {user_name}({user_id})")
                
                # 更新任务状态为成功
                task_log.status = "success"
                task_log.message = f"{sign_type}打卡成功"
                db.session.commit()
            else:
                add_sign_log(user_id, user_name, dep_id, dep_name, f"定时{sign_type}", f"失败: {result.get('message', '未知错误')}")
                logger.info(f"定时{sign_type}打卡失败: {user_name}({user_id}), 原因: {result.get('message', '未知错误')}")
                
                # 更新任务状态为失败
                task_log.status = "failed"
                task_log.message = f"{sign_type}打卡失败: {result.get('message', '未知错误')}"
                db.session.commit()
    
    except Exception as e:
        logger.error(f"定时打卡错误: {str(e)}")
        try:
            # 如果出错，创建一个新的app上下文来记录错误
            app = create_app()
            with app.app_context():
                # 这里延迟导入，避免循环引用
                from app.routes import add_sign_log
                
                add_sign_log(user_id, user_name, dep_id, dep_name, "定时", f"错误: {str(e)}")
                logger.error(f"详细错误追踪: {e.__class__.__name__}, {e}")
                
                # 记录任务错误
                now = datetime.now()
                task_type = "morning" if now.hour < 12 else "afternoon"
                task_time = f"{now.hour:02d}:{now.minute:02d}"
                
                task_log = TaskLog(
                    user_id=user_id,
                    user_name=user_name,
                    dep_id=dep_id,
                    dep_name=dep_name,
                    task_type=task_type,
                    task_time=task_time,
                    status="failed",
                    message=f"执行错误: {str(e)}"
                )
                db.session.add(task_log)
                db.session.commit()
        except Exception as inner_e:
            logger.error(f"记录错误日志失败: {str(inner_e)}")


def setup_scheduled_tasks():
    """
    配置所有定时任务
    """
    app = current_app._get_current_object()
    
    # 清除现有的定时任务
    scheduler.remove_all_jobs()
    
    # 查询所有启用的定时任务，按创建时间排序以确定先后顺序
    tasks = ScheduledTask.query.filter_by(enabled=True).order_by(ScheduledTask.created_at).all()
    
    # 从配置中获取打卡时间和最大用户数
    morning_times_by_user = current_app.config.get('MORNING_TIMES_BY_USER')
    afternoon_times_by_user = current_app.config.get('AFTERNOON_TIMES_BY_USER')
    max_users = current_app.config.get('MAX_SCHEDULED_USERS', 3)
    
    # 过滤已禁用或未设置任何打卡的任务
    active_tasks = [task for task in tasks if task.enabled and (task.schedule_morning or task.schedule_afternoon)]
    
    # 设置新的定时任务
    for idx, task in enumerate(active_tasks):
        # 如果超过配置的最大用户数，不添加更多任务
        if idx >= max_users:
            break
            
        # 获取当前用户的早上和下午打卡时间
        morning_times = morning_times_by_user[idx]
        afternoon_times = afternoon_times_by_user[idx]
        
        # 早上打卡设置 (多个时间点)
        if task.schedule_morning:
            for time_idx, (hour, minute) in enumerate(morning_times):
                scheduler.add_job(
                    id=f'morning_{task.user_id}_{time_idx}',
                    func=scheduled_sign,
                    args=[task.user_id, task.dep_id, task.user_name, task.dep_name],
                    trigger='cron',
                    hour=hour,
                    minute=minute
                )
                app.logger.info(f"已设置定时任务: morning_{task.user_id}_{time_idx}, 每天 {hour:02d}:{minute:02d} 执行")
        
        # 下午打卡 (多个时间点)
        if task.schedule_afternoon:
            for time_idx, (hour, minute) in enumerate(afternoon_times):
                scheduler.add_job(
                    id=f'afternoon_{task.user_id}_{time_idx}',
                    func=scheduled_sign,
                    args=[task.user_id, task.dep_id, task.user_name, task.dep_name],
                    trigger='cron',
                    hour=hour,
                    minute=minute
                )
                app.logger.info(f"已设置定时任务: afternoon_{task.user_id}_{time_idx}, 每天 {hour:02d}:{minute:02d} 执行")
    
    app.logger.info(f"已配置 {min(len(active_tasks), max_users)} 个用户的定时任务")


def init_scheduler(app):
    """
    初始化调度器
    :param app: Flask应用实例
    """
    global _scheduler_initialized
    
    # 如果调度器已初始化，则跳过
    if _scheduler_initialized:
        return
    
    # 尝试获取进程锁
    is_master = acquire_scheduler_lock()
    
    # 配置APScheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    # 设置为中国时区
    app.config['SCHEDULER_TIMEZONE'] = "Asia/Shanghai"
    
    # 设置日志级别为INFO，显示任务调度信息
    logging.getLogger('apscheduler').setLevel(logging.INFO)
    
    # 初始化调度器
    scheduler.init_app(app)
    
    # 只有主进程才启动调度器和设置任务
    if is_master:
        scheduler.start()
        
        # 创建数据库表 - 使用try-except捕获表已存在的错误
        with app.app_context():
            try:
                db.create_all()
                setup_scheduled_tasks()
            except Exception as e:
                # 如果表已存在，只记录日志而不中断程序
                logger.warning(f"创建数据库表时出现警告 (可能表已存在): {str(e)}")
                # 继续设置任务
                setup_scheduled_tasks()
        
        # 添加一个锁刷新任务
        scheduler.add_job(
            id='lock_refresh',
            func=refresh_scheduler_lock,
            trigger='interval',
            seconds=30
        )
        
        app.logger.info("定时任务调度器已启动")
    
    # 标记为已初始化
    _scheduler_initialized = True 