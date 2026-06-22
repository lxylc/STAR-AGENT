"""Flask 侧调用 Java 学习路径同步（画像掌握度更新后）。"""
import logging
import requests

from config import Config

logger = logging.getLogger(__name__)


def sync_path_from_profile(student_id: int, subject: str = "Python程序设计") -> dict:
    """
    通知 Java 根据 learning_profile 弱项微调当前路径优先级并刷新推送。
    失败时仅记录日志，不阻断主流程。
    """
    url = f"{Config.JAVA_API_BASE}/api/path/sync-from-profile"
    try:
        resp = requests.post(
            url,
            json={"studentId": student_id, "subject": subject},
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 401:
            logger.info("路径同步需登录态，跳过服务端调用 student=%s", student_id)
            return {"synced": False, "reason": "auth_required"}
        data = resp.json()
        if data.get("code") == 200:
            return {"synced": True, "detail": data.get("data")}
        logger.warning("路径同步失败: %s", data.get("message"))
        return {"synced": False, "reason": data.get("message")}
    except Exception as exc:
        logger.warning("路径同步请求异常: %s", exc)
        return {"synced": False, "reason": str(exc)}
