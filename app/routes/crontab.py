import ast
import asyncio
import datetime
import httpx
import sqlite3
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, Request, Cookie
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List

from app import logger, CRON_DB_FILE, USER_DB_FILE
from app.auth.dependencies import is_valid_open_id
from app.auth.utils import get_mobile_user_agent
from app.routes.index import get_attendance_info, show_sign_button
from app.routes.statistics import GetYueTjList
from app.utils.host import build_api_url
from app.utils.log import log_sign_activity, log_operation, LogType
from config import settings

# 创建路由器
router = APIRouter(tags=["定时"])

# 设置模板
templates = Jinja2Templates(directory="app/static/templates")

# 定义数据模型
class ScheduleRequest(BaseModel):
    morning: bool
    afternoon: bool
    morning_times: Optional[List[int]] = None  # 改为布尔值列表[1,0,1]表示三个时间点的选择状态
    afternoon_times: Optional[List[int]] = None  # 改为布尔值列表[1,0,1]表示三个时间点的选择状态

class ScheduleResponse(BaseModel):
    success: bool
    message: str
    morning_times: Optional[List[str]] = None
    afternoon_times: Optional[List[str]] = None
    schedule_id: Optional[int] = None
    user_limit_reached: bool = False

# 配置APScheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{CRON_DB_FILE}')
}

scheduler = BackgroundScheduler(jobstores=jobstores)

# 定义打卡时间
MORNING_TIMES = settings.MORNING_TIMES
AFTERNOON_TIMES = settings.AFTERNOON_TIMES

# 连接数据库
def get_db_connection():
    conn = sqlite3.connect(CRON_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_info(user_id: str):
    try:
        conn = sqlite3.connect(USER_DB_FILE)
        conn.row_factory = sqlite3.Row  # 这样可以通过列名访问结果
        cursor = conn.cursor()
        
        # 执行查询
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        # 将结果转换为字典
        result = dict(user) if user else None
        
        # 关闭连接
        conn.close()
        return result
        
    except Exception as e:
        print(f"获取用户信息失败: {str(e)}")
        return None


# 自动打卡函数
async def auto_sign(user_id: str):
    try:
        user_info = get_user_info(user_id)
        if not user_info:
            # 记录自动打卡错误日志
            await log_operation(
                "系统自动",
                LogType.CRON,
                f"自动打卡错误: 无法获取用户信息 {user_id}",
                "Auto Task",
                False
            )
            return logger.error(f"无法获取用户信息: {user_id}")
            
        username = user_info.get("username", "未知用户")
        user_id = user_info.get("user_id", user_id)
        dep_id = user_info.get("department_id", None)
        
        if not dep_id:
            # 记录自动打卡错误日志
            await log_operation(
                username,
                LogType.CRON,
                f"自动打卡错误: 用户没有部门ID",
                "Auto Task",
                False
            )
            return logger.error(f"用户 {user_id} 没有部门ID")
            
        # 确定打卡类型（根据时间判断是上班还是下班打卡）
        now = datetime.datetime.now()
        current_hour = now.hour
        sign_type = "上班打卡" if current_hour < 12 else "下班打卡"
        
        now = datetime.datetime.now()
        headers = {"User-Agent": get_mobile_user_agent()}
        yue_tj_list = await GetYueTjList(headers, user_id, str(now.year), str(now.month).zfill(2))
        is_workday = yue_tj_list[now.day - 1].get("isholiday") == 0
        if not is_workday:
            return logger.info("今天是休息日，无需打卡")
        
        attendance_data = await get_attendance_info(headers.get("User-Agent"), user_id)
        show_sign_btn = show_sign_button(attendance_data)
        if not show_sign_btn["show"]:
            return logger.warning(show_sign_btn["message"])
        
        url = build_api_url("/AttendanceCard/SaveAttCheckinout")
        data = {
            "model": {
                "Aid": 0,
                "UnitCode": "530114",
                "userID": user_id,
                "userDepID": dep_id,
                "Mid": 134,
                "Num_RunID": 14,
                "lng": "",
                "lat": "",
                "realaddress": "呈贡区人民检察院",
                "iSDelete": 0,
                "administratorChangesRemark": "呈贡区人民检察院"
            },
            "AttType": 1
        }
        # 实际环境中解除注释，返回真实API响应
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            result = response.json()
            
        # 记录打卡日志
        await log_sign_activity(
            username,
            sign_type,
            result.get('success', False),
            f"自动打卡: {result.get('message', '未知错误')}",
            "Auto Task"
        )
        
        # 记录操作日志
        await log_operation(
            username,
            LogType.CRON,
            f"自动{sign_type}结果: {result.get('message', '未知错误')}",
            "Auto Task",
            result.get('success', False)
        )
                
    except Exception as e:
        error_msg = f"自动打卡出错: {str(e)}"
        logger.error(error_msg)
        
        # 记录错误日志
        if user_info:
            await log_sign_activity(
                user_info.get("username", "未知用户"),
                "自动打卡",
                False,
                error_msg,
                "Auto Task"
            )
            
            # 记录操作日志
            await log_operation(
                user_info.get("username", "未知用户"),
                LogType.CRON,
                f"自动打卡错误: {error_msg}",
                "Auto Task",
                False
            )
        else:
            # 如果连用户信息都没获取到，使用系统名义记录
            await log_operation(
                "系统自动",
                LogType.CRON,
                f"自动打卡严重错误: {error_msg}",
                "Auto Task",
                False
            )

# 同步包装函数，用于运行异步函数
def sync_auto_sign(user_id: str):
    """
    同步函数，用于包装异步的auto_sign函数以便APScheduler调用
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 获取用户信息
    user_info = get_user_info(user_id)
    username = user_info.get("username", "未知用户") if user_info else f"用户({user_id})"
    
    try:        
        loop.run_until_complete(auto_sign(user_id))
    except Exception as e:
        logger.error(f"运行自动打卡函数失败: {str(e)}")
    finally:
        loop.close()

# 检查用户是否已有定时任务
def get_user_schedule(user_id: str):
    conn = get_db_connection()
    
    # 确保获取完整的字段列表
    query = '''
    SELECT id, user_id, username, morning, afternoon, schedule_index, 
           morning_time, afternoon_time, morning_selecte, afternoon_selecte
    FROM schedules WHERE user_id = ?
    '''
    
    # 执行查询
    try:
        schedule = conn.execute(query, (user_id,)).fetchone()
            
    except Exception as e:
        logger.error(f"查询用户定时设置时发生错误: {str(e)}")
        schedule = None
        
    conn.close()
    return schedule

# 获取可用的定时索引
def get_available_index():
    conn = get_db_connection()
    # 只考虑实际开启了定时的用户所占用的索引
    used_indices = [row[0] for row in conn.execute('SELECT schedule_index FROM schedules WHERE morning = 1 OR afternoon = 1').fetchall()]
    conn.close()
    
    for i in range(3):
        if i not in used_indices:
            return i
    
    logger.warning("无可用的定时索引，已达用户上限")
    return None

# 添加定时任务
def add_schedule_jobs(user_id: str, index: int, morning: bool, afternoon: bool):    
    # 添加上午打卡任务
    if morning:
        for time_str in MORNING_TIMES[index]:
            hour, minute = map(int, time_str.split(':'))
            job_id = f"{user_id}_morning_{time_str}"
            
            scheduler.add_job(
                sync_auto_sign,
                'cron',
                hour=hour,
                minute=minute,
                id=job_id,
                replace_existing=True,
                args=[user_id]
            )
    
    # 添加下午打卡任务
    if afternoon:
        for time_str in AFTERNOON_TIMES[index]:
            hour, minute = map(int, time_str.split(':'))
            job_id = f"{user_id}_afternoon_{time_str}"
            
            scheduler.add_job(
                sync_auto_sign,
                'cron',
                hour=hour,
                minute=minute,
                id=job_id,
                replace_existing=True,
                args=[user_id]
            )

# 删除用户的所有定时任务
def remove_schedule_jobs(user_id: str):
    job_ids = scheduler.get_jobs()
    removed_count = 0
    
    for job in job_ids:
        if job.id.startswith(f"{user_id}_"):
            scheduler.remove_job(job.id)
            removed_count += 1


# 启动定时器并从数据库恢复任务
def start_scheduler():
    try:
        # 恢复已有的定时任务
        conn = get_db_connection()
        schedules = conn.execute('SELECT * FROM schedules').fetchall()
        conn.close()
        
        for schedule in schedules:
            add_schedule_jobs(
                schedule['user_id'],
                schedule['schedule_index'],
                schedule['morning'] == 1,
                schedule['afternoon'] == 1
            )
        
        # 启动调度器
        if not scheduler.running:
            scheduler.start()
        return True
    except Exception as e:
        error_msg = f"启动调度器时发生错误: {str(e)}"
        logger.error(error_msg)
        return False

# 获取用户的定时设置
@router.get("/tasks")
async def get_schedule(request: Request, open_id: Optional[str] = Cookie(None)):
    
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

    schedule = get_user_schedule(user_info.get("user_id"))
    
    # 分配可用的索引（现有的或新的）
    index = schedule['schedule_index'] if schedule else get_available_index() or 0
    
    # 获取该索引对应的默认时间选项（这只是用于前端显示可选项）
    morning_times = MORNING_TIMES[index]
    afternoon_times = AFTERNOON_TIMES[index]
    
    if schedule:
        morning_selections = ast.literal_eval(schedule['morning_selecte'])
        afternoon_selections = ast.literal_eval(schedule['afternoon_selecte'])
        return JSONResponse({
            "success": True,
            "message": "获取定时设置成功",
            "morning_times": morning_times,
            "morning_selections": morning_selections,
            "afternoon_times": afternoon_times,
            "afternoon_selections": afternoon_selections
        })
    else:
        # 用户未设置，返回该索引对应的默认时间选项
        return JSONResponse({
            "success": True,
            "message": "未设置定时",
            "morning_times": morning_times,
            "morning_selections": [1, 1, 0],
            "afternoon_times": afternoon_times,
            "afternoon_selections": [1, 0, 0]
        })

# 保存用户的定时设置
@router.post("/tasks")
async def save_schedule(request: Request, schedule_req: ScheduleRequest, open_id: Optional[str] = Cookie(None)):
    
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
    
    # 获取用户参数
    user_id = user_info.get("user_id")
    username = user_info.get("username")

    conn = sqlite3.connect(CRON_DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedules WHERE user_id = ?", (user_id,))
    schedule = cursor.fetchone()
    
    # 获取用户选择状态和开启状态
    morning_selections = schedule_req.morning_times or [0, 0, 0]  # 默认全部不选
    afternoon_selections = schedule_req.afternoon_times or [0, 0, 0]  # 默认全部不选
    morning_status = 1 if schedule_req.morning else 0
    afternoon_status = 1 if schedule_req.afternoon else 0
    
    # 确定索引（现有用户保持原索引，新用户分配新索引）
    if schedule:
        # 获取现有索引
        cursor.execute("SELECT schedule_index FROM schedules WHERE user_id = ?", (user_id,))
        index = cursor.fetchone()[0]
    else:
        # 新用户，分配可用索引
        index = get_available_index()
        if index == None:
            # 记录失败日志
            await log_operation(
                username,
                LogType.CRON, 
                "更新定时任务失败: 已达到用户上限(3人)",
                request.client.host,
                False
            )
            
            return JSONResponse({
                "success": False,
                "message": "已达到定时任务用户数量限制(最多3个用户)",
                "user_limit_reached": True
            }, status_code=400)
    
    # 根据选择状态选择对应的时间
    morning_time = []
    afternoon_time = []

    for i, selected in enumerate(morning_selections):
        if selected == 1:
            morning_time.append(MORNING_TIMES[index][i])

    for i, selected in enumerate(afternoon_selections):
        if selected == 1:
            afternoon_time.append(AFTERNOON_TIMES[index][i])
    
    # 如果用户开启了某个时段但没有选择时间，视为取消该时段的定时
    if morning_status == 1 and not morning_time:
        morning_status = 0
    
    if afternoon_status == 1 and not afternoon_time:
        afternoon_status = 0
    
    # 准备日志详情
    log_details = (
        f"早上: {'、'.join(morning_time) if morning_status == 1 and morning_time else '无'}，"
        f"下午: {'、'.join(afternoon_time) if afternoon_status == 1 and afternoon_time else '无'}"
    )
    
    try:
        if schedule:
            cursor.execute(
                "UPDATE schedules SET morning = ?, afternoon = ?, morning_time = ?, afternoon_time = ?, morning_selecte = ?, afternoon_selecte = ? WHERE user_id = ?",
                (morning_status, afternoon_status, str(morning_time), str(afternoon_time), str(morning_selections), str(afternoon_selections), user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO schedules (user_id, username, morning, afternoon, schedule_index, morning_time, afternoon_time, morning_selecte, afternoon_selecte) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, username, morning_status, afternoon_status, index, str(morning_time), str(afternoon_time), str(morning_selections), str(afternoon_selections))
            )
        
        conn.commit()
        conn.close()
        
        try:
            # 先移除现有的定时任务
            remove_schedule_jobs(user_id)

            # 如果有开启的定时，添加新的定时任务
            add_schedule_jobs(user_id, index, morning_status == 1, afternoon_status == 1)
            
            # 记录成功日志
            await log_operation(
                username,
                LogType.CRON,
                f"更新定时任务成功: {log_details}",
                request.client.host,
                True
            )
            
            # 返回成功状态和消息
            return JSONResponse({
                "success": True,
                "message": "定时设置已保存",
                "morning_status": morning_status == 1,
                "afternoon_status": afternoon_status == 1
            })
        except Exception as e:
            error_msg = f"保存定时设置失败: {str(e)}"
            logger.error(error_msg)
            
            # 记录错误日志
            await log_operation(
                username,
                LogType.CRON,
                f"更新定时任务失败: {error_msg}",
                request.client.host,
                False
            )
            
            return JSONResponse({
                "success": False,
                "message": error_msg
            }, status_code=500)
    except Exception as e:
        error_msg = f"保存定时设置失败: {str(e)}"
        logger.error(error_msg)
        
        # 记录错误日志
        await log_operation(
            username,
            LogType.CRON,
            f"更新定时任务失败: {error_msg}",
            request.client.host,
            False
        )
        
        return JSONResponse({
            "success": False,
            "message": error_msg
        }, status_code=500)


# 在应用启动时，启动调度器
@router.on_event("startup")
async def startup_event():
    try:
        success = start_scheduler()
    except Exception as e:
        logger.error(f"记录系统启动日志失败: {str(e)}")

# 在应用关闭时，关闭调度器
@router.on_event("shutdown")
async def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
