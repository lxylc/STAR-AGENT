"""讯飞星火文生图（TTI）客户端。"""
import base64
import hashlib
import hmac
import logging
import uuid
from email.utils import formatdate
from pathlib import Path
from urllib.parse import urlencode

import requests

from config import Config

logger = logging.getLogger(__name__)

TTI_HOST = "spark-api.cn-huabei-1.xf-yun.com"
TTI_PATH = "/v2.1/tti"
TTI_URL = f"https://{TTI_HOST}{TTI_PATH}"


class TtiClientError(Exception):
    pass


def _build_tti_auth_url(api_key: str, api_secret: str) -> str:
    """讯飞 TTI 鉴权参数需附在 URL 查询串上（与官方 Python demo 一致）。"""
    date = formatdate(timeval=None, localtime=False, usegmt=True)
    signature_origin = f"host: {TTI_HOST}\ndate: {date}\nPOST {TTI_PATH} HTTP/1.1"
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
    query = urlencode({"authorization": authorization, "date": date, "host": TTI_HOST})
    return f"{TTI_URL}?{query}"


class XfyunTtiClient:
    def __init__(self):
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        self.enabled = Config.XFYUN_TTI_ENABLED

    def _validate(self):
        if not self.enabled:
            raise TtiClientError("文生图未启用，请在 .env 设置 XFYUN_TTI_ENABLED=1 并在控制台开通图片生成")
        if not self.api_secret:
            raise TtiClientError("请配置 XFYUN_API_SECRET")

    def generate_image(self, prompt: str, width: int = 512, height: int = 512) -> bytes:
        self._validate()
        prompt = (prompt or "").strip()[:900]
        if not prompt:
            raise TtiClientError("图片提示词为空")

        body = {
            "header": {"app_id": self.app_id},
            "parameter": {
                "chat": {
                    "domain": "general",
                    "width": width,
                    "height": height,
                }
            },
            "payload": {
                "message": {
                    "text": [{"role": "user", "content": prompt}]
                }
            },
        }

        url = _build_tti_auth_url(self.api_key, self.api_secret)
        resp = requests.post(
            url,
            json=body,
            headers={"content-type": "application/json"},
            timeout=90,
        )
        if resp.status_code != 200:
            raise TtiClientError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        header = data.get("header") or {}
        if header.get("code", 0) != 0:
            raise TtiClientError(f"TTI code={header.get('code')}, msg={header.get('message')}")

        texts = ((data.get("payload") or {}).get("choices") or {}).get("text") or []
        if not texts:
            raise TtiClientError("TTI 返回空图片")
        b64 = texts[0].get("content")
        if not b64:
            raise TtiClientError("TTI 图片 base64 为空")
        return base64.b64decode(b64)


def save_image_bytes(data: bytes, student_id: int, prefix: str = "img") -> str:
    """保存图片并返回可访问 URL 路径（相对 profile-api）。"""
    media_dir = Path(Config.MEDIA_DIR)
    sub = media_dir / str(student_id)
    sub.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.png"
    path = sub / name
    path.write_bytes(data)
    return f"/profile-api/media/{student_id}/{name}"
