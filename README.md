# 🕒 WorkClock - 智慧打卡助手

[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/chiupam/WorkClock/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/badge/issues-0-orange.svg)](https://github.com/chiupam/WorkClock/issues)
[![GitHub stars](https://img.shields.io/badge/stars-0-yellow.svg)](https://github.com/chiupam/WorkClock/stargazers)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker Pulls](https://img.shields.io/badge/docker_pulls-0-blue.svg)](https://hub.docker.com/r/chiupam/workclock-fastapi)

基于 FastAPI 重构的智能打卡辅助系统，提供便捷的考勤管理功能。通过自动化打卡流程，帮助您更高效地管理考勤记录。

> **⚠️ 重要提示**：使用本项目前，请确保正确配置主机地址（HOST）。由于主机地址涉及敏感信息，本文档中已使用"某单位"替代实际单位名称。未正确配置主机地址将导致系统无法正常使用。

## ✨ 功能特点

- 🔄 **自动化打卡** - 支持定时自动打卡，无需手动操作
- 📊 **数据统计** - 直观的打卡记录和统计信息
- 👥 **多用户管理** - 支持多用户和部门管理
- 🔔 **实时通知** - 打卡成功或失败的实时通知
- 🛡️ **安全防护** - 完善的安全机制和数据加密
- 📱 **响应式设计** - 支持各种设备屏幕尺寸
- ⏱️ **考勤统计** - 详细的考勤数据分析与统计功能
- ⏳ **定时倒计时** - 自定义打卡时间与倒计时提醒

## 👨‍💻 作者

**chiupam** - [GitHub](https://github.com/chiupam)

## 🛠️ 技术栈

- **后端框架**: [FastAPI](https://fastapi.tiangolo.com/) - 高性能的现代Python Web框架
- **ASGI服务器**: [Uvicorn](https://www.uvicorn.org/) - 轻量级高性能ASGI服务器
- **模板引擎**: [Jinja2](https://jinja.palletsprojects.com/) - 功能强大的模板引擎
- **数据库**: SQLite - 轻量级文件数据库
- **任务调度**: [APScheduler](https://apscheduler.readthedocs.io/) - 强大的Python任务调度库
- **进程管理**: [PM2](https://pm2.keymetrics.io/) - Node.js进程管理工具
- **容器化**: [Docker](https://www.docker.com/) - 容器化部署方案
- **前端技术**: HTML5, CSS3, JavaScript
- **数据验证**: [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证和设置管理库
- **认证授权**: [python-jose](https://github.com/mpdavis/python-jose), [passlib](https://passlib.readthedocs.io/)

## 📂 项目结构

```
./
├── app/                        # 主应用目录
│   ├── __init__.py             # 应用初始化
│   ├── main.py                 # 主应用入口
│   ├── auth/                   # 认证相关模块
│   │   ├── __init__.py
│   │   ├── dependencies.py     # 认证依赖项
│   │   ├── routes.py           # 认证路由
│   │   └── utils.py            # 认证工具函数
│   ├── routes/                 # 路由模块
│   │   ├── __init__.py
│   │   ├── admin/              # 管理员路由
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py    # 管理员仪表盘
│   │   │   ├── logs.py         # 日志管理
│   │   │   ├── privilege.py    # 权限管理
│   │   │   ├── schedules.py    # 计划任务管理
│   │   │   ├── settings.py     # 系统设置
│   │   │   ├── statistics.py   # 统计数据
│   │   │   ├── system.py       # 系统管理
│   │   │   └── utils.py        # 管理工具函数
│   │   ├── crontab.py          # 定时任务
│   │   ├── index.py            # 主页路由
│   │   ├── setup.py            # 系统设置
│   │   ├── sign.py             # 签到相关
│   │   └── statistics.py       # 统计相关
│   ├── static/                 # 静态资源
│   │   ├── css/                # CSS样式文件
│   │   ├── js/                 # JavaScript文件
│   │   ├── templates/          # HTML模板
│   │   └── favicon.ico         # 网站图标
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── api.py              # API工具
│       ├── db_init.py          # 数据库初始化
│       ├── host.py             # 主机配置
│       ├── log.py              # 日志工具
│       └── settings.py         # 设置管理
├── config.py                   # 全局配置
├── db.sh                       # 数据库脚本
├── docker-compose.yml          # Docker Compose配置
├── docker-entrypoint.sh        # Docker入口脚本
├── Dockerfile                  # Docker构建文件
├── Dockerfile.base             # 基础Docker构建文件
├── ecosystem.config.js         # PM2配置文件
├── requirements.txt            # 项目依赖
└── run.py                      # 应用启动脚本
```

## 🚀 部署方法

本项目仅支持Docker部署，确保您的服务器已安装Docker和Docker Compose。

### Docker部署步骤

1. 克隆仓库到您的服务器：

```bash
git clone https://github.com/chiupam/WorkClock.git
cd WorkClock
```

2. 构建并启动容器：

```bash
docker-compose up -d
```

3. 访问应用：

通过浏览器访问 `http://<服务器IP>:8000` 进入系统，首次访问需要完成系统初始化设置。

### 更新应用

当有新版本发布时，您可以通过以下步骤更新应用：

1. 进入项目目录：

```bash
cd WorkClock
```

2. 拉取最新代码：

```bash
git pull
```

3. 重新构建并启动容器：

```bash
docker-compose down
docker-compose up -d --build
```

也可以通过管理员界面的系统设置页面中的"更新项目代码"按钮一键更新。

## 🧪 本地测试

如果您想在本地测试应用，请按照以下步骤操作：

1. 克隆仓库：

```bash
git clone https://github.com/chiupam/WorkClock.git
cd WorkClock
```

2. 创建并激活虚拟环境：

```bash
python -m venv .venv
# Windows系统
.venv\Scripts\activate
# Linux/macOS系统
source .venv/bin/activate
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 运行应用：

```bash
python run.py
```

5. 访问应用：

通过浏览器访问 `http://localhost:8000` 进入系统。

## 📄 许可证

本项目采用 MIT 许可证 - 详情请查看 [LICENSE](https://github.com/chiupam/WorkClock/blob/main/LICENSE) 文件。

```
MIT License

Copyright (c) 2023 chiupam

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.