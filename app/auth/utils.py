import secrets
import string

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


def get_mobile_user_agent(request_user_agent: str = "") -> str:
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