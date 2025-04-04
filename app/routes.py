import secrets
import string
from datetime import datetime, timedelta
from functools import wraps
from typing import Union, Any, Callable, Tuple
from urllib.parse import urlencode

import requests
from flask import Blueprint, render_template, jsonify, request, current_app, session, redirect, url_for, make_response, Response
from flask_sse import sse
from werkzeug import Response

from app import db
from app.ciphertext import CookieCipher
from app.models import PermanentToken, SignLog, Logs

main = Blueprint('main', __name__)

# 注册 sse blueprint
main.register_blueprint(sse, url_prefix='/stream')


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
                "13": "检委办", "2": "系统管理员",
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
        response = requests.post(
            f"{current_app.config['HOST']}/AttendanceCard/SaveAttCheckinout",
            headers={'User-Agent': get_mobile_user_agent(request.headers.get('User-Agent'))},
            json=data,
            allow_redirects=False
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
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


@main.route('/admin', methods=['GET'])
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
