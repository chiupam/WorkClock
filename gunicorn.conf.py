# Gunicorn 配置文件
bind = "0.0.0.0:9051"
workers = 1
worker_class = "sync"
loglevel = "debug"
accesslog = "-"  # 输出到标准输出
errorlog = "-"   # 输出到标准错误
capture_output = True
enable_stdio_inheritance = True

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def on_starting(server):
    server.log.info("Starting Gunicorn...")

def on_reload(server):
    server.log.info("Reloading Gunicorn...") 