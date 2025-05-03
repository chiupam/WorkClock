import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import logger
from app.auth.dependencies import is_valid_open_id
from app.routes.statistics import GetYueTjList
from app.utils.host import build_api_url
from config import settings

# 创建路由器
router = APIRouter()

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")

@router.get("/")
async def root(request: Request, open_id: Optional[str] = Cookie(None)):
    """
    首页路由 - 检查系统是否需要初始化，并根据用户状态显示适当内容
    """
    
    # 检查系统是否已完成设置配置
    if not settings.IS_INITIALIZED:
        return RedirectResponse(url="/setup")
    
    # 如果没有cookie，直接返回登录页面
    if not open_id:
        return templates.TemplateResponse("login.html", {"request": request})
    
    # 验证用户身份
    is_valid, user_info = is_valid_open_id(open_id)
    
    if not is_valid:
        return templates.TemplateResponse("login.html", {"request": request})
    
    # 检查是否是管理员用户
    if user_info.get("user_id") == "admin":
        # 管理员特殊处理
        return RedirectResponse(url="/admin/dashboard")
    
    # 普通用户，获取考勤信息
    try:
        now = datetime.datetime.now()
        headers = {'User-Agent': request.headers.get('User-Agent')}    
        yue_tj_list = await GetYueTjList(headers, user_info.get("user_id"), str(now.year), str(now.month).zfill(2))
        is_workday = yue_tj_list[now.day - 1].get("isholiday") == 0
        if not is_workday:
            # 非工作日，不需要打卡，就不需要进行请求打卡数据了
            attendance_data = []
            show_sign_btn = {"show": False, "message": "今天是休息日，无需打卡"}
        else:
            # 工作日，需要打卡，需要进行请求打卡数据，显示签到按钮
            attendance_data = await get_attendance_info(request.headers.get('User-Agent'), user_info.get("user_id"))
            print(attendance_data)
            show_sign_btn = show_sign_button(attendance_data)

        # 登录成功，返回index.html
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "user_info": user_info,
                "attendance_data": attendance_data,
                "is_workday": is_workday,
                "show_sign_button": show_sign_btn,
                "current_month": datetime.datetime.now().month,
                "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    except Exception as e:
        # 处理异常，确保页面正常显示
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "user_info": user_info,
                "error_message": f"获取考勤数据失败: {str(e)}",
                "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "show_sign_button": {"show": False, "message": "获取数据失败"}
            }
        )
    

async def get_attendance_info(ua: str, user_id: int):
    """获取考勤信息"""

    def _format_record(_record):
        if not _record:
            return None

        _timestamp = int(_record['clockTime'].replace('/Date(', '').replace(')/', ''))
        clock_time = datetime.datetime.fromtimestamp(_timestamp / 1000)

        return {
            "type": "上班" if _record['clockType'] == 1 else "下班",
            "standardTime": "09:00" if _record['clockType'] == 1 else "17:00",
            "clockTime": clock_time.strftime("%H:%M:%S"),
            "location": _record['administratorChangesRemark'] or "未知地点"
        }
    
    try:
        # 构建API URL
        api_url = build_api_url('/AttendanceCard/GetAttCheckinoutList')
        headers = {'User-Agent': ua}
        params = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}

        # 使用httpx发送GET请求
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, headers=headers, json=params)
            
        # 检查响应状态
        if response.status_code == 200:
            now = datetime.datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # 过滤出天的记录
            today_records = []
            for record in response.json():
                timestamp = int(record['clockTime'].replace('/Date(', '').replace(')/', ''))
                record_date = datetime.datetime.fromtimestamp(timestamp / 1000)  # 转换
                if record_date.date() == today.date():
                    today_records.append(record)
            # 分离上班下班记录
            clock_in = next((record for record in today_records if record['clockType'] == 1), None)
            clock_out = next((record for record in today_records if record['clockType'] == 2), None)

            # 检查是否要显示补卡提醒
            current_time = now.hour * 60 + now.minute
            work_end_time = 17 * 60  # 17:00
            need_reminder = current_time >= work_end_time and not clock_in

            return {
                "needReminder": need_reminder,
                "clockInRecord": _format_record(clock_in),
                "clockOutRecord": _format_record(clock_out)
            }
            
    except Exception as e:
        # 处理异常，返回空字典
        logger.error(f"获取考勤信息异常: {str(e)}")
        return {}
    


async def check_is_workday(ua: str, user_id: int):
    """检查今天是否是工作日"""
    try:
        # 构建API URL
        now = datetime.datetime.now()

        api_url = build_api_url('/AttendanceCard/GetYueTjList')
        headers = {'User-Agent': ua}
        params = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}
        params = {**params, "year": f"{now.year}年", "month": f"{str(now.month).zfill(2)}月"}

        # 使用httpx发送GET请求
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url, headers={"User-Agent": ua})
            
            # 检查响应状态
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == 200:
                    work_day = data["data"]["workday"]
                    return work_day == 1
                else:
                    # 如果接口返回非200，默认为工作日
                    return True
            else:
                # 如果请求失败，默认为工作日
                return True
    except Exception as e:
        # 处理异常，默认为工作日
        logger.error(f"检查工作日异常: {str(e)}")
        return True
    

def show_sign_button(attendance_data: dict):
    """
    根据考勤数据决定是否显示打卡按钮
    返回格式: {"show": True/False, "message": "提示信息"}
    """
    result = {"show": False, "message": ""}  # 默认不显示按钮
    
    # 获取当前时间
    now = datetime.datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    current_time = current_hour * 60 + current_minute  # 转换为分钟
    
    # 上午打卡时间范围：06:00:00-09:00:59
    morning_start_time = 6 * 60  # 06:00
    morning_end_time = 9 * 60 + 59  # 09:59
    
    # 下午打卡时间范围：17:00:00-23:59:59
    afternoon_start_time = 17 * 60  # 17:00
    afternoon_end_time = 23 * 60 + 59  # 23:59
    
    # 检查打卡记录
    clock_in_record = attendance_data.get("clockInRecord")
    clock_out_record = attendance_data.get("clockOutRecord")
    
    # 判断是否在上午打卡时间段
    if morning_start_time <= current_time <= morning_end_time:
        if not clock_in_record:
            result["show"] = True
            result["message"] = "上班打卡"
        else:
            result["show"] = False
            result["message"] = "您已完成上班打卡"
    
    # 判断是否在下午打卡时间段
    elif afternoon_start_time <= current_time <= afternoon_end_time:
        if not clock_out_record:
            # 检查是否有上班打卡记录，如果没有上班打卡记录，提示需要先补签上班
            if not clock_in_record:
                result["show"] = True
                result["message"] = "请您先补签上班打卡"
            else:
                result["show"] = True
                result["message"] = "下班打卡"
        else:
            result["show"] = False
            result["message"] = "您已完成下班打卡"
    
    # 不在打卡时间段
    else:
        result["show"] = False
        result["message"] = f"当前时间 {now.strftime('%H:%M')} 不在打卡时间范围内"
    
    # 特殊情况处理：如果系统提示需要补签
    if attendance_data.get("needReminder", False):
        if not clock_in_record:
            result["show"] = True
            result["message"] = "请您补签上班打卡"
    
    return result