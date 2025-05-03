"""
设置辅助函数
"""
import os
import sqlite3

from app import SET_DB_FILE


def get_setting_from_db(key, default_value=None):
    """从数据库获取设置"""
    try:
        # 确保data目录存在
        if not os.path.exists("data"):
            return default_value
            
        # 如果数据库文件不存在，返回默认值
        if not os.path.exists(SET_DB_FILE):
            return default_value
            
        # 连接数据库
        conn = sqlite3.connect(SET_DB_FILE)
        cursor = conn.cursor()
        
        # 查询设置
        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
        result = cursor.fetchone()
        
        # 关闭连接
        conn.close()
        
        # 返回结果
        if result and result[0]:
            return result[0]
        return default_value
    except Exception as e:
        print(f"从数据库获取设置失败 {key}: {str(e)}")
        return default_value

def validate_settings(settings):
    """
    验证应用程序设置是否有效
    
    :param settings: 配置对象
    :return: 验证结果，布尔值
    """
    # 检查是否已初始化
    if not settings.IS_INITIALIZED:
        print("警告: 系统尚未初始化，请访问 /setup 完成初始化设置")
        return False
    
    # 检查API主机设置
    if not settings.API_HOST:
        print("错误: API主机地址未设置")
        return False
    
    return True
