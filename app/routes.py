import io
import logging
import os
import requests
import secrets
import shutil
import signal
import string
import subprocess
import threading
import time
import traceback
import zipfile
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request, current_app, session, redirect, url_for, make_response, \
    Response, send_file, stream_with_context
from flask_sse import sse
from flask_socketio import emit
from functools import wraps
from typing import Union, Any, Callable
from werkzeug import Response
import queue
import select
import uuid
import fcntl
from collections import defaultdict

import app.system as system
from app import db
from app.ciphertext import CookieCipher
from app.models import PermanentToken, SignLog, Logs, ScheduledTask, TaskLog
from app.scheduler import setup_scheduled_tasks
from app.system import get_version, check_update, get_system_info

main = Blueprint('main', __name__)

# 注册 sse blueprint
main.register_blueprint(sse, url_prefix='/stream')

# 存储活动进程信息
active_processes = {}

# 命令存储
running_commands = {}
command_outputs = defaultdict(queue.Queue)
command_expire_time = {}


def terminate_process(process):
    """尝试多种方式终止进程，兼容Docker容器环境"""
    try:
        if process.poll() is not None:  # 进程已退出
            return True
            
        # 首先尝试正常终止
        process.terminate()
        
        # 给进程一点时间来正常退出
        for _ in range(10):  # 尝试10次，每次等待0.1秒
            if process.poll() is not None:  # 进程已退出
                return True
            time.sleep(0.1)
            
        # 如果进程仍在运行，发送SIGKILL信号
        if process.poll() is None:
            try:
                os.kill(process.pid, signal.SIGKILL)
            except Exception as e:
                current_app.logger.error(f"SIGKILL终止进程失败: {str(e)}")
                
        return process.poll() is not None
    except Exception as e:
        current_app.logger.error(f"终止进程失败: {str(e)}\n{traceback.format_exc()}")
        return False


def get_cookie_value(name) -> Union[str, bool]:
    """
    获取并解密 cookie 值
    :param name: cookie 名称
    :return: 解密后的 cookie 值或 False
    """
    encrypted_value = request.cookies.get(name)
    if encrypted_value:
        return CookieCipher.decrypt_value(encrypted_value)
    return False


def verify(**kwargs):
    """
    验证 open_id, user_id, dep_id 是否匹配，可选择任意组合参数。
    :param kwargs: 动态传入 open_id, user_id, dep_id 等键值对
    :return: 查询到的记录或 None
    """
    # 过滤出有效的参数
    valid_params = {key: value for key, value in kwargs.items() if key in ['open_id', 'user_id', 'dep_id'] and value}

    # 如果没有有效参数，直接返回 False
    if not valid_params:
        return False

    # 动态查询
    return PermanentToken.query.filter_by(**valid_params).first()


def bind_user(user_id: int, user_name: str, dep_id: int, position: str, dep_name: str, open_id: str) -> bool:
    """
    绑定用户信息和 open_id
    :param user_id: 用户ID
    :param user_name: 用户名
    :param dep_id: 部门ID
    :param position: 职位
    :param dep_name: 部门名称
    :param open_id: open_id
    :return: 是否绑定成功
    """
    existing_binding = verify(user_id=user_id)

    if existing_binding:
        # 更新用户信息
        existing_binding.user_id = user_id
        existing_binding.user_name = user_name
        existing_binding.dep_id = dep_id
        existing_binding.position = position
        existing_binding.dep_name = dep_name
        existing_binding.open_id = open_id
        existing_binding.created_at = datetime.now()
        db.session.commit()
        return True

    # 创建新的绑定记录
    new_binding = PermanentToken(
        user_id=user_id,
        user_name=user_name,
        dep_id=dep_id,
        position=position,
        dep_name=dep_name,
        open_id=open_id,
        created_at=datetime.now()
    )
    db.session.add(new_binding)
    db.session.commit()
    return True


def add_sign_log(user_id, user_name, dep_id, dep_name, sign_type, sign_result):
    """
    添加打卡日志
    :param user_id: 用户ID
    :param user_name: 用户名
    :param dep_id: 部门ID
    :param dep_name: 部门名称
    :param sign_type: 打卡类型
    :param sign_result: 打卡结果
    """
    log = SignLog(
        user_id=user_id,
        user_name=user_name,
        dep_id=dep_id,
        dep_name=dep_name,
        sign_type=sign_type,
        sign_result=sign_result
    )
    db.session.add(log)
    db.session.commit()


def add_operation_log(user_name, dep_name, operation, details=None):
    """
    添加操作日志
    :param user_name: 用户名
    :param dep_name: 部门名称
    :param operation: 操作类型
    :param details: 操作详情
    """
    log = Logs(
        user_name=user_name,
        dep_name=dep_name,
        operation=operation,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()


def random_open_id() -> str:
    """
    生成随机 open_id
    :return: 随机 open_id
    """
    random_string = ''.join(
        secrets.choice(
            string.ascii_letters + string.digits
        ) for _ in range(20)
    )
    return "oFDlxxE_" + random_string


def get_mobile_user_agent(request_user_agent) -> str:
    """
    获取移动设备 user_agent
    :param request_user_agent: 请求头中的 user_agent
    :return: 移动设备 user_agent
    """
    default_mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.4(0x18000428) NetType/4G'

    # 如果没有 User-Agent，使用默认值
    if not request_user_agent:
        return default_mobile_ua

    # 检查是否是移动设备
    mobile_strings = ['Android', 'iPhone']
    is_mobile = any(x in request_user_agent for x in mobile_strings)

    if is_mobile:
        # 如果已经包含 MicroMessenger，直接使用原始 UA
        if 'MicroMessenger' in request_user_agent:
            return request_user_agent

        # 否则添加微信标识
        if 'Android' in request_user_agent:
            return "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.4(0x18000428) EdgA/131.0.0.0 NetType/4G"

    # 非移动设备返回默认值
    return default_mobile_ua


def fuckdaka_login(user_id: str, dep_id: int, dep_name: str) -> Union[str, Response, tuple[Response, int]]:
    """
    fuckdaka快捷登录
    :param user_id: 用户ID
    :param dep_id: 部门ID
    :param dep_name: 部门名称
    :return: 登录结果
    """
    try:
        new_open_id = random_open_id()
        user_name = "未知用户"

        # 获取部门用户列表
        response = requests.post(
            f"{current_app.config['HOST']}/Apps/getUserInfoList",
            headers={'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))},
            json={"unitcode": "530114", "depid": str(dep_id)}
        )
        result = next((item for item in response.json() if item["userid"] == int(user_id)), None)
        if not result:
            return render_template('root.html', phone="", error="未知错误")
        user_name = result['username']

        # 绑定用户信息
        bind_user(int(user_id), user_name, dep_id, "未知", dep_name, new_open_id)

        # 准备响应
        response = make_response(render_template('index.html'))

        # 设置加密的 cookie
        for cookie_name, cookie_value in [
            ('user_id', str(user_id)),
            ('open_id', new_open_id),
            ('verify_id', datetime.now().strftime('%Y%m%d'))  # 当天日期, 格式: YYYYMMDD
        ]:
            encrypted_value = CookieCipher.encrypt_value(cookie_value)
            response.set_cookie(
                cookie_name,
                encrypted_value,
                httponly=True,
                samesite='Lax'
            )
        add_operation_log(
            user_name=user_name,
            dep_name=dep_name,
            operation="FUCK登录",
            details="成功"
        )
        return response
    except Exception as e:
        print(f"Fuckdaka login error: {str(e)}")
        return jsonify({"success": False, "message": "获取用户信息失败"}), 500


@main.route('/', methods=['GET'])
def root() -> Union[Response, str]:
    """
    根路由
    :return: 登录页面
    """
    try:
        open_id = get_cookie_value('open_id')
        user_binding = verify(open_id=open_id)
        if open_id and user_binding:
            add_operation_log(
                user_name=user_binding.user_name,
                dep_name=user_binding.dep_name,
                operation="无密码登录",
                details="成功"
            )
            return redirect(url_for('main.index'))
        return render_template('root.html')

    except Exception as e:
        return render_template('root.html', error=str(e))


@main.route('/index', methods=['GET'])
def index() -> Union[Response, Response, str]:
    """
    主页
    :return: 主页
    """

    open_id = get_cookie_value('open_id')
    user_id = get_cookie_value('user_id')

    if not open_id or not user_id:
        return redirect(url_for('main.root'))

    # 检查数据库中是否存在该 open_id 的记录
    user_binding: Union[PermanentToken, None] = verify(open_id=open_id)

    # 如果找不到记录或者 user_id 不匹配，说明是非法请求
    if not user_binding or str(user_binding.user_id) != str(user_id):
        add_operation_log(
            user_name="非法用户", dep_name="非法用户",
            operation="无密码登录", details="失败"
        )
        response = make_response(redirect(url_for('main.root')))
        response.delete_cookie('open_id')
        response.delete_cookie('user_id')
        response.delete_cookie('verify_id')
        return response

    # 渲染登录页面并传入数据
    add_operation_log(
        user_name=user_binding.user_name, dep_name=user_binding.dep_name,
        operation="无密码登录", details="成功"
    )
    return render_template('index.html')


@main.route('/index', methods=['POST'])
def login() -> render_template:
    """
    登录
    :return: 登录页面
    """

    phone = request.form.get('phone')
    password = request.form.get('password')

    if not phone or not password:
        return render_template('root.html', error='请输入手机号码和密码')

    try:
        # 如果是管理员登录, 则添加 3 分钟的 session 会话有效期
        if phone == current_app.config['ADMIN_USERNAME']:
            if password != current_app.config['ADMIN_PASSWORD']:
                add_operation_log(
                    user_name="管理员", dep_name="管理员",
                    operation="密码登录", details="密码错误"
                )
                return render_template('root.html', phone=phone, error="管理员密码错误")
            session['admin'] = True  # 设置管理员会话
            current_app.permanent_session_lifetime = timedelta(minutes=3)  # 设置会话有效期为 3 分钟
            add_operation_log(
                user_name="管理员", dep_name="管理员",
                operation="密码登录", details="成功"
            )
            session.permanent = True  # 设置会话为永久会话
            session.modified = True  # 确保会话已修改
            return redirect(url_for('main.dashboard'))

        # 如果使用fuckdaka快捷添加部门编号和用户编号, 则验证fuckdaka密码
        if phone.startswith('fuckdaka/'):
            if password != current_app.config['FUCK_PASSWORD']:
                return render_template('root.html', phone="", error="未知错误")
            phone = phone.replace('fuckdaka/', '')
            dep_id, user_id = phone.split('/')
            dep_name_base = {
                "3": "院领导", "7": "政治部",
                "11": "办公室", "10": "综合业务部",
                "8": "第一检察部", "9": "第二检察部",
                "4": "第三检察部", "5": "第四检察部",
                "12": "第五检察部", "6": "待入职人员",
                "13": "检委办", "15": "未成年人检察组", 
                "2": "系统管理员",
                "1": "测试部门", "14": "退休离职人员"
            }
            if dep_id not in dep_name_base:
                return render_template('root.html', phone="", error="未知错误")
            return fuckdaka_login(user_id, dep_id, dep_name_base[dep_id])

        # 普通用户登录
        open_id = get_cookie_value('open_id')
        user_id = get_cookie_value('user_id')
        user_binding = verify(open_id=open_id, user_id=user_id)
        if user_binding:
            response = make_response(render_template('index.html'))
            # 设置加密的 cookie
            for cookie_name, cookie_value in [
                ('user_id', str(user_binding.user_id)), ('open_id', open_id),
                ('verify_id', datetime.now().strftime('%Y%m%d'))  # 当天日期, 格式: YYYYMMDD
            ]:
                encrypted_value = CookieCipher.encrypt_value(cookie_value)
                response.set_cookie(cookie_name, encrypted_value, httponly=True, samesite='Lax')
            add_operation_log(
                user_name=user_binding.user_name, dep_name=user_binding.dep_name,
                operation="无密码登录", details="成功"
            )
            return response

        # 新用户登录流程
        new_open_id = random_open_id()
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}

        # 登录验证
        login_response = requests.post(
            f"{current_app.config['HOST']}/Apps/wxLogin",
            headers=headers,
            json={"UserCccount": phone, "Password": password, "OpenID": new_open_id},
            allow_redirects=False
        )

        login_result: dict = login_response.json()
        if not login_result.get('success'):
            error = f"登录失败: {login_result.get('message', '未知错误')}"
            return render_template('root.html', phone=phone, error=error)

        # 获取用户信息
        user_response = requests.post(
            f"{current_app.config['HOST']}/Apps/AppIndex",
            headers={**headers, "Cookie": login_response.headers.get('Set-Cookie')},
            params={'UnitCode': '530114'},
            json={},
            allow_redirects=False
        )

        user_info: dict = user_response.json()
        if not user_info.get('success'):
            return render_template('index.html', phone=phone, error="获取用户信息失败")

        user_data = user_info['data']

        # 绑定用户信息
        bind_user(
            user_data['UserID'], user_data['UserName'],
            user_data['DepID'], user_data['Position'], user_data['DepName'],
            new_open_id
        )

        # 准备响应
        response = make_response(render_template('index.html'))

        # 设置加密的 cookie
        for cookie_name, cookie_value in [
            ('user_id', str(user_data['UserID'])),
            ('open_id', new_open_id),
            ('verify_id', datetime.now().strftime('%Y%m%d'))  # 当天日期, 格式: YYYYMMDD
        ]:
            encrypted_value = CookieCipher.encrypt_value(cookie_value)
            response.set_cookie(
                cookie_name,
                encrypted_value,
                httponly=True,
                samesite='Lax'
            )
        add_operation_log(
            user_name=user_data['UserName'], dep_name=user_data['DepName'],
            operation="密码登录", details="成功"
        )
        return response

    except Exception as e:
        return render_template('index.html', error=f"系统错误: {str(e)}")


@main.route('/logout')
def logout() -> Response:
    """
    登出
    :return: 登出页面
    """

    try:
        open_id = get_cookie_value('open_id')
        binding = verify(open_id=open_id)
        if open_id and binding:
            binding.open_id = f"DELETE_{binding.id}"
            binding.created_at = datetime.now()
            db.session.commit()
        session.clear()

        response = make_response(redirect(url_for('main.root')))
        response.delete_cookie('open_id')
        response.delete_cookie('user_id')
        response.delete_cookie('verify_id')
        return response

    except Exception as e:
        return redirect(url_for('main.root', error=str(e)))


@main.route('/getInfo', methods=['POST'])
def get_info() -> tuple[Response, int]:
    """
    获取用户信息
    :return: 用户信息
    """

    user_id = get_cookie_value('user_id')
    open_id = get_cookie_value('open_id')

    user_binding = verify(open_id=open_id, user_id=user_id)
    if not user_binding:
        return jsonify({"success": False, "message": "用户信息不存在"}), 404

    # 准备返回数据
    attendance_data, _ = get_attendance()
    result = {
        "success": True,
        "user": {
            "userId": user_binding.user_id,
            "depId": user_binding.dep_id,
            "userName": user_binding.user_name,
            "position": user_binding.position,
            "depName": user_binding.dep_name
        },
        "attendance": {**attendance_data['data'], "isworkingday": attendance_data['isworkingday']},
        "button": show_sign_button(attendance_data['data'])
    }
    return jsonify(result), 200


def get_attendance() -> Union[tuple[Response, int], tuple[dict[str, Union[dict, bool]], int], tuple[dict[str, Union[list[Any], bool]], int]]:
    """
    获取考勤数据
    :return: 考勤数据
    """

    blank_data = {"needReminder": False, "clockInRecord": None, "clockOutRecord": None}
    try:
        user_id = get_cookie_value('user_id')
        open_id = get_cookie_value('open_id')

        user_binding = verify(open_id=open_id, user_id=user_id)
        if not user_binding:
            return jsonify({"success": False, "message": "用户信息不存在"}), 404

        params = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}
        response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/GetAttCheckinoutList",
            params=params,
            headers={'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))},
            allow_redirects=False
        )
        response.raise_for_status()
        processed_data = process_attendance_data(response.json())

        now = datetime.now()
        response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/GetYueTjList",
            headers={'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))},
            params={**params, **{"year": f"{now.year}年", "month": f"{str(now.month).zfill(2)}月"}},
            json={},
            allow_redirects=False
        )
        response.raise_for_status()
        working = bool(response.json()[now.day - 1]['isworkingday'])

        return {"success": True, "data": processed_data, "isworkingday": working}, 200

    except Exception as e:
        blank_data['errorMsg'] = str(e)
        return {"success": False, "data": []}, 500


def process_attendance_data(raw_data) -> dict:
    """
    处理考勤数据
    :param raw_data: 原始考勤数据
    :return: 处理后的考勤数据
    """

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 过滤出天的记录
    today_records = []
    for record in raw_data:
        timestamp = int(record['clockTime'].replace('/Date(', '').replace(')/', ''))
        record_date = datetime.fromtimestamp(timestamp / 1000)  # 转换
        if record_date.date() == today.date():
            today_records.append(record)
    # 分离上班下班记录
    clock_in = next((record for record in today_records if record['clockType'] == 1), None)
    clock_out = next((record for record in today_records if record['clockType'] == 2), None)

    # 检查是否要显示补卡提醒
    current_time = now.hour * 60 + now.minute
    work_end_time = 17 * 60  # 17:00
    need_reminder = current_time >= work_end_time and not clock_in

    # 格式化记录
    def format_record(_record):
        if not _record:
            return None

        _timestamp = int(_record['clockTime'].replace('/Date(', '').replace(')/', ''))
        clock_time = datetime.fromtimestamp(_timestamp / 1000)

        return {
            "type": "上班" if _record['clockType'] == 1 else "下班",
            "standardTime": "09:00" if _record['clockType'] == 1 else "17:00",
            "clockTime": clock_time.strftime("%H:%M:%S"),
            "location": _record['administratorChangesRemark'] or "未知地点"
        }

    return {
        "needReminder": need_reminder,
        "clockInRecord": format_record(clock_in),
        "clockOutRecord": format_record(clock_out)
    }


def show_sign_button(attendance_records: dict) -> dict:
    """
    显示打卡按钮
    :param attendance_records: 考勤数据
    :return: 打卡按钮状态和消息
    """

    if attendance_records.get("errorMsg"):
        return {"show": False, "message": attendance_records.get("errorMsg")}

    # 获取当前时间
    now = datetime.now()
    current_time = now.hour * 60 + now.minute  # 转换为分钟

    # 定义时间段
    morning_start = 7 * 60  # 7:00
    morning_end = 9 * 60  # 9:00
    evening_start = 17 * 60  # 17:00
    evening_end = 23 * 60 + 59  # 23:59

    # 上班时间段（7:00-9:00）
    if morning_start <= current_time <= morning_end:
        # 如果已打卡，不继续打卡，否则会打早退卡
        if attendance_records.get("clockInRecord"):
            return {"show": False, "message": "今日已完成上班打卡"}
        else:
            return {"show": True, "message": ""}

    # 非打卡时间段（9:01-16:59）
    elif morning_end < current_time < evening_start:
        return {"show": False, "message": "上班期间严禁打卡"}

    # 下班时间段（17:00-23:59）
    elif evening_start <= current_time <= evening_end:
        if attendance_records.get("clockOutRecord"):
            return {"show": False, "message": "今日已完成下班打卡"}
        else:
            return {"show": True, "message": ""}
    else:
        return {"show": False, "message": "非打卡时间段"}


@main.route('/sign', methods=['POST'])
def sign() -> Union[tuple[Response, int], dict[str, Union[str, bool]], dict[str, Union[str, bool]], dict[str, Union[str, bool]], dict[str, Union[str, bool]], Response]:
    """
    打卡
    :return: 打卡结果
    """

    try:
        open_id = get_cookie_value('open_id')
        user_id = get_cookie_value('user_id')
        verify_id = get_cookie_value('verify_id')
        dep_id = request.json.get('depId')

        user_binding = verify(open_id=open_id, user_id=user_id, dep_id=dep_id)
        if not user_binding:
            return jsonify({"success": False, "message": "您是非法用户, 相关数据已做强记录且通知超级管理员"}), 404

        att_type = request.json.get('attType')
        has_ClockIn = request.json.get('clockIn')
        has_ClockOut = request.json.get('clockOut')

        # 获取当前时间
        now = datetime.now()
        current_time = now.hour * 60 + now.minute  # 转换为分钟

        # 定义时间段
        morning_start = 7 * 60  # 7:00
        morning_end = 9 * 60  # 9:00
        evening_start = 17 * 60  # 17:00
        evening_end = 23 * 60 + 59  # 23:59

        if verify_id != now.strftime('%Y%m%d'):
            attendance_data, _ = get_attendance()
            if not show_sign_button(attendance_data['data'])['show']:
                return jsonify({"success": False, "message": "当天浏览器缓存数据异常, 请刷新页面后重试"}), 400
            attendance = attendance_data['data']  # {'needReminder': False, 'clockInRecord': None, 'clockOutRecord': None}
            has_ClockIn, has_ClockOut = attendance['clockInRecord'], attendance['clockOutRecord']
            att_type = "下班" if now.hour >= 17 else "上班"

            # 上班时间段（7:00-9:00）
        if morning_start <= current_time <= morning_end:
            # 如果已打卡，不继续打卡，否则会打早退卡
            if has_ClockIn:
                return {"success": False, "message": "今日已完成上班打卡"}

        # 非打卡时间段（9:01-16:59）
        elif morning_end < current_time < evening_start:
            return {"success": False, "message": "上班期间严禁打卡"}

        # 下班时间段（17:00-23:59）
        elif evening_start <= current_time <= evening_end:
            if has_ClockOut:
                return {"success": False, "message": "今日已完成下班打卡"}
        else:
            return {"success": False, "message": "非打时间段"}

        result = fast_sign(user_id, dep_id)

        add_sign_log(
            user_id, user_binding.user_name,
            dep_id, user_binding.dep_name,
            att_type, result['message']
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def fast_sign(user_id, dep_id) -> dict:
    """
    快捷打卡
    :param user_id: 用户ID
    :param dep_id: 部门ID
    :return: 打卡结果
    """

    try:
        # 使用日志记录
        logger = logging.getLogger(__name__)
        
        # 获取HOST配置
        host = current_app.config.get('HOST', '')
        
        if not host:
            logger.error("未配置HOST环境变量，无法发送打卡请求")
            return {"success": False, "message": "未配置HOST环境变量"}
        
        # 发起打卡请求
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
                "realaddress": "",
                "iSDelete": 0,
                "administratorChangesRemark": "呈贡区人民检察院"
            },
            "AttType": 1
        }
        
        # 定义默认User-Agent
        default_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
        
        # 不再尝试从请求上下文获取UA
        user_agent = default_ua
            
        response = requests.post(
            f"{host}/AttendanceCard/SaveAttCheckinout",
            headers={'User-Agent': user_agent},
            json=data,
            allow_redirects=False
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        import traceback
        logger.error(f"打卡失败: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        return {"success": False, "message": str(e)}


@main.route('/getYueTjList')
def get_yue_tj_list() -> Union[tuple[Response, int], Response]:
    """
    获取月统计数据
    :return: 月统计数据
    """

    try:
        user_id = get_cookie_value('user_id')
        open_id = get_cookie_value('open_id')
        month = request.args.get('month')

        user_binding = verify(open_id=open_id, user_id=user_id)
        if not user_binding:
            return jsonify({"success": False, "message": "用户信息不存在"}), 404

        now = datetime.now()
        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}

        # 获取出勤统计数据
        attend_stat_params = {"UnitCode": "530114", "UserID": user_id, "SetClass": "1", "Mid": "134", "QueryType": "2"}
        attend_stat_response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/get_Attendance_Statistics",
            headers=headers,
            data={**attend_stat_params, **{"Syear": f"{now.year}年", "Smonth": f"{month.zfill(2)}月"}},
            allow_redirects=False
        )
        attend_stat_response.raise_for_status()
        attend_stat_dict = attend_stat_response.json()[0]["Attend_Stat_List"][0]
        attend_stat_key_list = ["LeaveDays", "LateNumber", "ZtNumber", "LackCarNumber"]  # 请假、迟到、早退、缺卡
        attend_stat_data = {key: attend_stat_dict[key] for key in attend_stat_key_list}

        # 获取月统计数据
        yue_tj_params = {"AttType": "1", "UnitCode": "530114", "userid": user_id, "Mid": "134"}
        yue_tj_response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/GetYueTjList",
            headers=headers,
            params={**yue_tj_params, **{"year": f"{now.year}年", "month": f"{month.zfill(2)}月"}},
            allow_redirects=False
        )
        yue_tj_response.raise_for_status()
        yue_tj_list = yue_tj_response.json()
        # 日期、是否节假日、加班、请假、上班打卡、下班打卡、上班补卡、下班补卡
        yue_tj_key_dict = {'rq', 'isholiday', 'jjr', 'IsQj', 'SWSBDKCS', 'XWXBDKCS', 'IsSwSbbuka', 'IsXwXbbuka'}
        yue_tj_data = [{key: item[key] for key in yue_tj_key_dict if key in item} for item in yue_tj_list]
        return jsonify({"statistics": attend_stat_data, "details": yue_tj_data})  # statistics, details

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def admin_required(f) -> Callable[[tuple[Any, ...], dict[str, Any]], Union[Response, Any]]:
    """
    管理员权限验证
    :param f: 目标函数
    :return: 目标函数
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):  # 检查是否是管理员登录
            return redirect(url_for('main.root'))  # 如果不是，重定向到首页
        return f(*args, **kwargs)  # 如果是，继续执行目标函数

    return decorated_function


@main.route('/admin')
@main.route('/dashboard')
@admin_required
def dashboard() -> Union[str, Response]:
    """
    管理员主页
    :return: 管理员主页
    """

    try:
        # 获取打卡日志
        logs = SignLog.query.order_by(SignLog.sign_time.desc()).all()

        # 处理日志数据
        log_data = [{
            'sign_time': log.sign_time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': log.user_name,
            'user_id': log.user_id,
            'dep_name': log.dep_name,
            'dep_id': log.dep_id,
            'sign_type': log.sign_type,
            'sign_result': log.sign_result
        } for log in logs]

        # 渲染模板并传入数据
        return render_template('dashboard.html', logs=log_data)

    except Exception as e:
        return redirect(url_for('main.root', error=str(e)))


@main.route('/admin/operation', methods=['GET'])
@admin_required
def admin_operation() -> render_template:
    """
    操作日志
    :return: 操作日志
    """

    try:
        # 获取数据库所有数据
        logs = Logs.query.order_by(Logs.created_at.desc()).all()

        # 处理数据库数据
        log_data = [{
            'user_name': log.user_name,
            'dep_name': log.dep_name,
            'operation': log.operation,
            'details': log.details,
            'ip_address': log.ip_address,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for log in logs]

        # 渲染模板并传入数据
        return render_template('operation.html', logs=log_data)

    except Exception as e:
        return redirect(url_for('main.root', error=str(e)))


@main.route('/admin/db', methods=['GET'])
@admin_required
def admin_db() -> render_template:
    """
    数据库管理
    :return: 数据库管理
    """

    try:
        # 获取数据库所有数据
        bindings = PermanentToken.query.order_by(PermanentToken.created_at.desc()).all()

        # 处理数据库数据
        db_data = [{
            'index': idx + 1,
            'user_name': f"{binding.user_name}({binding.user_id})",
            'department': f"{binding.dep_name}({binding.dep_id})",
            'open_id': binding.open_id,
            'created_at': binding.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for idx, binding in enumerate(bindings)]

        # 渲染模板并传入数据
        return render_template('database.html', bindings=db_data)

    except Exception as e:
        return redirect(url_for('main.root', error=str(e)))


@main.route('/admin/logout')
@admin_required
def admin_logout() -> Response:
    """
    管理员登出
    :return: 登出页面
    """

    session.clear()
    open_id = get_cookie_value('open_id')
    binding = verify(open_id=open_id)
    if open_id and binding:
        binding.open_id = f"DELETE_{datetime.now().strftime('%Y%m%d%H%M%S')}_{binding.id}"
        binding.created_at = datetime.now()
        db.session.commit()

    response = make_response(redirect(url_for('main.root')))
    response.delete_cookie('open_id')
    response.delete_cookie('user_id')
    response.delete_cookie('verify_id')
    return response


# 添加新的级打卡由
@main.route('/admin/super', methods=['GET', 'POST'])
@admin_required
def admin_super() -> Union[Response, str, tuple[Response, int], Response]:
    """
    超级管理员页面
    :return: 超级管理员页面
    """

    try:

        headers = {'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))}

        if request.method == 'POST':
            # 获取部门用户列表
            dep_id = request.json.get('depId')
            response = requests.post(
                f"{current_app.config['HOST']}/Apps/getUserInfoList",
                headers=headers,
                json={"unitcode": "530114", "depid": dep_id}
            )
            users = response.json()
            filtered_data = [{key: item[key] for key in {'userid', 'username'} if key in item} for item in users]
            return jsonify({"success": True, "users": filtered_data})

        else:
            # GET 请求获取部门列表
            response = requests.post(
                f"{current_app.config['HOST']}/Apps/GetDepList",
                headers=headers,
                json={"unitcode": "530114"},
            )
            departments = response.json()
            filtered_data = [{key: item[key] for key in {'depid', 'depname'} if key in item} for item in departments]
            return render_template('super.html', departments=filtered_data)

    except Exception as e:
        if request.method == 'POST':
            return jsonify({"success": False, "message": str(e)}), 500
        return redirect(url_for('main.root', error=str(e)))


@main.route('/admin/user', methods=['POST'])
@admin_required
def admin_user() -> Union[Response, tuple[Response, int]]:
    """
    管理员用户管理
    :return: 管理员用户管理
    """

    try:
        data = request.json
        new_open_id = random_open_id()

        dep_name_base = {
            "3": "院领导",
            "7": "政治部",
            "11": "办公室",
            "10": "综合业务部",
            "8": "第一检察部",
            "9": "第二检察部",
            "4": "第三检察部",
            "5": "第四检察部",
            "12": "第五检察部",
            "6": "待入职人员",
            "13": "检委办",
            "15": "未成年人检察组",
            "2": "系统管理员",
            "1": "测试部门",
            "14": "退休离职人员"
        }

        # 绑定用户信息
        bind_user(data['userId'], data['username'], data['depId'], "临时", dep_name_base[data['depId']], new_open_id)

        # 准备响应
        response = make_response(jsonify({"success": True, "redirect": url_for('main.index')}))

        # 设置加密的 cookie
        for cookie_name, cookie_value in [
            ('user_id', str(data['userId'])),
            ('open_id', new_open_id),
            ('verify_id', datetime.now().strftime('%Y%m%d'))
        ]:
            encrypted_value = CookieCipher.encrypt_value(cookie_value)
            response.set_cookie(
                cookie_name,
                encrypted_value,
                httponly=True,
                samesite='Lax'
            )

        return response

    except Exception as e:
        response_data = {
            "success": False,
            "redirect": url_for('main.root', error=str(e)),
            "message": str(e)
        }
        response = make_response(jsonify(response_data))
        return response, 500


@main.route('/getScheduleSettings', methods=['POST'])
def get_schedule_settings() -> Union[tuple[Response, int], dict]:
    """
    获取用户定时打卡设置
    :return: 定时打卡设置
    """
    try:
        # 从 cookie 获取用户信息
        user_id = get_cookie_value('user_id')
        open_id = get_cookie_value('open_id')
        
        # 验证用户有效性
        user_binding = verify(open_id=open_id, user_id=user_id)
        if not user_binding:
            return jsonify({"success": False, "message": "用户信息不存在"}), 404
            
        # 查询用户的定时任务设置
        task = ScheduledTask.query.filter_by(user_id=user_id).first()
        
        # 获取用户在定时任务中的序号
        user_position = 0
        if task:
            # 如果用户已有定时任务，计算用户的位置
            enabled_tasks = ScheduledTask.query.filter_by(enabled=True).order_by(ScheduledTask.created_at).all()
            for idx, enabled_task in enumerate(enabled_tasks):
                if enabled_task.user_id == int(user_id):
                    user_position = idx
                    break
        else:
            # 如果用户没有定时任务，计算新用户将会是第几个
            user_position = ScheduledTask.query.filter_by(enabled=True).count()
            
        # 从应用配置中获取打卡时间
        morning_times_by_user = current_app.config.get('MORNING_TIMES_BY_USER')
        afternoon_times_by_user = current_app.config.get('AFTERNOON_TIMES_BY_USER')
        max_users = current_app.config.get('MAX_SCHEDULED_USERS', 3)
        
        # 确保位置在有效范围内
        if user_position > max_users - 1:
            user_position = -1  # 表示超出限制
            
        # 初始化返回值
        settings = {
            "scheduleMorning": task.schedule_morning if task else False,
            "scheduleAfternoon": task.schedule_afternoon if task else False
        }
        
        # 准备用户的时间表
        morning_times = []
        afternoon_times = []
        
        if 0 <= user_position < len(morning_times_by_user):
            # 转换时间格式为字符串
            morning_times = [f"{hour:02d}:{minute:02d}" for hour, minute in morning_times_by_user[user_position]]
            afternoon_times = [f"{hour:02d}:{minute:02d}" for hour, minute in afternoon_times_by_user[user_position]]
        
        # 获取当前启用的任务数量
        current_users = ScheduledTask.query.filter_by(enabled=True).count()
        
        # 返回结果
        return jsonify({
            "success": True, 
            "settings": settings,
            "schedule_times": {
                "user_position": user_position,
                "morning_times": morning_times,
                "afternoon_times": afternoon_times
            },
            "max_users": max_users,
            "current_users": current_users
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main.route('/saveScheduleSettings', methods=['POST'])
def save_schedule_settings() -> Union[tuple[Response, int], dict]:
    """
    保存用户定时打卡设置
    :return: 保存结果
    """
    try:
        # 从 cookie 获取用户信息
        user_id = get_cookie_value('user_id')
        open_id = get_cookie_value('open_id')
        
        # 验证用户有效性
        user_binding = verify(open_id=open_id, user_id=user_id)
        if not user_binding:
            return jsonify({"success": False, "message": "用户信息不存在"}), 404
            
        # 获取请求数据
        data = request.json
        schedule_morning = data.get('scheduleMorning', False)
        schedule_afternoon = data.get('scheduleAfternoon', False)
        
        # 查询用户的现有设置
        task = ScheduledTask.query.filter_by(user_id=user_id).first()
        
        # 如果用户之前没有设置并准备设置新任务
        if not task and (schedule_morning or schedule_afternoon):
            # 检查当前已启用的定时任务数量
            enabled_tasks_count = ScheduledTask.query.filter_by(enabled=True).count()
            
            # 如果已经有3个用户设置了定时任务，则拒绝新添加的请求
            if enabled_tasks_count >= 3:
                return jsonify({
                    "success": False, 
                    "message": f"定时任务队列({enabled_tasks_count}/3)已排满，暂无法添加新的定时任务"
                })
        
        if task:
            # 更新现有设置
            task.schedule_morning = schedule_morning
            task.schedule_afternoon = schedule_afternoon
            # 如果两个打卡都没有启用，则将任务状态设置为禁用
            task.enabled = schedule_morning or schedule_afternoon
            task.updated_at = datetime.now()
        else:
            # 创建新设置
            task = ScheduledTask(
                user_id=user_binding.user_id,
                user_name=user_binding.user_name,
                dep_id=user_binding.dep_id,
                dep_name=user_binding.dep_name,
                schedule_morning=schedule_morning,
                schedule_afternoon=schedule_afternoon,
                enabled=schedule_morning or schedule_afternoon  # 设置启用状态
            )
            db.session.add(task)
            
        # 保存到数据库
        db.session.commit()
        
        # 记录操作日志
        add_operation_log(
            user_binding.user_name,
            user_binding.dep_name,
            "设置定时打卡",
            f"早上打卡: {schedule_morning}, 下午打卡: {schedule_afternoon}, 启用状态: {task.enabled}"
        )
        
        # 重新配置定时任务
        setup_scheduled_tasks()
        
        return jsonify({"success": True, "message": "定时打卡设置已保存"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@main.route('/admin/tasks', methods=['GET'])
@admin_required
def admin_tasks() -> render_template:
    """
    定时任务管理
    :return: 定时任务管理页面
    """
    try:
        # 获取所有定时任务设置
        tasks = ScheduledTask.query.order_by(ScheduledTask.updated_at.desc()).all()
        task_logs = TaskLog.query.order_by(TaskLog.created_at.desc()).limit(100).all()
        
        # 处理数据
        task_data = [{
            'id': task.id,
            'user_name': task.user_name,
            'user_id': task.user_id,
            'dep_name': task.dep_name,
            'dep_id': task.dep_id,
            'morning': task.schedule_morning,
            'afternoon': task.schedule_afternoon,
            'enabled': task.enabled,
            'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        } for task in tasks]
        
        log_data = [{
            'id': log.id,
            'user_name': log.user_name,
            'user_id': log.user_id,
            'dep_name': log.dep_name,
            'task_type': log.task_type,
            'task_time': log.task_time,
            'status': log.status,
            'message': log.message,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for log in task_logs]
        
        # 计算当前启用的有效任务数（同时启用了早上或下午打卡的任务）
        active_tasks_count = len([
            task for task in tasks 
            if task.enabled and (task.schedule_morning or task.schedule_afternoon)
        ])
        max_users = current_app.config.get('MAX_SCHEDULED_USERS', 3)
        
        # 渲染模板并传入数据
        return render_template(
            'tasks.html', 
            tasks=task_data, 
            logs=log_data,
            active_tasks_count=active_tasks_count,
            max_users=max_users
        )
    
    except Exception as e:
        return redirect(url_for('main.root', error=str(e)))


@main.route('/update', methods=['POST'])
def update():
    try:
        # 获取应用根目录
        app_root = os.getcwd()  # 在Docker中这通常是/app
        
        # 设置日志对象用于收集详细日志
        log_messages = []
        def add_log(msg):
            log_messages.append(msg)
            logging.info(msg)
        
        # 使用GitHub API直接下载ZIP归档，而不是使用git命令
        repo_dir = os.path.join(app_root, 'repo')
        zip_url = "https://github.com/chiupam/WorkClock/archive/refs/heads/main.zip"
        
        # 下载ZIP文件
        add_log("正在从GitHub下载最新代码...")
        try:
            response = requests.get(zip_url, timeout=10)
            if response.status_code != 200:
                error_msg = f"下载失败，状态码: {response.status_code}"
                add_log(error_msg)
                return jsonify({"success": False, "log": "\n".join(log_messages), "message": error_msg})
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            add_log(error_msg)
            return jsonify({"success": False, "log": "\n".join(log_messages), "message": error_msg})
        
        add_log("代码下载完成，准备解压...")
        
        # 处理目录
        try:
            # 确保临时目录存在
            temp_dir = os.path.join(app_root, 'temp_extract')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
            
            # 确保repo目录存在
            if not os.path.exists(repo_dir):
                os.makedirs(repo_dir, exist_ok=True)
            
            # 清空临时目录
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            
            # 清空repo目录
            for item in os.listdir(repo_dir):
                item_path = os.path.join(repo_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        except Exception as e:
            error_msg = f"准备目录失败: {str(e)}"
            add_log(error_msg)
            return jsonify({"success": False, "log": "\n".join(log_messages), "message": error_msg})
        
        # 解压文件
        try:
            z = zipfile.ZipFile(io.BytesIO(response.content))
            z.extractall(temp_dir)
            add_log("文件解压完成")
        except Exception as e:
            error_msg = f"解压失败: {str(e)}"
            add_log(error_msg)
            return jsonify({"success": False, "log": "\n".join(log_messages), "message": error_msg})
        
        # 检查解压后的目录
        extracted_dir = os.path.join(temp_dir, 'WorkClock-main')
        if not os.path.exists(extracted_dir):
            error_msg = f"解压后未找到主目录: {extracted_dir}"
            add_log(error_msg)
            return jsonify({"success": False, "log": "\n".join(log_messages), "message": error_msg})
        
        # 复制文件
        try:
            add_log("开始复制文件...")
            # 复制到repo目录
            for item in os.listdir(extracted_dir):
                s = os.path.join(extracted_dir, item)
                d = os.path.join(repo_dir, item)
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
            add_log("文件复制到repo目录完成")
            
            # 复制到app目录
            for item in os.listdir(repo_dir):
                s = os.path.join(repo_dir, item)
                d = os.path.join(app_root, item)
                if item in ['.git', '.github', 'repo', 'temp_extract', 'instance']:
                    continue
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                else:
                    if os.path.exists(d):
                        os.remove(d)
                    shutil.copy2(s, d)
        except Exception as e:
            error_msg = f"复制文件失败: {str(e)}"
            add_log(error_msg)
            return jsonify({"success": False, "log": "\n".join(log_messages), "message": error_msg})
        
        add_log("更新完成，准备重启应用...")
        
        # 异步执行重启，防止响应被中断
        def restart_app():
            try:
                time.sleep(1)  # 延迟1秒，确保HTTP响应已发送
                
                # 尝试获取Gunicorn主进程PID（通常是当前进程的父进程）
                master_pid = os.getppid()
                
                # 向Gunicorn主进程发送SIGHUP信号，触发优雅重启
                os.kill(master_pid, signal.SIGHUP)
                logging.info(f"已向主进程 {master_pid} 发送重启信号")
            except Exception as e:
                logging.error(f"通过SIGHUP重启失败: {str(e)}")
                # 如果上面方法失败，尝试更激进的方式
                try:
                    # 找到所有gunicorn进程
                    pids = subprocess.check_output(["pgrep", "gunicorn"]).decode().strip().split("\n")
                    # 向所有进程发送HUP信号
                    for pid in pids:
                        try:
                            if pid.strip():
                                pid_int = int(pid.strip())
                                os.kill(pid_int, signal.SIGHUP)
                                logging.info(f"已向进程 {pid_int} 发送重启信号")
                        except Exception as e:
                            logging.error(f"向进程 {pid} 发送信号失败: {str(e)}")
                except Exception as e:
                    logging.error(f"通过pgrep重启失败: {str(e)}")
                    # 如果所有方法都失败，则直接退出（依赖Docker的restart策略）
                    logging.warning("尝试通过exit(0)触发Docker重启")
                    os._exit(0)
        
        # 在单独的线程中执行重启
        import threading
        restart_thread = threading.Thread(target=restart_app)
        restart_thread.daemon = True
        restart_thread.start()
        
        return jsonify({
            "success": True, 
            "log": "\n".join(log_messages) + "\n更新完成，应用即将重启...",
            "message": "更新成功，应用即将重启"
        })
    except Exception as e:
        logging.error(f"更新失败: {str(e)}", exc_info=True)  # 添加详细日志
        return jsonify({
            "success": False, 
            "log": f"更新过程中发生错误: {str(e)}\n{traceback.format_exc()}",
            "message": f"更新失败: {str(e)}"
        })


# 系统管理页面路由
@main.route('/system')
def system_page():
    """系统管理页面"""
    return render_template('system.html', version=get_version())


@main.route('/api/system/info')
def system_info():
    """获取系统信息"""
    try:
        # 获取系统信息
        sys_info = get_system_info()
        
        # 获取环境变量信息
        env_info = {
            'PATH': os.environ.get('PATH', '未设置'),
            'PYTHONPATH': os.environ.get('PYTHONPATH', '未设置'),
            'USER': os.environ.get('USER', '未设置'),
            'HOME': os.environ.get('HOME', '未设置'),
            'PWD': os.getcwd(),
            'is_docker': os.path.exists('/.dockerenv')
        }
        
        # 测试基本命令可用性
        cmd_results = {}
        for cmd in ['ls', 'pwd', 'cat', 'echo', 'ps', 'grep']:
            try:
                proc = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=2)
                cmd_results[cmd] = {
                    'path': proc.stdout.strip() if proc.returncode == 0 else None,
                    'available': proc.returncode == 0
                }
            except Exception as e:
                cmd_results[cmd] = {
                    'path': None,
                    'available': False,
                    'error': str(e)
                }
        
        return jsonify({
            'success': True,
            'info': sys_info,
            'env': env_info,
            'commands': cmd_results
        })
    except Exception as e:
        current_app.logger.error(f"获取系统信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@main.route('/api/system/check_update', methods=['POST'])
@admin_required
def check_system_update():
    """检查系统更新"""
    return jsonify(check_update())


@main.route('/api/update_system', methods=['POST'])
@admin_required
def update_system():
    # 复用原有 update 逻辑
    return update()


@main.route('/execute_command', methods=['POST'])
def execute_command():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "无效的请求数据"}), 400
        
        command = data.get('command', '').strip()
        timeout = int(data.get('timeout', 10))
        
        if not command:
            return jsonify({"status": "error", "message": "命令不能为空"}), 400
        
        # 生成唯一命令ID
        command_id = str(uuid.uuid4())
        
        # 设置命令过期时间（30分钟后）
        command_expire_time[command_id] = datetime.now() + timedelta(minutes=30)
        
        # 创建线程运行命令
        thread = threading.Thread(
            target=run_command,
            args=(command_id, command, timeout)
        )
        thread.daemon = True
        thread.start()
        
        current_app.logger.info(f"启动命令执行: {command} (ID: {command_id}, 超时: {timeout}秒)")
        
        return jsonify({
            "status": "started",
            "command_id": command_id,
            "message": "命令已开始执行"
        })
    
    except Exception as e:
        current_app.logger.error(f"执行命令时出错: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": f"服务器错误: {str(e)}"
        }), 500


def run_command(command_id, command, timeout):
    queue = command_outputs[command_id]
    
    try:
        # 创建子进程执行命令，不使用setsid
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        
        # 记录进程对象
        running_commands[command_id] = process
        pid = process.pid
        
        current_app.logger.info(f"命令已启动 - ID: {command_id}, PID: {pid}, 命令: {command}")
        
        # 读取输出线程
        def reader():
            try:
                for line in iter(process.stdout.readline, ''):
                    queue.put({"status": "output", "lines": [line]})
            except Exception as e:
                current_app.logger.error(f"读取命令输出时出错: {str(e)}\n{traceback.format_exc()}")
                queue.put({"status": "error", "message": f"读取输出错误: {str(e)}"})
            finally:
                if process.stdout:
                    process.stdout.close()
        
        # 启动读取线程
        read_thread = threading.Thread(target=reader)
        read_thread.daemon = True
        read_thread.start()
        
        # 等待命令完成或超时
        try:
            return_code = process.wait(timeout=timeout)
            queue.put({"status": "completed", "return_code": return_code})
            current_app.logger.info(f"命令已完成 - ID: {command_id}, 返回码: {return_code}")
        except subprocess.TimeoutExpired:
            # 超时处理
            terminate_process(process)
            queue.put({"status": "terminated", "message": f"命令执行超时({timeout}秒)"})
            current_app.logger.warning(f"命令已超时 - ID: {command_id}, 超时: {timeout}秒")
        
    except Exception as e:
        current_app.logger.error(f"运行命令时出错: {str(e)}\n{traceback.format_exc()}")
        queue.put({"status": "error", "message": f"执行命令出错: {str(e)}"})
    
    finally:
        # 确保进程已经终止
        if command_id in running_commands:
            process = running_commands[command_id]
            if process and process.poll() is None:
                try:
                    terminate_process(process)
                except Exception as e:
                    current_app.logger.error(f"终止进程时出错: {str(e)}\n{traceback.format_exc()}")


def cleanup_expired_commands():
    now = datetime.now()
    expired_ids = []
    
    for cmd_id, expire_time in list(command_expire_time.items()):
        if now > expire_time:
            expired_ids.append(cmd_id)
    
    for cmd_id in expired_ids:
        if cmd_id in running_commands:
            try:
                proc = running_commands[cmd_id]
                if proc.poll() is None:
                    terminate_process(proc)
            except Exception as e:
                current_app.logger.error(f"清理过期命令时出错: {str(e)}")
        
        # 清理资源
        if cmd_id in running_commands:
            del running_commands[cmd_id]
        if cmd_id in command_outputs:
            del command_outputs[cmd_id]
        if cmd_id in command_expire_time:
            del command_expire_time[cmd_id]
        
        current_app.logger.info(f"已清理过期命令: {cmd_id}")


# 定期运行清理任务（每分钟检查一次）
def start_cleanup_thread():
    def cleanup_loop():
        while True:
            try:
                cleanup_expired_commands()
            except Exception as e:
                current_app.logger.error(f"清理线程出错: {str(e)}")
            time.sleep(60)  # 每分钟检查一次
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    current_app.logger.info("已启动命令清理线程")


# 不在模块级别直接调用，而是将其注册为应用初始化后的回调函数
def init_cleanup_thread(app):
    """初始化清理线程，在应用上下文中调用"""
    with app.app_context():
        start_cleanup_thread()


@main.route('/stop_command/<command_id>', methods=['POST'])
def stop_command(command_id):
    try:
        if command_id in running_commands:
            process = running_commands[command_id]
            
            if process and process.poll() is None:
                terminate_process(process)
                command_outputs[command_id].put({
                    "status": "terminated",
                    "message": "命令已手动终止"
                })
                current_app.logger.info(f"命令被手动终止 - ID: {command_id}")
                return jsonify({"status": "success", "message": "命令已终止"})
            else:
                return jsonify({"status": "error", "message": "命令已经完成"})
        else:
            return jsonify({"status": "error", "message": "找不到指定的命令"})
    
    except Exception as e:
        current_app.logger.error(f"停止命令时出错: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"status": "error", "message": f"停止命令出错: {str(e)}"}), 500


@main.route('/command_output/<command_id>')
def command_output(command_id):
    """使用Server-Sent Events流式传输命令输出"""
    
    if command_id not in command_outputs:
        return jsonify({"status": "error", "message": "找不到指定的命令"}), 404
    
    def generate():
        queue = command_outputs[command_id]
        last_ping = time.time()
        
        while True:
            try:
                # 每隔10秒发送一个ping以保持连接活跃
                current_time = time.time()
                if current_time - last_ping > 10:
                    yield f"data: {json.dumps({'status': 'ping'})}\n\n"
                    last_ping = current_time
                
                # 获取队列中的数据，最多等待1秒
                try:
                    data = queue.get(timeout=1)
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # 如果是终止类消息，结束流
                    if data['status'] in ['completed', 'terminated', 'error']:
                        break
                except queue.Empty:
                    # 检查进程是否仍在运行
                    if command_id in running_commands:
                        process = running_commands[command_id]
                        if process.poll() is not None:
                            # 进程已结束，但没有收到完成消息
                            return_code = process.poll()
                            yield f"data: {json.dumps({'status': 'completed', 'return_code': return_code})}\n\n"
                            break
                    else:
                        # 没有找到进程，可能已经结束
                        yield f"data: {json.dumps({'status': 'error', 'message': '命令已结束或不存在'})}\n\n"
                        break
            
            except Exception as e:
                current_app.logger.error(f"生成命令输出时出错: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': f'输出流错误: {str(e)}'})}\n\n"
                break
    
    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 禁用Nginx缓冲
    return response