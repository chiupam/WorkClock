import re

from config import settings


def build_api_url(path: str) -> str:
    """
    构建API URL，确保正确处理带有或不带有斜杠的基础URL
    
    :param path: API路径，可以以斜杠开头也可以不以斜杠开头
    :return: 完整的API URL
    """

    host = settings.API_HOST
    if not host:
        return f"http://127.0.0.1:8001/{path.lstrip('/')}"
    
    host = re.sub(r'^(https?:\/{0,2})', '', host)

    if "zhcj" in host:
        return f"https://{host}/{path.lstrip('/')}"
    elif host.replace('.', '').replace(':', '').isdigit():
        return f"http://{host}/{path.lstrip('/')}"
    else:
        return f"http://{host}/{path.lstrip('/')}"
    