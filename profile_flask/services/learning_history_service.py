"""学习历史 — 聚合辅导、答疑与画像构建对话记录。"""
import re

from services.dialogue_service import list_build_dialogue_sessions, list_messages
from services.mongo_client import dialogue_collection, ensure_indexes
from services.qa_service import qa_session_id
from services.tutoring_service import TUTORING_SESSION_PREFIX


def _format_entries(messages: list[dict], source: str, source_label: str) -> list[dict]:
    entries = []
    pending_question = None
    for msg in messages or []:
        role = msg.get("role")
        msg_type = msg.get("msg_type") or "text"
        if role == "user":
            pending_question = (msg.get("content") or "").strip()
            continue
        if role != "assistant":
            continue

        answer = ""
        if msg_type == "tutoring_answer":
            payload = msg.get("payload") or {}
            answer = (payload.get("text_answer") or msg.get("content") or "").strip()
        else:
            answer = (msg.get("content") or "").strip()

        if not answer and not pending_question:
            continue

        entries.append(
            {
                "id": msg.get("id"),
                "source": source,
                "source_label": source_label,
                "question": pending_question or "（无提问记录）",
                "answer": answer,
                "msg_type": msg_type,
                "created_at": msg.get("created_at"),
            }
        )
        pending_question = None
    entries.reverse()
    return entries


def _list_tutoring_session_ids(student_id: int) -> list[str]:
    """获取该学生所有智能辅导会话 ID，按最近活跃倒序。"""
    try:
        ensure_indexes()
    except Exception:
        return []
    prefix = f"{TUTORING_SESSION_PREFIX}{student_id}"
    pipeline = [
        {
            "$match": {
                "student_id": student_id,
                "session_id": {"$regex": f"^{re.escape(prefix)}"},
            }
        },
        {"$group": {"_id": "$session_id", "last_at": {"$max": "$created_at"}}},
        {"$sort": {"last_at": -1}},
    ]
    rows = list(dialogue_collection().aggregate(pipeline))
    return [row["_id"] for row in rows if row.get("_id")]


def _answer_snippet(msg: dict, limit: int = 160) -> str:
    msg_type = msg.get("msg_type") or "text"
    if msg_type == "tutoring_answer":
        payload = msg.get("payload") or {}
        text = (payload.get("text_answer") or msg.get("content") or "").strip()
    else:
        text = (msg.get("content") or "").strip()
    if not text:
        return ""
    return text[:limit] + ("…" if len(text) > limit else "")


def _summarize_tutoring_session(student_id: int, session_id: str) -> dict | None:
    """将单个辅导会话聚合为一条历史记录。"""
    messages = list_messages(student_id, session_id)
    user_msgs = [
        m for m in messages
        if m.get("role") == "user" and (m.get("content") or "").strip()
    ]
    if not user_msgs:
        return None

    first_q = user_msgs[0]["content"].strip()
    exchanges = _format_entries(messages, "tutoring", "智能辅导")
    chronological = list(reversed(exchanges))

    last_answer = ""
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        if msg.get("msg_type") in ("tutoring_welcome", "mastery_update"):
            continue
        snippet = _answer_snippet(msg)
        if snippet:
            last_answer = snippet
            break

    started_at = messages[0].get("created_at") if messages else None
    updated_at = messages[-1].get("created_at") if messages else None
    title = first_q[:80] + ("…" if len(first_q) > 80 else "")

    return {
        "id": session_id,
        "session_id": session_id,
        "source": "tutoring",
        "source_label": "智能辅导",
        "title": title,
        "question": first_q,
        "answer": last_answer or "（暂无回答摘要）",
        "question_count": len(user_msgs),
        "exchange_count": len(chronological),
        "created_at": updated_at,
        "started_at": started_at,
        "updated_at": updated_at,
        "exchanges": chronological,
    }


def _list_tutoring_sessions(student_id: int) -> list[dict]:
    sessions = []
    for sid in _list_tutoring_session_ids(student_id):
        entry = _summarize_tutoring_session(student_id, sid)
        if entry:
            sessions.append(entry)
    return sessions


def _build_entry(msg: dict) -> dict | None:
    role = msg.get("role")
    if role not in ("user", "assistant"):
        return None
    content = (msg.get("content") or "").strip()
    if not content:
        return None
    return {
        "id": msg.get("id"),
        "source": "profile_build",
        "source_label": "画像构建",
        "role": role,
        "msg_type": msg.get("msg_type") or "text",
        "content": content,
        "payload": msg.get("payload") or {},
        "session_id": msg.get("session_id"),
        "created_at": msg.get("created_at"),
    }


def get_learning_history(student_id: int) -> dict:
    qa_sid = qa_session_id(student_id)

    tutoring = _list_tutoring_sessions(student_id)
    qa_msgs = list_messages(student_id, qa_sid)
    build_sessions = list_build_dialogue_sessions(student_id)

    qa = _format_entries(qa_msgs, "qa", "日常答疑")

    build_entries = []
    for session in build_sessions:
        for msg in session.get("messages") or []:
            entry = _build_entry(msg)
            if entry:
                build_entries.append(entry)
    build_entries.reverse()

    return {
        "student_id": student_id,
        "tutoring": tutoring,
        "qa": qa,
        "profile_build": build_entries,
        "profile_build_sessions": build_sessions,
        "total": len(tutoring) + len(qa) + len(build_entries),
    }
