import subprocess
import time  # 添加time模块

from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["系统"])

# 添加一个检查服务是否ready的帮助函数
async def check_service_ready(port=8000, max_retries=5, retry_interval=1):
    """
    检查服务是否准备就绪
    
    参数:
        port: 服务监听的端口
        max_retries: 最大重试次数
        retry_interval: 重试间隔（秒）
    
    返回:
        bool: 服务是否准备就绪
    """
    import socket
    
    for i in range(max_retries):
        try:
            # 尝试连接到服务端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"服务在端口 {port} 已就绪")
                return True
            else:
                print(f"重试 {i+1}/{max_retries}: 服务在端口 {port} 未就绪，等待 {retry_interval} 秒...")
                time.sleep(retry_interval)
        except Exception as e:
            print(f"检查服务就绪状态时发生错误: {str(e)}")
            time.sleep(retry_interval)
    
    print(f"服务在端口 {port} 未能在 {max_retries * retry_interval} 秒内就绪")
    return False

# 内部函数，用于重启应用
async def _restart_application():
    """使用PM2重启应用程序的内部函数"""
    try:
        # 打印调试信息
        subprocess.run(["pm2", "list"], shell=True, check=False)
        
        # 先尝试获取当前配置中的应用名
        config_check = subprocess.run(
            "cat ecosystem.config.js | grep name", 
            shell=True, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        
        app_name = "work"  # 默认应用名
        if config_check.returncode == 0:
            stdout = config_check.stdout.decode('utf-8').strip()
            if "name" in stdout and ":" in stdout:
                # 提取配置文件中的应用名
                try:
                    app_name_part = stdout.split(":")[1].strip()
                    # 移除引号和逗号
                    app_name = app_name_part.replace('"', '').replace("'", "").replace(',', '').strip()
                except Exception as e:
                    print(f"提取应用名失败: {str(e)}")
        
        # 首先检查应用是否已经运行
        status_check = subprocess.run(
            f"pm2 id {app_name} 2>/dev/null || echo 'not_found'", 
            shell=True, 
            stdout=subprocess.PIPE,
            check=False
        )
        
        stdout = status_check.stdout.decode('utf-8').strip()
        
        if "not_found" in stdout:
            print(f"应用 {app_name} 未运行，执行启动操作")
            # 应用未运行，执行启动
            result = subprocess.run(
                "pm2 start ecosystem.config.js", 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
        else:
            # 应用已运行，执行重载
            result = subprocess.run(
                f"pm2 reload {app_name} || pm2 restart {app_name}", 
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
        
        stdout = result.stdout.decode('utf-8') if result.stdout else ""
        stderr = result.stderr.decode('utf-8') if result.stderr else ""
        
        # 检查服务是否就绪
        is_ready = await check_service_ready(port=8000, max_retries=5, retry_interval=1)
        
        if result.returncode != 0:
            return {
                "success": True,
                "message": f"应用正在重启，但有警告: {stderr}",
                "is_ready": is_ready
            }
        
        return {
            "success": True, 
            "message": "应用正在重启，请等待片刻...",
            "is_ready": is_ready
        }
    except Exception as e:
        print(f"重启失败，错误: {str(e)}")
        return {
            "success": False, 
            "message": f"重启请求失败: {str(e)}",
            "is_ready": False
        }

# 用于从setup路由调用的函数
async def trigger_restart_after_setup():
    """系统设置后触发重启"""
    return await _restart_application()
