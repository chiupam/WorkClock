import httpx
from fastapi import Response
from app.utils.host import build_api_url
from app import logger


async def wx_login(headers: dict, data: dict):
    """
    微信登录
    """
    
    api_url = build_api_url("/Apps/wxLogin")

    try:
        async with httpx.AsyncClient() as client:
            api_response = await client.post(api_url, headers=headers, json=data)
            api_data = api_response.json()
            if api_data.get("success", False):
                return api_response.headers.get("Set-Cookie", {})
            else:
                logger.error(f"API请求成功但返回失败状态: {api_data.get('message', '未知错误')}")
                return None
    except Exception as e:
        logger.error(f"获取用户信息时发生异常: {str(e)}")
        return None


async def get_user_info(headers: dict):
    """
    获取用户信息
    """
    
    api_url = build_api_url("/Apps/AppIndex")
    params = {'UnitCode': '530114'}
    
    try:
        async with httpx.AsyncClient() as client:
            api_response = await client.get(api_url, headers=headers, params=params)
            api_data = api_response.json()
            if api_data.get("success", False):
                api_data = api_data.get("data", {})
                fields = ["UserID", "UserName", "DepID", "Position", "DepName"]
                user_info = {}
                for field in fields:
                    user_info[field] = api_data.get(field, "")
                return user_info
            else:
                logger.error(f"API请求成功但返回失败状态: {api_data.get('message', '未知错误')}")
                return None
    except Exception as e:
        logger.error(f"获取用户信息时发生异常: {str(e)}")
        return None
    

async def get_attendance_info(headers: dict, user_id: int) -> Response | None:
    """
    获取指定用户的考勤打卡信息。

    该函数通过异步 HTTP 请求调用考勤系统接口，获取用户的上下班打卡记录。

    参数:
        headers (dict): 请求所需的 HTTP 请求头，通常包含身份认证信息。
        user_id (int): 用户的唯一标识符，用于查询其考勤数据。

    返回:
        httpx.Response | None: 若请求成功返回响应对象，否则返回 None。
    """

    api_url = build_api_url('/AttendanceCard/GetAttCheckinoutList')
    data = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, headers=headers, json=data)
            if response.status_code == 200:
                return response
            else:
                logger.error(f"API请求成功但返回失败状态")
                return None
    except Exception as e:
        logger.error(f"获取用户获取考勤信息时发生异常: {str(e)}")
        return None

