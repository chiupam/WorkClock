import asyncio
import calendar
import datetime
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, Request, Cookie, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.dependencies import is_valid_open_id
from app.auth.utils import get_mobile_user_agent
from app.utils.host import build_api_url

router = APIRouter(tags=["考勤统计"])

class StatisticData(BaseModel):
    month: int
    year: Optional[int] = None

@router.post("/monthly")
async def get_monthly_statistics(
    request: Request,
    data: StatisticData, 
    open_id: Optional[str] = Cookie(None)
):
    """
    获取用户月度考勤统计数据
    
    返回用户指定月份的考勤统计数据，包括请假、迟到、早退、缺卡次数和日历数据
    """
    # 验证用户身份
    if not open_id:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    
    is_valid, user_info = is_valid_open_id(open_id)
    if not is_valid:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    # 获取用户ID
    user_id = user_info.get("user_id", None)
    if not user_id:
        raise HTTPException(status_code=400, detail="无法获取用户ID")
    
    # 固定请求头
    headers = {"User-Agent": get_mobile_user_agent(request.headers.get("User-Agent", ""))}

    # 获取年月参数(整数类型，用于计算)
    month_int = data.month
    year_int = data.year or datetime.datetime.now().year
    
    # 获取日历天数
    _, days_in_month = calendar.monthrange(year_int, month_int)
    
    # 转换为字符串格式(用于API请求)
    month_str = str(month_int).zfill(2)
    year_str = str(year_int)
    
    # 获取统计数据
    stats = await get_Attendance_Statistics(headers, user_id, year_str, month_str)
    daily_records = await GetYueTjList(headers, user_id, year_str, month_str)
    
    # 构建返回的数据结构 - 返回原始数据，让前端处理
    result = {
        "success": True,
        "statistics": stats,
        "details": daily_records,
        "year": year_int,
        "month": month_int,
        "days": days_in_month
    }
    
    return JSONResponse(
        status_code=200,
        content=result
    )

def generate_calendar_data(daily_records: List[Dict], year: int, month: int) -> List[Dict]:
    """
    根据每日考勤记录生成日历数据
    
    参数:
        daily_records: 每日考勤记录列表
        year: 年份
        month: 月份
        
    返回:
        日历数据列表
    """
    calendar_data = []
    
    # 获取当前日期
    now = datetime.datetime.now()
    current_day = now.day if now.year == year and now.month == month else 0
    
    # 获取月份的天数
    _, days_in_month = calendar.monthrange(year, month)
    
    # 如果daily_records为空或者长度不足,则可能是概览模式
    is_overview_mode = not daily_records or len(daily_records) < days_in_month/2
    
    # 处理每一天的数据
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        
        # 创建日期对象
        date_obj = datetime.date(year, month, day)
        weekday = date_obj.weekday()
        
        # 如果是概览模式，只提供日期和星期几，不提供状态
        if is_overview_mode:
            calendar_data.append({
                "day": day,
                "weekday": weekday,
                "status": {"type": "none", "label": ""}
            })
            continue
        
        # 尚未到来的日期（包括未来的日期）
        if day > current_day:
            status = {"type": "future", "label": ""}
            calendar_data.append({
                "day": day,
                "weekday": weekday,
                "status": status
            })
            continue
        
        # 查找当天的记录
        day_record = next((record for record in daily_records if record.get('rq') == date_str), None)
        
        if not day_record:
            # 如果找不到记录，创建一个默认记录
            # 周末
            if weekday >= 5:  # 5和6是周六和周日
                status = {"type": "rest", "label": "休息"}
            else:
                status = {"type": "check", "label": "✓"}
        else:
            # 节假日
            if day_record.get('isholiday') == 1:
                holiday_name = day_record.get('jjr', '')
                # 处理节假日名称，如果超过3个字符，只取前两个
                if holiday_name and len(holiday_name) >= 3:
                    holiday_name = holiday_name[:2]
                status = {"type": "holiday", "label": holiday_name if holiday_name else "休息"}
            # 请假
            elif day_record.get('IsQj') == 1:
                status = {"type": "leave", "label": "请假"}
            # 根据打卡记录判断状态
            else:
                morning_clock = day_record.get('SWSBDKCS', 0)
                afternoon_clock = day_record.get('XWXBDKCS', 0)
                
                # 周末或节假日休息
                if weekday >= 5 or day_record.get('isholiday') == 1:
                    status = {"type": "rest", "label": "休息"}
                # 缺卡
                elif morning_clock == 0 or afternoon_clock == 0:
                    status = {"type": "absent", "label": "缺卡"}
                # 正常出勤 - 使用对勾标记
                else:
                    status = {"type": "check", "label": "✓"}
        
        calendar_data.append({
            "day": day,
            "weekday": weekday,
            "status": status
        })
    
    return calendar_data


async def get_Attendance_Statistics(headers: dict, user_id: int, year: str, month: str) -> Dict[str, Any]:
    """
    获取指定用户某月的出勤统计信息。

    向后端 API 发送请求，获取用户在指定年份和月份的出勤统计数据，
    包括请假天数、迟到次数、早退次数和缺卡次数。

    参数:
        headers (dict): 请求头（包含认证信息等）。
        user_id (int): 用户 ID。
        year (str): 年份（如 "2024"）。
        month (str): 月份（如 "04"）。

    返回:
        Dict[str, Any]: 一个包含出勤统计项的字典：
            {
                "LeaveDays": ...,
                "LateNumber": ...,
                "ZtNumber": ...,
                "LackCarNumber": ...
            }
    """
    
    api_url = build_api_url("/AttendanceCard/get_Attendance_Statistics")
    data = {"UnitCode": "530114", "UserID": user_id, "SetClass": "1", "Mid": "134", "QueryType": "2"}
    data = {**data, "Syear": f"{year}年", "Smonth": f"{month}月"}

    # 重试次数
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:  # 设置30秒超时
                response = await client.post(api_url, headers=headers, json=data)
                stat_dict = response.json()[0]["Attend_Stat_List"][0]
                # 请假、迟到、早退、缺卡
                stat_list = ["LeaveDays", "LateNumber", "ZtNumber", "LackCarNumber"]  
                stat_data = {key: stat_dict[key] for key in stat_list}
                return stat_data
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
            # 连接错误
            retry_count += 1
            if retry_count < max_retries:
                # 等待一段时间再重试，每次重试增加等待时间
                await asyncio.sleep(1 * retry_count)  # 第一次等待1秒，第二次2秒，依此类推
                continue
            break
        except Exception as e:
            # 其他错误
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(1 * retry_count)
                continue
            break

    # 返回默认数据
    return {"LeaveDays": 0, "LateNumber": 0, "ZtNumber": 0, "LackCarNumber": 0}
    

async def GetYueTjList(headers: dict, user_id: int, year: str, month: str) -> List[Dict[str, Any]]:
    """
    获取指定用户某月的日常考勤明细列表。

    调用后端 API，返回指定用户在某年某月的每日考勤数据，
    包括是否节假日、是否请假、加班标记、打卡/补卡记录等。

    参数:
        headers (dict): 请求头（包含认证信息等）。
        user_id (int): 用户 ID。
        year (str): 年份（如 "2024"）。
        month (str): 月份（如 "04"）。

    返回:
        List[Dict[str, Any]]: 每日考勤明细的列表，每项包含：
            - rq: 日期
            - isholiday: 是否节假日
            - jjr: 节假日标记
            - IsQj: 是否请假
            - SWSBDKCS: 上午上班打卡次数
            - XWXBDKCS: 下午下班打卡次数
            - IsSwSbbuka: 上午补卡标记
            - IsXwXbbuka: 下午补卡标记
    """

    api_url = build_api_url("/AttendanceCard/GetYueTjList")
    params = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}
    params = {**params, "year": f"{year}年", "month": f"{month}月"}

    # 重试次数
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:  # 设置30秒超时
                response = await client.post(api_url, headers=headers, params=params)
                data = response.json()
                # 日期、是否节假日、节假日、请假、上班打卡、下班打卡、上班补卡、下班补卡
                stat_fields = {'rq', 'isholiday', 'jjr', 'IsQj', 'SWSBDKCS', 'XWXBDKCS', 'IsSwSbbuka', 'IsXwXbbuka'}
                stat_list = [{key: item[key] for key in stat_fields if key in item} for item in data]
                return stat_list
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
            # 连接错误
            retry_count += 1
            if retry_count < max_retries:
                # 等待一段时间再重试，每次重试增加等待时间
                await asyncio.sleep(1 * retry_count)  # 第一次等待1秒，第二次2秒，依此类推
                continue
            break
        except Exception as e:
            # 其他错误
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(1 * retry_count)
                continue
            break

    # 返回空列表
    return []
