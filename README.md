# 🕒 WorkClock - 智慧打卡助手

[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/chiupam/WorkClock/blob/main/LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/chiupam/WorkClock)](https://github.com/chiupam/WorkClock/releases/latest)
[![GitHub issues](https://img.shields.io/badge/issues-0-orange.svg)](https://github.com/chiupam/WorkClock/issues)
[![GitHub stars](https://img.shields.io/badge/stars-0-yellow.svg)](https://github.com/chiupam/WorkClock/stargazers)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker Pulls](https://img.shields.io/badge/docker_pulls-0-blue.svg)](https://hub.docker.com/r/chiupam/workclock)

一个基于 Flask 的智能打卡辅助系统，提供便捷的考勤管理功能。通过自动化打卡流程，帮助您更高效地管理考勤记录。

> **⚠️ 重要提示**：使用本项目前，请确保正确配置主机地址（HOST）。由于主机地址涉及敏感信息，本文档中已使用"某单位"替代实际单位名称。未正确配置主机地址将导致系统无法正常使用。

## ✨ 功能特点

- 🔄 **自动化打卡** - 支持定时自动打卡，无需手动操作
- 📊 **数据统计** - 直观的打卡记录和统计信息
- 👥 **多用户管理** - 支持多用户和部门管理
- 🔔 **实时通知** - 打卡成功或失败的实时通知
- 🛡️ **安全防护** - 完善的安全机制和数据加密
- 📱 **响应式设计** - 支持各种设备屏幕尺寸

## 👨‍💻 作者

**chiupam** - [GitHub](https://github.com/chiupam)

## 🛠️ 技术栈

### 后端
- 🐍 Python 3.9+
- 🌶️ Flask Web 框架
- 🗄️ SQLAlchemy ORM
- 🔐 Flask-Login 用户认证
- 📡 Flask-SSE（服务器发送事件）
- 🦄 Gunicorn WSGI 服务器

### 前端
- 📜 原生 JavaScript
- 🎨 CSS3 动画
- 📱 响应式设计
- 🖼️ SVG 图标系统
- ⚡ 实时状态更新

### 数据库
- 💾 SQLite（支持多数据库）
  - `app.db`：用户主数据库
  - `logs.db`：操作日志数据库
  - `sign.db`：签到日志数据库

### 安全
- 🔒 Cookie 加密存储
- 🛡️ Session 管理
- 🔰 CSRF 防护
- 🛑 XSS 防护
- 🧪 请求参数验证
- 💫 用户状态持久化

## 🚀 快速开始

### Docker 快速部署

```bash
docker run -d \
  --name workclock \
  -p 9051:9051 \
  -e SECRET_KEY=yoursecretkey \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=yourpassword \
  -e DEVELOPMENT=false \
  -e HOST=https://your-domain.com \
  -e FUCK_PASSWORD=fastloginpassword \
  -e VERSION=v1.0.0 \
  -v $(pwd)/instance:/app/instance \
  chiupam/workclock:latest
```

## ⚙️ 环境变量配置

| 环境变量 | 说明 | 默认值 | 是否必填 |
|---------|------|-------|----------|
| SECRET_KEY | 应用密钥 | abcdef123456!@#$%^ | 生产环境必填 |
| ADMIN_USERNAME | 管理员用户名 | admin | 否 |
| ADMIN_PASSWORD | 管理员密码 | 1qaz2wsx3edc | 生产环境必填 |
| DEVELOPMENT | 开发环境标志 | true | 否 |
| HOST | API 主机地址 | - | 生产环境必填 |
| FUCK_PASSWORD | 快速打卡密码 | fuckdaka | 否 |
| VERSION | 应用版本号 | - | 否 |

> **⚠️ 注意**：在生产环境（DEVELOPMENT=false）中，必须设置 HOST 环境变量，否则系统将无法正常工作。HOST 应该是完整的 URL 地址，包含协议（http/https）。

## 🏗️ 项目架构

```
WorkClock/                          # 项目根目录
├── app/                            # 应用主目录
│   ├── __init__.py                 # 应用初始化文件
│   ├── models.py                   # 数据库模型定义
│   ├── routes.py                   # 路由和视图函数
│   ├── scheduler.py                # 定时任务调度器
│   ├── system.py                   # 系统管理功能
│   ├── static/                     # 静态资源目录
│   │   ├── css/                    # CSS 样式文件
│   │   ├── js/                     # JavaScript 文件
│   │   └── favicon.ico             # 网站图标
│   └── templates/                  # HTML 模板目录
├── Dockerfile                      # Docker 构建文件
├── docker-compose.yml              # Docker Compose 配置
├── config.py                       # 应用配置文件
├── gunicorn.conf.py                # Gunicorn 服务器配置
├── requirements.txt                # Python 依赖清单
└── run.py                          # 应用入口文件
```

## 💻 本地开发

1. **克隆项目**
```bash
git clone https://github.com/chiupam/WorkClock.git
cd WorkClock
```

2. **创建并激活虚拟环境**
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Linux/macOS
source .venv/bin/activate
# Windows(CMD)
.venv\Scripts\activate
# Windows(PowerShell)
.venv\Scripts\Activate.ps1
```

3. **安装项目依赖**
```bash
# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

4. **设置环境变量**
```bash
# Linux/macOS
export DEVELOPMENT=true
export VERSION=v1.0.0-dev

# Windows(CMD)
set DEVELOPMENT=true
set VERSION=v1.0.0-dev

# Windows(PowerShell)
$env:DEVELOPMENT="true"
$env:VERSION="v1.0.0-dev"
```

5. **运行开发服务器**
```bash
python run.py
```

6. **访问应用**
- 打开浏览器访问：`http://localhost:9051`
- 使用默认管理员账号密码登录：admin/1qaz2wsx3edc

## 📞 支持与帮助

如果您在使用过程中遇到任何问题，可以通过以下方式获取帮助：

- 🔍 [提交 Issue](https://github.com/chiupam/WorkClock/issues)

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE)。