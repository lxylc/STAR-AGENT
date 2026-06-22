"""日常答疑对话 — 讯飞星火作答 + AI 识别知识点并动态更新掌握等级。"""
import json
import logging
import re

from models import KnowledgePoint, StudentProfile, SubjectModule, db
from services.dialogue_service import append_message, list_messages
from services.behavior_event_service import record_event
from services.learning_profile_sync import sync_mastery_from_student_profile
from services.profile_service import update_knowledge_point_level
from services.spark_client import SparkClientError, SparkLiteClient

logger = logging.getLogger(__name__)

QA_SESSION_PREFIX = "qa-"

ANSWER_SYSTEM_PROMPT = """你是 Python 程序设计课程的答疑助手，面向大学生。
请用清晰、友好的中文回答学生的知识点问题，适当举例。
回答控制在 300 字以内，不要输出 JSON。"""

ANALYZE_PROMPT_TEMPLATE = """分析以下 Python 学习答疑对话，判断涉及哪些知识点及掌握度变化。

可选知识点（仅从此列表选择，名称需完全一致）：
{kp_list}

对话：
学生：{question}
助手：{answer}

规则：
- 若学生表现出对该知识点的正确理解或学会了新内容，delta 为 +1
- 若学生表现出明显误解或答错核心概念，delta 为 -1
- 若对话仅泛泛提及、无法判断掌握变化，delta 为 0
- 每条 delta 取值只能是 -1、0、1
- 最多返回 3 个相关知识点

仅输出 JSON，格式：
{{"updates":[{{"kp_name":"知识点名","delta":0,"reason":"简短原因"}}]}}"""


def qa_session_id(student_id: int) -> str:
    return f"{QA_SESSION_PREFIX}{student_id}"


def _load_kp_catalog() -> list[dict]:
    rows = (
        db.session.query(KnowledgePoint, SubjectModule)
        .join(SubjectModule, KnowledgePoint.module_id == SubjectModule.module_id)
        .order_by(SubjectModule.module_id, KnowledgePoint.kp_id)
        .all()
    )
    return [
        {
            "kp_id": kp.kp_id,
            "kp_name": kp.kp_name,
            "module_id": mod.module_id,
            "module_name": mod.module_name,
        }
        for kp, mod in rows
    ]


def _kp_name_map() -> dict[str, dict]:
    return {item["kp_name"]: item for item in _load_kp_catalog()}


def _parse_analyze_json(raw: str) -> list[dict]:
    text = (raw or "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return []
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    updates = data.get("updates") or []
    if not isinstance(updates, list):
        return []
    return [u for u in updates if isinstance(u, dict) and u.get("kp_name")]


def _apply_mastery_updates(student_id: int, updates: list[dict]) -> list[dict]:
    """根据 AI 分析结果调整知识点掌握等级（1-4）。"""
    kp_map = _kp_name_map()
    applied = []

    for item in updates:
        name = (item.get("kp_name") or "").strip()
        if name not in kp_map:
            continue
        try:
            delta = int(item.get("delta", 0))
        except (TypeError, ValueError):
            delta = 0
        if delta not in (-1, 0, 1):
            delta = 0
        if delta == 0:
            continue

        kp = kp_map[name]
        row = StudentProfile.query.filter_by(
            student_id=student_id, kp_id=kp["kp_id"]
        ).first()
        current = row.master_level if row else 2
        new_level = max(1, min(4, current + delta))

        if row and row.master_level == new_level:
            continue

        update_knowledge_point_level(
            student_id,
            kp["kp_id"],
            new_level,
            reason=item.get("reason") or "日常答疑动态更新",
        )
        applied.append(
            {
                "kp_id": kp["kp_id"],
                "kp_name": name,
                "module_name": kp["module_name"],
                "old_level": current,
                "new_level": new_level,
                "reason": item.get("reason") or "",
            }
        )
        try:
            from services.profile_snapshot_service import log_profile_change
            log_profile_change(
                student_id,
                f"kp:{name}",
                str(current),
                str(new_level),
                "qa",
            )
        except Exception:
            pass

    if applied:
        sync_mastery_from_student_profile(student_id)
    return applied


def init_qa_dialogue(student_id: int) -> dict:
    sid = qa_session_id(student_id)
    existing = list_messages(student_id, sid)
    if not existing:
        append_message(
            student_id,
            "assistant",
            "text",
            "你好！这里是日常答疑区，你可以自由提问 Python 相关知识点。"
            "我会尽力解答，并根据对话内容动态更新你的知识点掌握画像。",
            session_id=sid,
        )
    return {
        "student_id": student_id,
        "session_id": sid,
        "messages": list_messages(student_id, sid),
    }


def ask_question(student_id: int, question: str) -> dict:
    q = (question or "").strip()
    if not q:
        raise ValueError("请输入问题")
    if len(q) > 2000:
        raise ValueError("问题过长，请精简后重试")

    sid = qa_session_id(student_id)
    append_message(student_id, "user", "text", q, session_id=sid)
    record_event(student_id, "qa_ask", "qa", {"question_len": len(q)})

    catalog = _load_kp_catalog()
    kp_names = [c["kp_name"] for c in catalog]
    client = SparkLiteClient()

    try:
        if "```" in q or "解释以下 Python 代码" in q:
            answer_prompt = (
                "你是 Python 程序设计课程的答疑助手，面向大学生。\n"
                "请解释学生给出的代码，说明含义与运行结果；需要示例时用 markdown 代码块（```python）。\n"
                "控制在 500 字以内，不要输出 JSON。\n\n"
                f"{q}"
            )
            max_tokens = 1536
        else:
            answer_prompt = f"{ANSWER_SYSTEM_PROMPT}\n\n学生问题：{q}"
            max_tokens = 1024
        answer = client.chat(answer_prompt, max_tokens=max_tokens)
    except SparkClientError as exc:
        logger.exception("星火答疑失败")
        answer = (
            "抱歉，AI 服务暂时不可用，请稍后再试。"
            f"（{exc}）"
        )

    append_message(student_id, "assistant", "text", answer, session_id=sid)

    mastery_updates = []
    if kp_names and not answer.startswith("抱歉，AI 服务暂时不可用"):
        try:
            analyze_prompt = ANALYZE_PROMPT_TEMPLATE.format(
                kp_list="、".join(kp_names),
                question=q,
                answer=answer,
            )
            raw = client.chat(analyze_prompt)
            parsed = _parse_analyze_json(raw)
            mastery_updates = _apply_mastery_updates(student_id, parsed)
        except Exception:
            logger.exception("知识点掌握度分析失败，跳过动态更新")

    if mastery_updates:
        summary = "；".join(
            f"「{u['kp_name']}」L{u['old_level']}→L{u['new_level']}"
            for u in mastery_updates
        )
        append_message(
            student_id,
            "system",
            "mastery_update",
            f"已根据本次对话更新掌握度：{summary}",
            payload={"updates": mastery_updates},
            session_id=sid,
        )

    return {
        "student_id": student_id,
        "session_id": sid,
        "answer": answer,
        "mastery_updates": mastery_updates,
        "messages": list_messages(student_id, sid),
    }


def clear_qa_history(student_id: int) -> None:
    """重新生成画像时清空答疑记录。"""
    from services.mongo_client import dialogue_collection

    sid = qa_session_id(student_id)
    dialogue_collection().delete_many(
        {"student_id": student_id, "session_id": sid}
    )
    logger.info("已清空答疑记录 student=%s", student_id)


def get_qa_history(student_id: int) -> dict:
    sid = qa_session_id(student_id)
    return {
        "student_id": student_id,
        "session_id": sid,
        "messages": list_messages(student_id, sid),
    }
