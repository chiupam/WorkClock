# Gunicorn 配置文件
bind = "0.0.0.0:9051"
workers = 1
worker_class = "sync"
timeout = 120
keepalive = 5

# 重启配置
graceful_timeout = 10  # 优雅重启超时时间
# 不再使用基于请求数的重启

# 基于时间的重启配置
reload_extra_files = []  # 需要监控变化的文件列表，为空则只监控时间
reload_engine = "auto"
reload = True  # 启用重载功能
# 每天凌晨3点重启 (使用cron格式：分 时 日 月 星期)
reload_extra_kwargs = {"cron": ["0 3 * * *"]}  # 每天凌晨3点0分重启

# 日志配置
log_level = "info"  # 日志级别
log_file = "-"  # 日志文件路径
log_format = "%(asctime)s - %(levelname)s - %(message)s"  # 日志格式
errorlog = "-"
accesslog = None  # 完全禁用访问日志