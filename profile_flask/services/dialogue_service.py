"""画像构建对话记录（MongoDB）。"""
import logging
from datetime import datetime
from uuid import uuid4

from config import Config
from services.mongo_client import dialogue_collection, ensure_indexes

logger = logging.getLogger(__name__)


def _now():
    return datetime.utcnow()


def _next_round(student_id: int, session_id: str) -> int:
    last = (
        dialogue_collection()
        .find({"student_id": student_id, "session_id": session_id})
        .sort("round_no", -1)
        .limit(1)
    )
    for doc in last:
        return int(doc.get("round_no", 0)) + 1
    return 1


class DialogueStoreError(Exception):
    """MongoDB 对话存储不可用。"""


def append_message(
    student_id: int,
    role: str,
    msg_type: str,
    content: str,
    payload: dict | None = None,
    session_id: str | None = None,
) -> dict:
    """写入一条对话消息。"""
    try:
        ensure_indexes()
    except Exception as exc:
        raise DialogueStoreError(
            "MongoDB 未连接，请先启动 MongoDB（默认 mongodb://127.0.0.1:27017）"
        ) from exc
    sid = session_id or str(student_id)
    doc = {
        "student_id": student_id,
        "session_id": sid,
        "role": role,
        "msg_type": msg_type,
        "content": content,
        "payload": payload or {},
        "round_no": _next_round(student_id, sid),
        "created_at": _now(),
    }
    dialogue_collection().insert_one(doc)
    doc["_id"] = str(doc["_id"])
    return doc


def _doc_to_message(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "role": doc.get("role"),
        "msg_type": doc.get("msg_type", "text"),
        "content": doc.get("content", ""),
        "payload": doc.get("payload") or {},
        "round_no": doc.get("round_no"),
        "session_id": doc.get("session_id"),
        "created_at": doc.get("created_at").isoformat()
        if doc.get("created_at")
        else None,
    }


def list_messages(student_id: int, session_id: str | None = None) -> list[dict]:
    """按时间顺序返回对话列表（供前端渲染）。"""
    ensure_indexes()
    sid = session_id or str(student_id)
    cursor = (
        dialogue_collection()
        .find({"student_id": student_id, "session_id": sid})
        .sort("created_at", 1)
    )
    return [_doc_to_message(doc) for doc in cursor]


def list_build_dialogue_sessions(student_id: int) -> list[dict]:
    """画像构建相关的全部会话（session_id 为 student_id 或 student_id-xxx）。"""
    ensure_indexes()
    sid = str(student_id)
    cursor = (
        dialogue_collection()
        .find(
            {
                "student_id": student_id,
                "$or": [
                    {"session_id": sid},
                    {"session_id": {"$regex": f"^{sid}-"}},
                ],
                "role": {"$in": ["user", "assistant"]},
            }
        )
        .sort("created_at", 1)
    )
    grouped: dict[str, list[dict]] = {}
    for doc in cursor:
        session_id = doc.get("session_id") or sid
        grouped.setdefault(session_id, []).append(_doc_to_message(doc))

    sessions = []
    for session_id, messages in grouped.items():
        sessions.append(
            {
                "session_id": session_id,
                "started_at": messages[0]["created_at"] if messages else None,
                "ended_at": messages[-1]["created_at"] if messages else None,
                "message_count": len(messages),
                "messages": messages,
            }
        )
    sessions.sort(key=lambda item: item.get("started_at") or "", reverse=True)
    return sessions


def update_message_payload(student_id: int, session_id: str, message_id: str, payload_patch: dict) -> bool:
    """合并更新某条消息的 payload（用于辅导多媒体持久化）。"""
    from bson import ObjectId

    try:
        ensure_indexes()
        oid = ObjectId(message_id)
    except Exception:
        return False
    doc = dialogue_collection().find_one(
        {"_id": oid, "student_id": student_id, "session_id": session_id}
    )
    if not doc:
        return False
    payload = dict(doc.get("payload") or {})
    payload.update(payload_patch)
    payload["media_persisted"] = True
    dialogue_collection().update_one(
        {"_id": oid},
        {"$set": {"payload": payload}},
    )
    return True


def reset_session(student_id: int) -> str:
    """开启新会话：返回新 session_id（旧记录保留）。"""
    session_id = f"{student_id}-{uuid4().hex[:8]}"
    append_message(
        student_id,
        "system",
        "text",
        "会话已重置，请完成模块自评与校验答题以构建学习画像。",
        session_id=session_id,
    )
    return session_id


def init_build_dialogue(
    student_id: int,
    modules: list,
    level_options: list,
    basic_defaults: dict | None = None,
) -> dict:
    """
    初始化画像构建对话：欢迎语 → 基本情况表单 →（提交后）模块自评。
    """
    session_id = f"{student_id}-{uuid4().hex[:8]}"
    defaults = basic_defaults or {}
    append_message(
        student_id,
        "assistant",
        "text",
        "你好！欢迎使用对话式学习画像构建。请先填写你的 **基本情况**，再完成模块自评与分层校验答题，"
        "系统将生成完整学习画像并同步至「我的画像」。",
        session_id=session_id,
    )
    append_message(
        student_id,
        "assistant",
        "basic_info",
        "请填写你的基本学习情况",
        payload={
            "submitted": False,
            "form": {
                "grade": defaults.get("grade", ""),
                "major": defaults.get("major", ""),
                "daily_study_hours": defaults.get("daily_study_hours", 2),
                "learn_preference": defaults.get("learn_preference", "mixed"),
                "learn_goal": defaults.get("learn_goal", ""),
            },
        },
        session_id=session_id,
    )
    return {
        "student_id": student_id,
        "session_id": session_id,
        "messages": list_messages(student_id, session_id),
        "phase": "basic",
    }


def append_module_assess_card(
    student_id: int, session_id: str, modules: list, level_options: list
) -> None:
    append_message(
        student_id,
        "assistant",
        "module_assess",
        "请选择各模块掌握程度（A完全不会 / B有点了解 / C基本掌握 / D非常熟练）",
        payload={
            "modules": modules,
            "level_options": level_options,
            "submitted": False,
        },
        session_id=session_id,
    )


def record_basic_info_submit(
    student_id: int, session_id: str, form: dict
) -> None:
    summary = (
        f"年级 {form.get('grade') or '未填'}，专业 {form.get('major') or '未填'}，"
        f"每日 {form.get('daily_study_hours', 2)} 小时，"
        f"偏好 {form.get('learn_preference', 'mixed')}，"
        f"目标 {form.get('learn_goal') or '未填'}"
    )
    append_message(
        student_id,
        "user",
        "text",
        f"我的基本情况：{summary}",
        session_id=session_id,
    )
    col = dialogue_collection()
    last = col.find_one(
        {"student_id": student_id, "session_id": session_id, "msg_type": "basic_info"},
        sort=[("created_at", -1)],
    )
    if last:
        payload = last.get("payload") or {}
        payload["submitted"] = True
        payload["form"] = form
        col.update_one({"_id": last["_id"]}, {"$set": {"payload": payload}})


def record_assess_submit(
    student_id: int,
    session_id: str,
    assessments: list[dict],
    module_labels: list[str],
) -> None:
    """记录用户完成模块自评。"""
    summary = "；".join(module_labels)
    append_message(
        student_id,
        "user",
        "text",
        f"我已完成模块自评：{summary}",
        session_id=session_id,
    )
    # 将自评卡片标记为已提交（更新最后一条 module_assess）
    col = dialogue_collection()
    last = col.find_one(
        {"student_id": student_id, "session_id": session_id, "msg_type": "module_assess"},
        sort=[("created_at", -1)],
    )
    if last:
        payload = last.get("payload") or {}
        payload["submitted"] = True
        payload["assessments"] = assessments
        col.update_one({"_id": last["_id"]}, {"$set": {"payload": payload}})


def record_quiz_batch(
    student_id: int,
    session_id: str,
    exercises: list[dict],
) -> None:
    append_message(
        student_id,
        "assistant",
        "text",
        f"已根据你的自评抽取 {len(exercises)} 道分层校验选择题，请在下方逐题作答后提交。",
        session_id=session_id,
    )
    append_message(
        student_id,
        "assistant",
        "exercise_quiz",
        "分层校验选择题",
        payload={"exercises": exercises, "submitted": False},
        session_id=session_id,
    )


def record_quiz_submit(student_id: int, session_id: str, summary: str) -> None:
    append_message(
        student_id,
        "user",
        "text",
        f"我已完成校验答题。{summary}",
        session_id=session_id,
    )
    col = dialogue_collection()
    last = col.find_one(
        {"student_id": student_id, "session_id": session_id, "msg_type": "exercise_quiz"},
        sort=[("created_at", -1)],
    )
    if last:
        payload = last.get("payload") or {}
        payload["submitted"] = True
        col.update_one({"_id": last["_id"]}, {"$set": {"payload": payload}})


def record_build_result(
    student_id: int,
    session_id: str,
    module_results: list[dict],
    message: str,
) -> None:
    append_message(
        student_id,
        "assistant",
        "result",
        message,
        payload={"module_results": module_results},
        session_id=session_id,
    )


def mark_choice_card_submitted(
    student_id: int, session_id: str, selected: str
) -> None:
    """将最近一条未提交的选择卡片标记为已作答。"""
    col = dialogue_collection()
    last = col.find_one(
        {
            "student_id": student_id,
            "session_id": session_id,
            "msg_type": "choice_card",
            "payload.submitted": False,
        },
        sort=[("created_at", -1)],
    )
    if last:
        payload = last.get("payload") or {}
        payload["submitted"] = True
        payload["selected"] = selected
        col.update_one({"_id": last["_id"]}, {"$set": {"payload": payload}})
