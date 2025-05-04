FROM chiupam/workclock:base

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY . .

# 创建空的数据目录并设置入口点脚本权限（单层）
RUN mkdir -p data && \
    chmod +x *.sh

# 暴露端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"] 