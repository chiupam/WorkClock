# 基于预先构建的基础镜像
FROM chiupam/workclock:base

# 添加VERSION参数
ARG VERSION=unknown
ENV VERSION=${VERSION}

# 使用 root 用户
USER root

# 复制应用代码
COPY . .
EXPOSE 9051

CMD ["python", "-m", "gunicorn", "-c", "gunicorn.conf.py", "run:app"]