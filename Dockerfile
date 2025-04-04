# 使用 Alpine 作为基础镜像
FROM python:3.9-alpine

# 切换到非 root 用户
USER root

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV FLASK_APP=run.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# 复制项目文件
COPY . .

# # 检查网络连接并配置源
# RUN if ! ping -c 1 google.com > /dev/null 2>&1; then \
#         echo "https://mirrors.aliyun.com/alpine/v3.20/main" > /etc/apk/repositories && \
#         echo "https://mirrors.aliyun.com/alpine/v3.20/community" >> /etc/apk/repositories && \
#         pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
#         pip config set install.trusted-host mirrors.aliyun.com; \
#     fi

# 更新系统并安装依赖
RUN echo "https://mirrors.aliyun.com/alpine/v3.20/main" > /etc/apk/repositories && \
    echo "https://mirrors.aliyun.com/alpine/v3.20/community" >> /etc/apk/repositories && \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com && \
    apk update && apk upgrade && \
    apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 创建实例目录并设置权限
RUN mkdir -p instance && \
    chmod 777 instance && \
    adduser -D appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 9051

# 启动命令
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
