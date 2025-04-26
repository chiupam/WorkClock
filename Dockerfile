# 构建阶段
FROM python:3.9-alpine3.15 AS builder

WORKDIR /build
COPY requirements.txt .

RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev libffi-dev && \
    pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 运行阶段
FROM python:3.9-alpine3.15

# 添加VERSION参数
ARG VERSION=unknown

WORKDIR /app
ENV FLASK_APP=run.py \
    FLASK_DEBUG=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai \
    PATH="/usr/local/bin:$PATH" \
    VERSION=${VERSION}

# 复制并安装依赖
COPY --from=builder /wheels /wheels
RUN apk add --no-cache tzdata musl-dev libffi-dev linux-headers && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels && \
    adduser -D appuser && \
    mkdir -p instance && \
    chmod 777 instance && \
    mkdir -p /app/repo /app/temp_extract && \
    chown appuser:appuser /app/repo /app/temp_extract && \
    chmod 755 /app/repo /app/temp_extract

# 复制应用代码
COPY --chown=appuser:appuser . .
EXPOSE 9051

CMD ["python", "-m", "gunicorn", "-c", "gunicorn.conf.py", "run:app"]
