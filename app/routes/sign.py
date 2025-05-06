import datetime
import httpx
from typing import Optional

from fastapi import APIRouter, Request, Cookie, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.dependencies import is_valid_open_id
from app.auth.utils import get_mobile_user_agent
from config import settings
from app.utils.host import build_api_url
from app.utils.log import log_sign_activity, log_operation, LogType

router = APIRouter(tags=["打卡"])

class SignData(BaseModel):
    attendance: int = 0

@router.post("/sign")
async def sign_in(request: Request, data: SignData, open_id: Optional[str] = Cookie(None)):
    """
    用户打卡接口
    
    处理用户的打卡请求，根据当前时间确定是上班打卡还是下班打卡
    """

    # 验证用户身份
    if not open_id:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    
    is_valid, user_info = is_valid_open_id(open_id)
    if not is_valid:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    # 获取用户ID
    user_id = user_info.get("user_id", None)
    username = user_info.get("username", "未知用户")
    if not user_id:
        raise HTTPException(status_code=400, detail="无法获取用户ID")
    
    # 根据attendance状态决定打卡类型
    attendance = data.attendance
    is_valid, clock_type, message = check_sign_time(attendance)
    sign_type = "上班打卡" if clock_type == 1 else "下班打卡"
    
    if not is_valid:
        # 记录失败的打卡请求
        await log_sign_activity(
            username, 
            sign_type,
            False, 
            message,
            request.client.host
        )
        
        # 记录操作日志 - 打卡失败
        await log_operation(
            username,
            LogType.SIGN,
            f"{sign_type}失败: {message}",
            request.client.host,
            False
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "message": message,
                "clockType": sign_type
            }
        )

    result = await SaveAttCheckinout(request, open_id)
    
    # 记录打卡结果到日志数据库
    success = result.get("success", False)
    result_message = result.get("message", "未知结果")
    
    await log_sign_activity(
        username, 
        sign_type,
        success, 
        result_message,
        request.client.host
    )
    
    # 记录操作日志 - 打卡结果
    await log_operation(
        username,
        LogType.SIGN,
        f"{sign_type}结果: {result_message}",
        request.client.host,
        success
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "success": success,
            "message": result_message,
            "clockType": sign_type
        }
    )

def check_sign_time(attendance: int):
    """
    判断当前时间段是否可以打卡
    早上7:00-9:00可以打卡，下午17:00-23:59可以打卡
    """

    current_time = datetime.datetime.now().time()
    morning_start = datetime.time(7, 0)
    morning_end = datetime.time(9, 0)
    afternoon_start = datetime.time(17, 0)
    afternoon_end = datetime.time(23, 59)
    
    # 判断是否在早上打卡时间段
    if morning_start <= current_time <= morning_end:
        if attendance == 0:
            return True, 1, "上班打卡"
        else:
            return False, 0, "上班已经打卡"
    # 判断是否在下午打卡时间段
    elif afternoon_start <= current_time <= afternoon_end:
        if attendance == 0 or attendance == 1:
            return True, 2, "下班打卡，请补签上班卡"
        else:
            return False, 0, "下班已经打卡"
    else:
        return False, 0, "不在打卡时间段"
    

async def SaveAttCheckinout(request: Request, open_id: str):
    """
    保存打卡记录
    """

    _, user_info = is_valid_open_id(open_id)

    user_id = user_info.get("user_id", None)
    dep_id = user_info.get("department_id", None)

    if not user_id or not dep_id:
        raise HTTPException(status_code=400, detail="无法获取用户ID")

    api_url = build_api_url("/AttendanceCard/SaveAttCheckinout")
    headers = {"User-Agent": get_mobile_user_agent(request.headers.get("User-Agent", ""))}
    data = {"model": {"Aid": 0, "UnitCode": settings.UNIT_CODE, "userID": user_id, "userDepID": dep_id, "Mid": 134, "Num_RunID": 14, "lng": "", "lat": "", "realaddress": settings.REAL_ADDRESS, "iSDelete": 0, "administratorChangesRemark": settings.REAL_ADDRESS}, "AttType": 1}
    
    # 实际环境中解除注释，返回真实API响应
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=data, headers=headers)
        return response.json()
