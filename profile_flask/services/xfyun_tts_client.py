"""讯飞在线语音合成（TTS）WebSocket 客户端。"""
import base64
import hashlib
import hmac
import json
import logging
import ssl
import uuid
from email.utils import formatdate
from pathlib import Path
from urllib.parse import urlencode

import websocket

from config import Config

logger = logging.getLogger(__name__)

TTS_WS_URL = "wss://tts-api.xfyun.cn/v2/tts"
TTS_AUTH_HOST = "ws-api.xfyun.cn"


class TtsClientError(Exception):
    pass


def _build_tts_auth_url(api_key: str, api_secret: str) -> str:
    date = formatdate(timeval=None, localtime=False, usegmt=True)
    signature_origin = f"host: {TTS_AUTH_HOST}\ndate: {date}\nGET /v2/tts HTTP/1.1"
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
    query = urlencode({"authorization": authorization, "date": date, "host": TTS_AUTH_HOST})
    return f"{TTS_WS_URL}?{query}"


class XfyunTtsClient:
    def __init__(self):
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        self.vcn = Config.XFYUN_TTS_VCN
        self.enabled = Config.XFYUN_TTS_ENABLED

    def _validate(self):
        if not self.enabled:
            raise TtsClientError("语音合成未启用，请在 .env 设置 XFYUN_TTS_ENABLED=1 并在控制台开通在线语音合成")
        if not self.api_secret:
            raise TtsClientError("请配置 XFYUN_API_SECRET")

    def synthesize_mp3(self, text: str) -> bytes:
        self._validate()
        text = (text or "").strip()
        if not text:
            raise TtsClientError("合成文本为空")
        if len(text.encode("utf-8")) > 7800:
            text = text[:2000]

        auth_url = _build_tts_auth_url(self.api_key, self.api_secret)
        req = {
            "common": {"app_id": self.app_id},
            "business": {
                "aue": "lame",
                "vcn": self.vcn,
                "speed": 50,
                "volume": 50,
                "pitch": 50,
                "tte": "UTF8",
            },
            "data": {
                "status": 2,
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
            },
        }
        payload = json.dumps(req)

        audio_parts: list[bytes] = []
        error_holder: list[str] = []
        done = {"flag": False}

        def on_message(ws, message):
            try:
                resp = json.loads(message)
                code = resp.get("code", 0)
                if code != 0:
                    error_holder.append(f"TTS code={code}, msg={resp.get('message')}")
                    ws.close()
                    done["flag"] = True
                    return
                audio_b64 = (resp.get("data") or {}).get("audio")
                if audio_b64:
                    audio_parts.append(base64.b64decode(audio_b64))
                if resp.get("data", {}).get("status") == 2:
                    ws.close()
                    done["flag"] = True
            except Exception as exc:
                error_holder.append(str(exc))
                done["flag"] = True

        def on_error(ws, error):
            error_holder.append(str(error))
            done["flag"] = True

        def on_open(ws):
            ws.send(payload)

        ws = websocket.WebSocketApp(
            auth_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=lambda *args: done.update({"flag": True}),
        )
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        if error_holder:
            raise TtsClientError(error_holder[0])
        result = b"".join(audio_parts)
        if not result:
            raise TtsClientError("TTS 返回空音频")
        return result


def save_audio_bytes(data: bytes, student_id: int, prefix: str = "tts") -> str:
    media_dir = Path(Config.MEDIA_DIR)
    sub = media_dir / str(student_id)
    sub.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.mp3"
    path = sub / name
    path.write_bytes(data)
    return f"/profile-api/media/{student_id}/{name}"
