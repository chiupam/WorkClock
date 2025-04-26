"""
系统管理模块，提供系统信息获取和版本管理功能
"""
import logging
import os
import platform
import psutil
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 版本信息缓存及默认值
_version_cache = {
    "version": None,       # 初始为None，将从环境变量或GitHub中读取
    "timestamp": 0,        # 上次获取时间
    "cache_ttl": 3600      # 缓存有效期（秒）
}

# GitHub API信息缓存
_github_cache = {
    "data": None,
    "timestamp": 0,
    "cache_ttl": 3600
}

# 系统信息缓存
_system_info_cache = {
    "data": None,
    "timestamp": 0,
    "cache_ttl": 30        # 30秒缓存有效期
}

def _get_version_from_env():
    """
    从环境变量获取版本号
    :return: 版本号或None
    """
    try:
        env_version = os.environ.get('VERSION')
        if env_version:
            return env_version
    except Exception as e:
        logger.warning(f"从环境变量读取版本号失败: {str(e)}")
    return None

def _fetch_github_version():
    """
    从GitHub获取最新版本tag
    :return: 最新版本号
    """
    # 检查缓存是否有效
    now = time.time()
    if _version_cache["version"] is not None and now - _version_cache["timestamp"] < _version_cache["cache_ttl"]:
        return _version_cache["version"]
    
    # 首先从环境变量读取
    env_version = _get_version_from_env()
    if env_version:
        _version_cache["version"] = env_version
        _version_cache["timestamp"] = now
        return env_version
    
    # 无法从环境变量读取，使用缓存的GitHub数据
    if _github_cache["data"] is not None and now - _github_cache["timestamp"] < _github_cache["cache_ttl"]:
        latest_version = _github_cache["data"].get("tag_name")
        if latest_version:
            _version_cache["version"] = latest_version
            _version_cache["timestamp"] = now
            return latest_version
    
    # 尝试从GitHub获取
    try:
        response = requests.get(
            "https://api.github.com/repos/chiupam/WorkClock/releases/latest",
            timeout=3  # 降低超时，避免长时间阻塞
        )
        if response.status_code == 200:
            data = response.json()
            # 更新GitHub缓存
            _github_cache["data"] = data
            _github_cache["timestamp"] = now
            
            latest_version = data.get("tag_name")
            if latest_version:
                # 更新版本缓存
                _version_cache["version"] = latest_version
                _version_cache["timestamp"] = now
                logger.info(f"从GitHub获取到最新版本: {latest_version}")
                return latest_version
    except Exception as e:
        logger.warning(f"获取GitHub版本失败: {str(e)}")
    
    # 所有方法都失败，使用默认版本
    default_version = "v0.0.0"  # 作为最后的后备选项
    _version_cache["version"] = default_version
    _version_cache["timestamp"] = now
    return default_version

# 后台更新GitHub数据的线程
def _background_fetch_github_data():
    try:
        response = requests.get(
            "https://api.github.com/repos/chiupam/WorkClock/releases/latest",
            timeout=3
        )
        if response.status_code == 200:
            now = time.time()
            _github_cache["data"] = response.json()
            _github_cache["timestamp"] = now
            logger.info("后台更新GitHub数据成功")
    except Exception as e:
        logger.warning(f"后台更新GitHub数据失败: {str(e)}")

# 使用线程池执行耗时操作
_executor = ThreadPoolExecutor(max_workers=2)

# 动态获取当前版本
def get_version():
    """
    获取当前版本
    :return: 版本号
    """
    version = _fetch_github_version()
    
    # 如果版本是通过环境变量获取的，在后台更新GitHub数据
    if version == _get_version_from_env():
        now = time.time()
        if _github_cache["data"] is None or now - _github_cache["timestamp"] > _github_cache["cache_ttl"]:
            _executor.submit(_background_fetch_github_data)
    
    return version

# 提供VERSION常量以向后兼容
VERSION = get_version()

def get_system_info():
    """
    获取系统信息
    :return: 系统信息字典
    """
    # 检查缓存是否有效
    now = time.time()
    if _system_info_cache["data"] is not None and now - _system_info_cache["timestamp"] < _system_info_cache["cache_ttl"]:
        return _system_info_cache["data"]
    
    try:
        # 基本系统信息
        info = {
            "system": platform.system(),
            "version": platform.version(),
            "python_version": platform.python_version(),
            "app_version": get_version(),
            "uptime": get_uptime(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 资源使用信息
        try:
            info["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            info["memory_usage"] = psutil.virtual_memory().percent
            info["disk_usage"] = psutil.disk_usage("/").percent
        except (ImportError, AttributeError):
            # 如果psutil不可用，填入默认值
            info["cpu_usage"] = None
            info["memory_usage"] = None
            info["disk_usage"] = None
        
        # 更新缓存
        _system_info_cache["data"] = info
        _system_info_cache["timestamp"] = now
            
        return info
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        if _system_info_cache["data"] is not None:
            return _system_info_cache["data"]  # 返回过期缓存而不是错误
        return {"error": str(e)}

def get_uptime():
    """
    获取系统运行时间
    :return: 运行时间字符串
    """
    try:
        # 使用Linux兼容的方法获取系统运行时间
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_s = float(f.readline().split()[0])
        except:
            # 备选方法：使用psutil
            uptime_s = time.time() - psutil.boot_time()
                
        # 转换为可读格式
        days, remainder = divmod(uptime_s, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(days)}天 {int(hours)}小时 {int(minutes)}分钟"
    except Exception as e:
        logger.error(f"获取系统运行时间失败: {str(e)}")
        return "未知"

def check_update():
    """
    检查系统更新
    :return: 更新信息
    """
    current_version = get_version()
    
    # 使用缓存的GitHub数据
    now = time.time()
    if _github_cache["data"] is not None and now - _github_cache["timestamp"] < _github_cache["cache_ttl"]:
        data = _github_cache["data"]
        latest_version = data.get("tag_name", current_version)
        changelog = data.get("body", "")
    else:
        # 缓存无效，尝试获取新数据
        try:
            response = requests.get(
                "https://api.github.com/repos/chiupam/WorkClock/releases/latest",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                # 更新缓存
                _github_cache["data"] = data
                _github_cache["timestamp"] = now
                
                latest_version = data.get("tag_name", current_version)
                changelog = data.get("body", "")
            else:
                return {
                    "current_version": current_version,
                    "has_update": False,
                    "latest_version": current_version,
                    "changelog": "无法获取更新信息"
                }
        except Exception as e:
            logger.warning(f"检查更新失败: {str(e)}")
            return {
                "current_version": current_version,
                "has_update": False,
                "latest_version": current_version,
                "changelog": "无法获取更新信息"
            }
    
    # 正确比较版本号
    def parse_version(version):
        # 移除v前缀
        if version.startswith('v'):
            version = version[1:]
        # 分割成数字列表
        return [int(x) for x in version.split('.')]
    
    current_parts = parse_version(current_version)
    latest_parts = parse_version(latest_version)
    
    # 逐位比较版本号
    has_update = False
    for i in range(max(len(current_parts), len(latest_parts))):
        current_part = current_parts[i] if i < len(current_parts) else 0
        latest_part = latest_parts[i] if i < len(latest_parts) else 0
        if latest_part > current_part:
            has_update = True
            break
        elif latest_part < current_part:
            has_update = False
            break
    
    # 如果发现新版本，记录日志
    if has_update:
        logger.info(f"发现新版本: {latest_version}")
    
    return {
        "current_version": current_version,
        "has_update": has_update,
        "latest_version": latest_version,
        "changelog": changelog
    }
