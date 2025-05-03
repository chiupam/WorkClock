#!/bin/sh
set -e

echo "启动脚本开始执行..."

# 初始化数据库
echo "正在初始化数据库..."
python -c "from app.utils.db_init import initialize_database; initialize_database()"

# 检查标记并清除
if [ -f "/app/data/needs_restart" ]; then
    echo "启动时发现重启标记文件，清除标记"
    rm -f "/app/data/needs_restart"
fi

if [ -f "/app/data/needs_update" ]; then
    echo "启动时发现更新标记文件，清除标记"
    rm -f "/app/data/needs_update"
fi

# 检查PM2是否安装
which pm2 >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "错误: PM2未安装，请确保基础镜像中已安装PM2"
    exit 1
fi

# 检查ecosystem.config.js是否存在
if [ ! -f "/app/ecosystem.config.js" ]; then
    echo "错误: 找不到PM2配置文件 ecosystem.config.js"
    exit 1
fi

# 使用PM2启动应用
echo "使用PM2启动应用..."
echo "当前工作目录: $(pwd)"
echo "配置文件内容:"
cat ecosystem.config.js

# 启动前删除旧的PM2进程和日志
pm2 delete all 2>/dev/null || true
rm -rf /root/.pm2/logs/* 2>/dev/null || true

# 启动应用
exec pm2-runtime ecosystem.config.js 