"""讯飞 HTTP API 鉴权（文生图等 POST 接口）。"""
import base64
import hashlib
import hmac
from email.utils import formatdate
from urllib.parse import urlparse


def build_http_auth_headers(
    url: str,
    api_key: str,
    api_secret: str,
    method: str = "POST",
) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname
    path = parsed.path or "/"
    date = formatdate(timeval=None, localtime=False, usegmt=True)

    signature_origin = f"host: {host}\ndate: {date}\n{method.upper()} {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

    return {
        "Host": host,
        "Date": date,
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8",
    }
