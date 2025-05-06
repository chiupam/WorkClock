import calendar
import datetime
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app import logger
from app.auth.dependencies import admin_required
from app.auth.utils import get_mobile_user_agent
from app.routes.admin.utils import get_admin_stats, get_admin_name, templates
from app.routes.index import get_attendance_info, show_sign_button
from app.routes.sign import check_sign_time
from app.routes.statistics import GetYueTjList, get_Attendance_Statistics
from app.utils.host import build_api_url
from app.utils.log import LogType, log_operation, log_sign_activity
from config import settings

DEPARTMENTS = {
    "3": "院领导",
    "7": "政治部",
    "11": "办公室",
    "10": "综合业务部",
    "8": "第一检察部",
    "9": "第二检察部",
    "4": "第三检察部",
    "5": "第四检察部",
    "12": "第五检察部",
    "15": "未成年人检察组",
    "6": "待入职人员",
    "13": "检委办",
    "2": "系统管理员",
    "1": "测试部门",
    "14": "退休离职人员"
}

class StatisticData(BaseModel):
    month: int
    year: Optional[int] = None

# 创建路由器
router = APIRouter()

@router.get("/privilege")
@admin_required
async def admin_privilege_page(request: Request):
    """
    管理员特权登录页面
    """
    
    # 获取基本统计信息
    stats = await get_admin_stats()
    
    # 获取open_id
    open_id = request.cookies.get("open_id")
    
    # 查询当前管理员信息
    admin_name = await get_admin_name(open_id)
    
    # 返回特权登录页面
    return templates.TemplateResponse(
        "admin/privilege.html", 
        {
            "request": request,
            "user_info": {"username": admin_name, "user_id": "admin"},
            "stats": stats,
            "page_title": "特权登录",
            "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@router.get("/embed")
@admin_required
async def admin_embed_user(request: Request):
    """
    管理员特权查看用户界面 - 嵌入iframe使用
    """
    try:
        # 获取请求参数
        user_id = request.query_params.get("user_id")
        
        if not user_id:
            return JSONResponse({
                "success": False, 
                "message": "用户ID不能为空"
            }, status_code=400)
        
        # 从真实服务器获取用户信息
        api_url = build_api_url('/Apps/getUserInfo')
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}
        data = {"userid": user_id, "unitcode": settings.UNIT_CODE}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, headers=headers, json=data)
            server_data = response.json()
        
        # 创建用户信息
        user_info = {
            "user_id": user_id,
            "username": server_data.get("xm", "未知用户"),
            "department_id": server_data.get("depid", ""),
            "department_name": server_data.get("dep", DEPARTMENTS.get(server_data.get("depid", ""), "未知部门")),
            "position": server_data.get("zw", "")
        }
        
        # 获取考勤信息
        now = datetime.datetime.now()
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}
        
        # 获取月度考勤数据
        yue_tj_list = await GetYueTjList(headers, user_id, str(now.year), str(now.month).zfill(2))
        is_workday = yue_tj_list[now.day - 1].get("workday") == 1
        
        # 处理考勤数据
        if not is_workday:
            # 非工作日
            attendance_data = []
            show_sign_btn = {"show": False, "message": "今天是休息日，无需打卡"}
        else:
            # 工作日，获取考勤数据
            attendance_data = await get_attendance_info(headers, user_id)
            show_sign_btn = show_sign_button(attendance_data)
        
        # 返回用户查看界面，使用index.html模板
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user_info": user_info,
                "attendance_data": attendance_data,
                "is_workday": is_workday,
                "show_sign_button": show_sign_btn,
                "current_month": now.month,
                "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "is_admin_view": True  # 标记为管理员查看模式
            }
        )
    except Exception as e:
        logger.error(f"嵌入用户界面失败: {str(e)}")
        return JSONResponse(
            {
                "success": False,
                "message": f"查看用户界面失败: {str(e)}"
            },
            status_code=500
        )

@router.post("/departments")
@admin_required
async def post_departments(request: Request):
    """
    获取部门列表API (POST方法)
    """
    try:
        # 构建部门列表
        departments = []
        
        for dept_id, dept_name in DEPARTMENTS.items():
            departments.append({
                "department_id": dept_id,
                "department_name": dept_name
            })
                
        return JSONResponse({
            "success": True,
            "departments": departments
        })
    except Exception as e:
        logger.error(f"获取部门列表失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取部门列表失败: {str(e)}"
        }, status_code=500)

@router.post("/users")
@admin_required
async def post_department_users(request: Request):
    """
    获取部门下的用户列表API (POST方法)
    """
    try:
        # 获取请求数据
        data = await request.json()
        department_id = data.get("department_id")
        
        if not department_id:
            return JSONResponse({
                "success": False,
                "message": "部门ID不能为空"
            }, status_code=400)
            
        # 校验部门ID是否存在
        if department_id not in DEPARTMENTS:
            return JSONResponse({
                "success": False,
                "message": "部门不存在"
            }, status_code=404)
            
        # 向真实服务器发送请求获取部门用户列表
        api_url = build_api_url('/Apps/getUserInfoList')
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}
        data = {"depid": department_id, "unitcode": settings.UNIT_CODE}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, headers=headers, json=data)
            users = [{key: item[key] for key in {'userid', 'username'} if key in item} for item in response.json()]
        
        return JSONResponse({
            "success": True,
            "users": users,
            "department_name": DEPARTMENTS[department_id]
        })
    except Exception as e:
        logger.error(f"获取部门用户失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取部门用户失败: {str(e)}"
        }, status_code=500)
    
@router.get("/user/embed")
@admin_required
async def get_user_embed(request: Request):
    """
    此函数用给前端返回内嵌页面，但是不返回用户信息，返回用户信息由post_user_embed函数返回
    """
    try:
        # 获取请求参数
        user_id = request.query_params.get("user_id")
        
        if not user_id:
            return JSONResponse({
                "success": False, 
                "message": "用户ID不能为空"
            }, status_code=400)
        
        # 返回空的用户页面框架
        return templates.TemplateResponse(
            "admin/embed.html",  # 使用新的模板
            {
                "request": request,
                "user_id": user_id,
                "is_admin_view": True,
                "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    except Exception as e:
        logger.error(f"加载嵌入页面失败: {str(e)}")
        return JSONResponse(
            {
                "success": False,
                "message": f"加载嵌入页面失败: {str(e)}"
            },
            status_code=500
        )

@router.post("/user/embed")
@admin_required
async def post_user_embed(request: Request):
    """
    此函数用以获取内嵌页面的用户信息，要求前端给后端返回（用户名、用户ID、部门名称、部门ID）
    """
    try:
        # 获取请求数据
        data = await request.json()
        user_id = data.get("user_id")
        
        if not user_id:
            return JSONResponse({
                "success": False,
                "message": "用户ID不能为空"
            }, status_code=400)
        
        # 检查前端是否传递了完整的用户信息
        user_name = data.get("userName")
        department_id = data.get("departmentId")
        department_name = data.get("departmentName")
        
        # 获取考勤信息
        now = datetime.datetime.now()
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}
        
        # 获取月度考勤数据
        yue_tj_list = await GetYueTjList(headers, user_id, str(now.year), str(now.month).zfill(2))
        is_workday = yue_tj_list[now.day - 1].get("isholiday")  == 0
        # 处理考勤数据
        if not is_workday:
            # 非工作日
            attendance_data = []
            show_sign_btn = {"show": False, "message": "今天是休息日，无需打卡"}
        else:
            # 工作日，获取考勤数据
            ua = get_mobile_user_agent(request.headers.get('User-Agent'))
            attendance_data = await get_attendance_info(ua, user_id)
            show_sign_btn = show_sign_button(attendance_data)
        
        return JSONResponse({
            "success": True,
            "user_info": data,
            "attendance_data": attendance_data,
            "is_workday": is_workday,
            "show_sign_button": show_sign_btn,
            "current_month": now.month,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取用户信息失败: {str(e)}"
        }, status_code=500)

@router.post("/user/embed/sign")
@admin_required
async def post_user_embed_sign(request: Request):
    """
    为用户执行签到操作API (POST方法)，与现有的embed.js兼容
    """
    try:
        # 获取请求数据
        data = await request.json()
        user_id = data.get("user_id")
        sign_type = data.get("sign_type")

        if not user_id or not sign_type:
            return JSONResponse({
                "success": False,
                "message": "用户ID和签到类型不能为空"
            }, status_code=400)
        
        username = data.get("user_name")
        sign_status = data.get("sign_status")

        # 检查当前时间是否可以打卡
        can_sign, _, message = check_sign_time(sign_status)
        if not can_sign:
            return JSONResponse({
                "success": False,
                "message": message
            }, status_code=400)
        

        dep_id = data.get("departmentId")

        api_url = build_api_url("/AttendanceCard/SaveAttCheckinout")
        headers = {"User-Agent": get_mobile_user_agent(request.headers.get("User-Agent", ""))}
        data = {"model": {"Aid": 0, "UnitCode": settings.UNIT_CODE, "userID": user_id, "userDepID": dep_id, "Mid": 134, "Num_RunID": 14, "lng": "", "lat": "", "realaddress": "", "iSDelete": 0, "administratorChangesRemark": settings.REAL_ADDRESS}, "AttType": 1}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=data, headers=headers)
            result = response.json()
            
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
    except Exception as e:
        logger.error(f"用户签到失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"用户签到失败: {str(e)}"
        }, status_code=500)
    
@router.get("/user/embed/metrics")
@admin_required
async def get_user_embed_metrics(request: Request):
    """
    GET方法，返回内嵌的用户考勤统计信息页面
    """
    try:
        # 获取请求参数
        user_id = request.query_params.get("user_id")
        
        if not user_id:
            return JSONResponse({
                "success": False, 
                "message": "用户ID不能为空"
            }, status_code=400)
        
        # 返回空的用户页面框架
        return templates.TemplateResponse(
            "admin/metrics.html",  # 使用新的模板
            {
                "request": request,
                "user_id": user_id,
                "is_admin_view": True,
                "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    except Exception as e:
        logger.error(f"加载嵌入页面失败: {str(e)}")
        return JSONResponse(
            {
                "success": False,
                "message": f"加载嵌入页面失败: {str(e)}"
            },
            status_code=500
        )

@router.post("/user/embed/metrics")
@admin_required
async def post_user_embed_metrics(request: Request):
    """
    获取用户统计信息API (POST方法)
    """
    
    try:
        # 获取请求数据
        data = await request.json()
        user_id = data.get("user_id")
        
        headers = {"User-Agent": get_mobile_user_agent(request.headers.get("User-Agent", ""))}

        # 获取年月参数(整数类型，用于计算)
        month_int = data.get("month")
        year_int = data.get("year") or datetime.datetime.now().year
        
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
    except Exception as e:
        logger.error(f"获取用户统计信息失败: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"获取用户统计信息失败: {str(e)}"
        }, status_code=500)


@router.get("/user/embed/schedule")
@admin_required
async def get_user_embed_schedule(request: Request):
    """
    GET方法，返回内嵌的用户定时设置页面
    """
    pass

@router.post("/user/embed/schedule")
@admin_required
async def post_user_embed_schedule(request: Request):
    """
    获取用户定时设置信息API (POST方法)
    """
    pass