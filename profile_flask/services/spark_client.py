"""讯飞星火 Lite WebSocket 客户端（判题专用）。"""
import base64
import hashlib
import hmac
import json
import logging
import ssl
from email.utils import formatdate
from urllib.parse import urlencode

import websocket

from config import Config

logger = logging.getLogger(__name__)

JUDGE_PROMPT_TEMPLATE = """你现在是Python阅卷老师，请批改学生答案。
题目：{question}
参考答案：{reference}
学生作答：{user_answer}
仅输出结果：正确 或 错误"""


class SparkClientError(Exception):
    pass


def _build_auth_url(host_url: str, api_key: str, api_secret: str) -> str:
    """生成带鉴权参数的 WebSocket URL（与 Java XfAuthUtil 一致）。"""
    from urllib.parse import urlparse

    parsed = urlparse(host_url)
    host = parsed.hostname
    path = parsed.path or "/"

    # 必须使用 GMT 时间；utcnow()+mktime() 会把 UTC 当本地时间，导致 date 偏差数小时
    date = formatdate(timeval=None, localtime=False, usegmt=True)

    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
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

    query = urlencode({"authorization": authorization, "date": date, "host": host})
    return f"{host_url}?{query}"


def _build_request(app_id: str, domain: str, user_content: str) -> dict:
    return {
        "header": {"app_id": app_id, "uid": "profile-build"},
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": Config.SPARK_TEMPERATURE,
                "max_tokens": Config.SPARK_MAX_TOKENS,
            }
        },
        "payload": {
            "message": {
                "text": [{"role": "user", "content": user_content}]
            }
        },
    }


class SparkLiteClient:
    """星火 Lite 同步对话封装。"""

    def __init__(self):
        self.app_id = Config.XFYUN_APP_ID
        self.api_key = Config.XFYUN_API_KEY
        self.api_secret = Config.XFYUN_API_SECRET
        self.host_url = Config.SPARK_HOST_URL
        self.domain = Config.SPARK_DOMAIN

    def _validate(self):
        if not self.api_secret or self.api_secret == "在此填写APISecret":
            raise SparkClientError(
                "请配置 XFYUN_API_SECRET（.env 或环境变量）"
            )

    def chat(self, user_content: str, max_tokens: int | None = None) -> str:
        """同步调用，聚合流式返回为完整文本。"""
        self._validate()
        auth_url = _build_auth_url(self.host_url, self.api_key, self.api_secret)
        req = _build_request(self.app_id, self.domain, user_content)
        if max_tokens is not None:
            req["parameter"]["chat"]["max_tokens"] = max_tokens
        payload = json.dumps(req, ensure_ascii=False)

        answer_parts: list[str] = []
        error_holder: list[str] = []
        done = {"flag": False}

        def on_message(ws, message):
            try:
                resp = json.loads(message)
                header = resp.get("header") or {}
                code = header.get("code", 0)
                if code != 0:
                    error_holder.append(
                        f"星火错误 code={code}, msg={header.get('message')}"
                    )
                    ws.close()
                    done["flag"] = True
                    return

                choices = (resp.get("payload") or {}).get("choices") or {}
                for item in choices.get("text") or []:
                    if item.get("content"):
                        answer_parts.append(item["content"])
                if choices.get("status") == 2:
                    ws.close()
                    done["flag"] = True
            except Exception as exc:
                error_holder.append(str(exc))
                done["flag"] = True

        def on_error(ws, error):
            logger.error("星火 WebSocket 错误: %s", error)
            error_holder.append(str(error))
            done["flag"] = True

        def on_open(ws):
            ws.send(payload)

        def on_close(ws, close_status_code, close_msg):
            done["flag"] = True

        ws = websocket.WebSocketApp(
            auth_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        if error_holder:
            raise SparkClientError(error_holder[0])
        result = "".join(answer_parts).strip()
        if not result:
            raise SparkClientError("星火返回内容为空")
        return result

    def judge_answer(self, question: str, reference: str, user_answer: str) -> bool:
        """
        调用星火判题，解析「正确」/「错误」。
        失败时记录日志并做关键词兜底。
        """
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            reference=reference,
            user_answer=user_answer,
        )
        try:
            raw = self.chat(prompt)
            logger.info("判题原始回复: %s", raw[:200])
            normalized = raw.replace(" ", "").strip()
            if "正确" in normalized and "错误" not in normalized:
                return True
            if "错误" in normalized:
                return False
            # 模型未严格遵循格式时兜底
            if normalized.lower() in ("correct", "true", "yes", "对"):
                return True
            return False
        except Exception as exc:
            logger.exception("星火判题失败，使用本地模糊匹配: %s", exc)
            return _fallback_judge(reference, user_answer)


def _fallback_judge(reference: str, user_answer: str) -> bool:
    """API 不可用时的简单兜底：去空白后包含关系或完全相等。"""
    ref = (reference or "").strip().lower()
    ans = (user_answer or "").strip().lower()
    if not ans:
        return False
    return ans == ref or ref in ans or ans in ref
