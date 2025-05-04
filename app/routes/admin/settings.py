import datetime
import sqlite3
import os
import subprocess

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import SET_DB_FILE, logger
from app.auth.dependencies import admin_required
from app.routes.admin.utils import get_admin_stats, get_admin_name, templates
from app.routes.admin.system import trigger_restart_after_setup
from config import Settings
from config import settings

# 创建路由器
router = APIRouter()

@router.get("/settings")
@admin_required
async def admin_settings_page(request: Request):
    """
    管理员系统设置页面
    """
    
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回设置页面
    return templates.TemplateResponse(
        "admin/settings.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "系统设置",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@router.get("/settings-api")
@admin_required
async def get_settings_api(request: Request):
    """
    获取系统设置API
    """
    try:
        # 连接数据库
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        
        # 获取所有设置
        cursor.execute("SELECT setting_key, setting_value, description FROM system_settings")
        settings_data = cursor.fetchall()
        
        # 格式化设置数据
        formatted_settings = {}
        for setting in settings_data:
            formatted_settings[setting[0]] = {
                "value": setting[1],
                "description": setting[2]
            }
        
        conn.close()
        
        return JSONResponse({
            "success": True,
            "settings": formatted_settings
        })
    except Exception as e:
        logger.error(f"获取设置失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取设置失败: {str(e)}"
        }, status_code=500)

@router.post("/settings-api")
@admin_required
async def update_settings(request: Request):
    """
    更新系统设置
    """
    # 确保系统已初始化
    if not settings.IS_INITIALIZED:
        logger.warning("尝试在系统未初始化时更新设置")
        return JSONResponse({
            "success": False, 
            "message": "系统尚未初始化"
        })
    
    try:
        # 获取提交的数据
        data = await request.json()
        logger.info(f"收到设置更新请求: {data}")
        
        # 连接数据库
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        
        # 更新设置
        current_time = datetime.datetime.now().timestamp()
        
        # 允许更新的字段
        allowed_fields = ["api_host", "admin_password", "fuck_password", "system_name"]
        updated = False
        
        for key in data:
            if key in allowed_fields and data[key]:
                # 密码字段验证长度
                if key.endswith("_password") and len(data[key]) < 6:
                    logger.warning(f"密码长度不足: {key}")
                    return JSONResponse({
                        "success": False, 
                        "message": f"{key}长度不能少于6个字符"
                    })
                
                logger.info(f"更新设置: {key}")
                cursor.execute(
                    "UPDATE system_settings SET setting_value = ?, updated_at = ? WHERE setting_key = ?",
                    (data[key], current_time, key)
                )
                updated = True
        
        conn.commit()
        conn.close()
        
        if not updated:
            logger.warning("没有有效设置字段被更新")
            return JSONResponse({
                "success": False, 
                "message": "没有提供有效的设置字段"
            })
        
        # 重新加载设置
        logger.info("重新加载设置")
        Settings()
        
        # 获取是否需要重启的标志
        needs_restart = data.get("needs_restart", True)  # 默认为True，大多数设置需要重启
        logger.info(f"是否需要重启: {needs_restart}")
        
        if needs_restart:
            # 创建标记文件，表示需要重启
            try:
                with open("data/needs_restart", "w") as f:
                    f.write(f"Settings updated at: {datetime.datetime.now().isoformat()}")
                logger.info("创建重启标记文件成功")
            except Exception as e:
                logger.warning(f"创建重启标记文件失败: {str(e)}")
                # 忽略标记文件创建失败的情况
            
            # 触发系统重启
            logger.info("触发系统重启")
            restart_result = await trigger_restart_after_setup()
            logger.info(f"重启结果: {restart_result}")
            
            # 返回重启消息
            if restart_result["success"]:
                return JSONResponse({
                    "success": True, 
                    "message": "设置已更新，系统正在重启...", 
                    "restart": True
                })
            else:
                return JSONResponse({
                    "success": True, 
                    "message": f"设置已更新，但重启失败: {restart_result['message']}", 
                    "restart": False
                })
        else:
            # 不需要重启，直接返回成功
            logger.info("设置更新成功，无需重启")
            return JSONResponse({
                "success": True, 
                "message": "设置已更新", 
                "restart": False
            })
    except Exception as e:
        logger.error(f"更新设置失败: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False, 
            "message": f"更新设置失败: {str(e)}"
        }, status_code=500)

@router.post("/sign/settings")
@admin_required
async def post_sign_settings(request: Request):
    """
    获取签到设置API (POST方法)
    """
    try:
        # 连接设置数据库
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        
        # 查询签到设置
        cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE 'sign_%'")
        
        settings = {}
        for row in cursor.fetchall():
            settings[row[0]] = row[1]
        
        conn.close()
        
        # 如果没有配置，使用默认值
        if not settings:
            settings = {
                "sign_morning_start_hour": "8",
                "sign_morning_start_minute": "0",
                "sign_morning_end_hour": "9",
                "sign_morning_end_minute": "0",
                "sign_afternoon_start_hour": "17",
                "sign_afternoon_start_minute": "0",
                "sign_afternoon_end_hour": "18",
                "sign_afternoon_end_minute": "0"
            }
        
        # 提取设置值
        sign_settings = {
            "morning_start_hour": settings.get("sign_morning_start_hour", "8"),
            "morning_start_minute": settings.get("sign_morning_start_minute", "0"),
            "morning_end_hour": settings.get("sign_morning_end_hour", "9"),
            "morning_end_minute": settings.get("sign_morning_end_minute", "0"),
            "afternoon_start_hour": settings.get("sign_afternoon_start_hour", "17"),
            "afternoon_start_minute": settings.get("sign_afternoon_start_minute", "0"),
            "afternoon_end_hour": settings.get("sign_afternoon_end_hour", "18"),
            "afternoon_end_minute": settings.get("sign_afternoon_end_minute", "0")
        }
        
        return JSONResponse({
            "success": True,
            "settings": sign_settings
        })
    except Exception as e:
        logger.error(f"获取签到设置失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取签到设置失败: {str(e)}"
        }, status_code=500)

@router.post("/update-code")
@admin_required
async def update_project_code(request: Request):
    """
    更新项目代码API
    从github拉取最新代码并部署
    """
    try:
        # 获取请求数据，如果解析失败则使用默认值
        force_update = False
        try:
            data = await request.json()
            force_update = data.get("force_update", False)
        except Exception:
            # JSON解析失败，使用默认值
            logger.warning("JSON解析失败，使用默认force_update=False")
        
        logger.info(f"收到更新项目代码请求，强制更新：{force_update}")
        
        # 创建repo目录（如果不存在）
        repo_dir = os.path.join(os.getcwd(), "repo")
        
        # 如果选择强制更新，则删除整个repo目录
        if force_update and os.path.exists(repo_dir):
            logger.info("强制更新模式：删除现有repo目录")
            # 使用subprocess而不是shutil以支持各种环境
            delete_cmd = f"rm -rf {repo_dir}"
            subprocess.run(
                delete_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
        
        # 重新创建repo目录（如果不存在）
        if not os.path.exists(repo_dir):
            os.makedirs(repo_dir)
            logger.info(f"创建repo目录: {repo_dir}")
        
        # 检查是否已经克隆了仓库
        git_dir = os.path.join(repo_dir, ".git")
        if not os.path.exists(git_dir):
            # 仓库尚未克隆，执行git clone
            logger.info("仓库尚未克隆，执行克隆操作")
            clone_cmd = "git clone https://github.com/chiupam/WorkClock.git repo"
            clone_result = subprocess.run(
                clone_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            if clone_result.returncode != 0:
                error_msg = clone_result.stderr.decode('utf-8')
                logger.error(f"克隆仓库失败: {error_msg}")
                return JSONResponse({
                    "success": False,
                    "message": f"克隆仓库失败: {error_msg}"
                }, status_code=500)
        else:
            # 仓库已存在，执行git pull
            logger.info("仓库已存在，执行拉取操作")
            # 添加--force选项强制覆盖本地修改
            pull_cmd = f"cd {repo_dir} && git fetch --all && git reset --hard origin/main && git pull"
            pull_result = subprocess.run(
                pull_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            stdout = pull_result.stdout.decode('utf-8')
            stderr = pull_result.stderr.decode('utf-8')
            
            if pull_result.returncode != 0:
                logger.error(f"拉取代码失败: {stderr}")
                return JSONResponse({
                    "success": False,
                    "message": f"拉取代码失败: {stderr}"
                }, status_code=500)
            
            # 检查是否已经是最新
            if "Already up to date" in stdout:
                logger.info("代码已经是最新版本")
                return JSONResponse({
                    "success": True,
                    "message": "代码已经是最新版本，无需更新",
                    "restart": False
                })
        
        # 复制文件到app目录
        src_dir = repo_dir
        dst_dir = os.getcwd()
        
        # 复制代码文件，但排除一些目录
        copy_cmd = f"rsync -av --exclude='.git' --exclude='repo' --exclude='data' --exclude='.idea' --exclude='.vscode' --exclude='.venv' {src_dir}/ {dst_dir}/"
        
        copy_result = subprocess.run(
            copy_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        if copy_result.returncode != 0:
            stderr = copy_result.stderr.decode('utf-8')
            logger.error(f"复制文件失败: {stderr}")
            return JSONResponse({
                "success": False,
                "message": f"复制文件失败: {stderr}"
            }, status_code=500)
        
        # 创建重启标记文件
        try:
            with open("data/needs_restart", "w") as f:
                f.write(f"Code updated at: {datetime.datetime.now().isoformat()}")
            logger.info("创建重启标记文件成功")
        except Exception as e:
            logger.warning(f"创建重启标记文件失败: {str(e)}")
            # 忽略标记文件创建失败的情况
        
        # 触发系统重启
        logger.info("触发系统重启")
        restart_result = await trigger_restart_after_setup()
        logger.info(f"重启结果: {restart_result}")
        
        # 返回结果
        if restart_result["success"]:
            return JSONResponse({
                "success": True,
                "message": "代码已更新，系统正在重启...",
                "restart": True
            })
        else:
            return JSONResponse({
                "success": True,
                "message": f"代码已更新，但重启失败: {restart_result.get('message', '未知错误')}",
                "restart": False
            })
    
    except Exception as e:
        logger.error(f"更新代码失败: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "message": f"更新代码失败: {str(e)}"
        }, status_code=500) 