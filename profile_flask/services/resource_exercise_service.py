"""从一键生成的 learning_resource（EXERCISE / content_json）加载专项习题。"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import text

from models import SubjectModule, db
from services.question_quality_service import filter_valid_questions, is_valid_choice_question

logger = logging.getLogger(__name__)


def _clean_json_text(raw: str) -> str:
    t = (raw or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```json\s*", "", t, flags=re.I)
        t = re.sub(r"^```\s*", "", t)
        t = re.sub(r"```\s*$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        return t[start : end + 1]
    return t


def _normalize_options(opts) -> dict:
    if isinstance(opts, dict):
        return {str(k): str(v) for k, v in opts.items()}
    if isinstance(opts, list):
        letters = "ABCDEFGH"
        out = {}
        for i, v in enumerate(opts):
            key = letters[i] if i < len(letters) else str(i + 1)
            out[key] = str(v)
        return out
    return {}


def _normalize_answer(ans) -> str:
    if isinstance(ans, list):
        return ",".join(str(x).strip().upper() for x in ans if str(x).strip())
    return str(ans or "").strip()


def parse_exercise_content_json(json_str: str, *, resource_id: str | int) -> list[dict]:
    """将 Java ExerciseAgent 的 content_json 转为习题中心可批改题目列表。"""
    if not json_str:
        return []
    try:
        data = json.loads(_clean_json_text(json_str))
    except json.JSONDecodeError:
        logger.warning("习题 JSON 解析失败 resource=%s", resource_id)
        return []

    questions: list[dict] = []
    idx = 0
    prefix = f"res-{resource_id}"

    for item in data.get("singleChoice") or data.get("single_choice") or []:
        if not isinstance(item, dict):
            continue
        qtext = (item.get("question") or "").strip()
        if not qtext:
            continue
        idx += 1
        candidate = {
            "qid": f"{prefix}-sc-{idx}",
            "type": "choice",
            "content": qtext,
            "options": _normalize_options(item.get("options")),
            "answer": _normalize_answer(item.get("answer")),
            "analysis": (item.get("analysis") or "").strip(),
        }
        if is_valid_choice_question(candidate):
            questions.append(candidate)
        else:
            logger.warning("专项习题丢弃无效单选题: %s", qtext[:60])

    for item in data.get("multiChoice") or data.get("multi_choice") or []:
        if not isinstance(item, dict):
            continue
        qtext = (item.get("question") or "").strip()
        if not qtext:
            continue
        idx += 1
        ans = _normalize_answer(item.get("answer"))
        questions.append(
            {
                "qid": f"{prefix}-mc-{idx}",
                "type": "multi_choice",
                "content": qtext,
                "options": _normalize_options(item.get("options")),
                "answer": ans,
                "analysis": (item.get("analysis") or "").strip(),
            }
        )

    for item in data.get("shortAnswer") or data.get("short_answer") or []:
        if not isinstance(item, dict):
            continue
        qtext = (item.get("question") or "").strip()
        if not qtext:
            continue
        idx += 1
        questions.append(
            {
                "qid": f"{prefix}-sa-{idx}",
                "type": "short",
                "content": qtext,
                "options": {},
                "answer": _normalize_answer(item.get("answer")),
                "analysis": (item.get("analysis") or "").strip(),
            }
        )

    # 兼容 Flask 模块练习 JSON 格式
    for item in data.get("questions") or []:
        if not isinstance(item, dict):
            continue
        qtext = (item.get("content") or item.get("question") or "").strip()
        if not qtext:
            continue
        idx += 1
        qtype = (item.get("type") or "choice").strip().lower()
        if qtype not in ("choice", "judge", "short", "coding"):
            qtype = "choice"
        candidate = {
            "qid": str(item.get("qid") or f"{prefix}-q-{idx}"),
            "type": qtype,
            "content": qtext,
            "options": _normalize_options(item.get("options")) if qtype == "choice" else {},
            "answer": _normalize_answer(item.get("answer")),
            "analysis": (item.get("analysis") or "").strip(),
            "test_cases": item.get("test_cases"),
        }
        if qtype == "choice" and not is_valid_choice_question(candidate):
            logger.warning("专项习题丢弃无效选择题: %s", qtext[:60])
            continue
        questions.append(candidate)

    return questions


def _fetch_resource_row(resource_id: int, student_id: int) -> dict | None:
    row = db.session.execute(
        text(
            "SELECT id, resource_type, title, content_json, knowledge_point, subject "
            "FROM learning_resource "
            "WHERE id = :id AND student_id = :sid AND deleted = 0"
        ),
        {"id": resource_id, "sid": student_id},
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "resource_type": row[1],
        "title": row[2],
        "content_json": row[3],
        "knowledge_point": row[4],
        "subject": row[5],
    }


def _find_latest_exercise_resource(
    student_id: int,
    module_id: int | None = None,
    module_name: str | None = None,
) -> dict | None:
    mod_name = module_name
    if module_id and not mod_name:
        mod = SubjectModule.query.get(module_id)
        mod_name = mod.module_name if mod else None

    params: dict = {"sid": student_id}
    kp_filter = ""
    if mod_name:
        kp_filter = (
            "AND (knowledge_point = :kp OR knowledge_point LIKE :kp_like "
            "OR title LIKE :kp_like)"
        )
        params["kp"] = mod_name
        params["kp_like"] = f"%{mod_name}%"

    row = db.session.execute(
        text(
            "SELECT id, resource_type, title, content_json, knowledge_point, subject "
            "FROM learning_resource "
            "WHERE student_id = :sid AND resource_type = 'exercise' AND deleted = 0 "
            f"{kp_filter} "
            "AND content_json IS NOT NULL AND content_json != '' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        params,
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "resource_type": row[1],
        "title": row[2],
        "content_json": row[3],
        "knowledge_point": row[4],
        "subject": row[5],
    }


def load_special_exercise_questions(
    student_id: int,
    module_id: int | None = None,
    resource_id: str | int | None = None,
) -> tuple[list[dict], str, int, str, int | None]:
    """
    加载「一键生成」写入的专项习题（固定题集，非随机）。
    返回 (questions, module_name, module_id, resource_title, resource_db_id)
    """
    resource = None
    rid: int | None = None

    if resource_id is not None:
        rid_str = str(resource_id)
        if rid_str.startswith("preview-"):
            raise ValueError("请先点击「星火 AI 深度生成」，为本模块生成专项习题后再作答")
        try:
            rid = int(rid_str)
        except ValueError as exc:
            raise ValueError("无效的资源 ID") from exc
        resource = _fetch_resource_row(rid, student_id)
        if not resource:
            raise ValueError("专项习题资源不存在，请重新一键生成学习资源")
    elif module_id is not None:
        mod = SubjectModule.query.get(int(module_id))
        resource = _find_latest_exercise_resource(
            student_id, int(module_id), mod.module_name if mod else None
        )
        if resource:
            rid = int(resource["id"])
    else:
        raise ValueError("需要 module_id 或 resource_id")

    if not resource:
        raise ValueError(
            "尚未生成本模块专项习题。请在学习资源页点击「星火 AI 深度生成」，"
            "系统将根据当前薄弱点生成配套习题。"
        )

    if (resource.get("resource_type") or "").lower() != "exercise":
        raise ValueError("该资源不是习题类型")

    questions = parse_exercise_content_json(resource.get("content_json") or "", resource_id=rid or 0)
    if not questions:
        raise ValueError("习题资源内容为空，请重新一键生成学习资源")

    mod_id = int(module_id) if module_id is not None else None
    mod_name = resource.get("knowledge_point") or resource.get("title") or "模块"
    if mod_id:
        mod = SubjectModule.query.get(mod_id)
        if mod:
            mod_name = mod.module_name

    for q in questions:
        q["module_id"] = mod_id
        q["module_name"] = mod_name

    questions = filter_valid_questions(questions, module_name=mod_name, module_id=mod_id)
    if not questions:
        raise ValueError("习题资源无有效题目（选项不完整），请重新一键生成学习资源")

    return questions, mod_name, mod_id or 0, resource.get("title") or "专项习题", rid


def count_special_questions_by_module(student_id: int) -> dict[int, int]:
    """各模块最新一键生成专项习题的题量（供习题中心章节展示）。"""
    from models import SubjectModule

    mod_by_name = {m.module_name: m.module_id for m in SubjectModule.query.all()}
    try:
        rows = db.session.execute(
            text(
                "SELECT id, content_json, knowledge_point, title "
                "FROM learning_resource "
                "WHERE student_id = :sid AND resource_type = 'exercise' AND deleted = 0 "
                "AND content_json IS NOT NULL AND TRIM(content_json) != '' "
                "ORDER BY created_at DESC"
            ),
            {"sid": student_id},
        ).fetchall()
    except Exception as exc:
        logger.warning("查询专项习题题量失败: %s", exc)
        return {}

    counts: dict[int, int] = {}
    for row in rows:
        kp = (row[2] or row[3] or "").strip()
        mid = None
        for name, module_id in mod_by_name.items():
            if name in kp or kp in name:
                mid = int(module_id)
                break
        if mid is None or mid in counts:
            continue
        n = len(parse_exercise_content_json(row[1] or "", resource_id=row[0]))
        if n > 0:
            counts[mid] = n
    return counts
