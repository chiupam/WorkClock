# 某单位 - 智慧打卡助手

[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/chiupam/WorkClock/blob/main/LICENSE)
[![GitHub release](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/chiupam/WorkClock/releases/tag/v1.0.0)
[![GitHub issues](https://img.shields.io/badge/issues-0-orange.svg)](https://github.com/chiupam/WorkClock/issues)
[![GitHub stars](https://img.shields.io/badge/stars-0-yellow.svg)](https://github.com/chiupam/WorkClock/stargazers)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker Pulls](https://img.shields.io/badge/docker_pulls-0-blue.svg)](https://hub.docker.com/r/chiupam/workclock)

一个基于 Flask 的智能打卡辅助系统，提供便捷的考勤管理功能。

> **重要提示**：使用本项目前，请确保正确配置主机地址（HOST）。由于主机地址涉及敏感信息，本文档中已使用"某单位"替代实际单位名称。未正确配置主机地址将导致系统无法正常使用。

## 作者

**chiupam** - [GitHub](https://github.com/chiupam)

## 功能特性

### 用户功能
- 登录系统
  - 手机号密码登录
  - Token 持久化存储
  - 自动登录（Cookie 记住登录状态）
  - 快捷登录（fuckdaka 模式）

- 打卡功能
  - 一键快速打卡
  - 智能判断上下班时间（7:00-9:00 上班打卡，17:00-23:59 下班打卡）
  - 自动记录打卡位置
  - 打卡结果实时反馈
  - 休息日智能提示
  
- 考勤记录
  - 查看当日打卡记录
  - 显示标准打卡时间
  - 智能提醒补卡
  - 显示打卡地点信息

- 考勤统计
  - 按月份查看考勤记录
  - 显示节假日信息
  - 显示请假记录
  - 区分正常打卡和补卡
  - 实时显示待打卡状态
  - 智能隐藏未来日期

### 管理员功能
- 日志管理
  - 查看打卡日志
  - 查看操作日志
  - 查看数据库绑定记录
  
- 超级打卡
  - 部门人员管理
  - 快速切换用户
  - 临时授权管理

## 技术栈

### 后端
- Python 3.9+
- Flask Web 框架
- SQLAlchemy ORM
- Flask-Login 用户认证
- Flask-SSE（服务器发送事件）
- Gunicorn WSGI 服务器

### 前端
- 原生 JavaScript
- CSS3 动画
- 响应式设计
- SVG 图标系统
- 实时状态更新

### 数据库
- SQLite（支持多数据库）
  - app.db：用户主数据库
  - logs.db：操作日志数据库
  - sign.db：签到日志数据库

### 安全
- Cookie 加密存储
- Session 管理
- CSRF 防护
- XSS 防护
- 请求参数验证
- 用户状态持久化

## 快速开始

### Docker 快速部署
```bash
# 拉取镜像
docker pull chiupam/workclock:latest

# 运行容器
docker run -d \
  --name workclock \
  -p 9051:9051 \
  -e SECRET_KEY=yoursecretkey \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=yourpassword \
  -e DEVELOPMENT=false \
  -e HOST=https://your-domain.com \
  -e FUCK_PASSWORD=fastloginpassword \
  chiupam/workclock:latest
```

## 系统要求

### 环境依赖
```txt
Flask
Flask-Login
Flask-SQLAlchemy
Flask-SSE
gunicorn
requests
cryptography
python-dotenv
```

## 部署说明

### Docker 手动构建部署
```shell
# 克隆代码
git clone https://github.com/chiupam/WorkClock.git
cd WorkClock

# 构建镜像
docker build -t workclock:latest .

# 运行容器
docker run -d \
  --name workclock \
  --privileged \
  -p 9051:9051 \
  -e SECRET_KEY=yoursecretkey \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=yourpassword \
  -e DEVELOPMENT=false \
  -e HOST=https://your-domain.com \
  -e FUCK_PASSWORD=fastloginpassword \
  -v $(pwd)/instance:/app/instance \
  workclock:latest

# 进入容器
docker exec -it workclock sh
```

### 环境变量配置
- SECRET_KEY：应用密钥
- ADMIN_USERNAME：管理员用户名
- ADMIN_PASSWORD：管理员密码
- DEVELOPMENT：开发环境标志（true/false）
- HOST：API 主机地址（**生产环境必填**，格式如：https://example.com）
- FUCK_PASSWORD：快速打卡密码

> **⚠️ 重要提示**：在生产环境（DEVELOPMENT=false）中，必须设置 HOST 环境变量，否则系统将无法正常工作。HOST 应该是完整的 URL 地址，包含协议（http/https）。

## 项目架构

```
WorkClock/                          # 项目根目录
├── .github/                        # GitHub 配置目录
│   └── workflows/                  # GitHub Actions 工作流
│       └── docker-publish.yml      # Docker 构建发布工作流
├── app/                            # 应用主目录
│   ├── __init__.py                 # 应用初始化文件
│   ├── ciphertext.py               # 加密相关功能
│   ├── models.py                   # 数据库模型定义
│   ├── routes.py                   # 路由和视图函数
│   ├── static/                     # 静态资源目录
│   │   ├── css/                    # CSS 样式文件
│   │   │   ├── dashboard.css       # 仪表盘页面样式
│   │   │   ├── database.css        # 数据库页面样式
│   │   │   ├── dep.css             # 部门页面样式
│   │   │   ├── index.css           # 首页样式
│   │   │   ├── root.css            # 管理员页面样式
│   │   │   └── super.css           # 超级管理员页面样式
│   │   └── favicon.ico             # 网站图标
│   └── templates/                  # HTML 模板目录
│       ├── dashboard.html          # 仪表盘页面模板
│       ├── database.html           # 数据库页面模板
│       ├── dep.html                # 部门页面模板
│       ├── index.html              # 首页模板
│       ├── operation.html          # 操作页面模板
│       ├── root.html               # 管理员页面模板
│       └── super.html              # 超级管理员页面模板
├── instance/                       # 实例配置目录
│   ├── app.db                      # 主应用数据库
│   ├── logs.db                     # 日志数据库
│   └── sign.db                     # 签到数据库
├── .dockerignore                   # Docker 忽略文件
├── .gitignore                      # Git 忽略文件
├── Dockerfile                      # Docker 构建文件
├── LICENSE                         # MIT 许可证文件
├── README.md                       # 项目说明文档
├── config.py                       # 应用配置文件
├── database.py                     # 数据库操作文件
├── gunicorn.conf.py                # Gunicorn 服务器配置
├── requirements.txt                # Python 依赖清单
└── run.py                          # 应用入口文件
```

## 本地开发

1. 克隆项目
```bash
git clone https://github.com/chiupam/WorkClock.git
cd WorkClock
```

2. 创建并激活虚拟环境
```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
## macOS/Linux
source .venv/bin/activate
## Windows
.venv\Scripts\activate
```

3. 安装项目依赖
```bash
# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

4. 设置环境变量（两种方式）

方式一：使用 .env 文件（推荐）
```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，修改相关配置
vim .env  # 或使用其他编辑器
```

方式二：直接设置环境变量
```bash
# macOS/Linux
export SECRET_KEY="开发密钥"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="管理员密码"
export DEVELOPMENT="true"
export HOST="主机地址"
export FUCK_PASSWORD="快速打卡密码"

# Windows (PowerShell)
$env:SECRET_KEY="开发密钥"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="管理员密码"
$env:DEVELOPMENT="true"
$env:HOST="主机地址"
$env:FUCK_PASSWORD="快速打卡密码"
```

5. 运行开发服务器
```bash
python run.py
```

6. 访问应用
- 打开浏览器访问：`http://localhost:9051`
- 使用设置的管理员账号密码登录

7. 开发完成后
```bash
# 停止开发服务器：Ctrl+C
# 退出虚拟环境
deactivate
```

## 注意事项
- 确保 instance 目录有写入权限
- 生产环境必须修改默认密钥
- 建议定期备份数据库
- 注意保护管理员密码和 FUCK_PASSWORD

## 贡献
欢迎提交 Issues 和 Pull Requests 来改进项目。

## 许可证
本项目采用 [MIT 许可证](LICENSE)。