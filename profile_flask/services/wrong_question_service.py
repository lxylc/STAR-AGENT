"""错题库 — 汇总画像测评与模块练习中的错题。"""
import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from models import Exercise, KnowledgePoint, SubjectModule, db
from services.mongo_client import ensure_indexes, get_db
from services.question_quality_service import (
    is_placeholder_options,
    lookup_bank_entry,
    normalize_qtext,
)

logger = logging.getLogger(__name__)

WRONG_COL = "wrong_question_record"


def _normalize_qtext(text: str) -> str:
    return normalize_qtext(text)


def _wrong_collection():
    ensure_indexes()
    col = get_db()[WRONG_COL]
    col.create_index([("student_id", 1), ("created_at", -1)])
    col.create_index([("student_id", 1), "dedupe_key"])
    return col


def _dedupe_key(student_id: int, module_id: int, content: str, ex_id: int | None = None) -> str:
    if ex_id:
        return f"{student_id}:ex:{int(ex_id)}"
    norm = _normalize_qtext(content)
    return f"{student_id}:m{int(module_id)}:{norm[:160]}"


def _find_duplicate_wrong(
    col,
    student_id: int,
    module_id: int,
    content: str,
    ex_id: int | None = None,
) -> dict | None:
    key = _dedupe_key(student_id, module_id, content, ex_id)
    doc = col.find_one({"student_id": student_id, "dedupe_key": key})
    if doc:
        return doc
    if ex_id:
        doc = col.find_one({"student_id": student_id, "ex_id": int(ex_id)})
        if doc:
            return doc
    norm = _normalize_qtext(content)
    if not norm:
        return None
    for doc in col.find({"student_id": student_id, "module_id": int(module_id)}):
        doc_norm = _normalize_qtext(doc.get("content"))
        if doc_norm == norm or (norm in doc_norm or doc_norm in norm):
            return doc
    return None


def _dedupe_merged_items(items: list[dict]) -> list[dict]:
    """合并列表按题目去重，保留最近一次错误记录。"""
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        mid = int(item.get("module_id") or 0)
        ex_id = item.get("ex_id")
        if ex_id:
            key = f"ex:{ex_id}"
        else:
            key = f"m{mid}:{_normalize_qtext(item.get('content'))}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def persist_practice_wrong_questions(
    student_id: int,
    module_id: int,
    module_name: str,
    results: list[dict],
) -> int:
    """模块练习提交后，将错题写入 MongoDB（同题 upsert，不重复入库）。"""
    wrong_items = [r for r in (results or []) if not r.get("is_correct")]
    if not wrong_items:
        return 0

    col = _wrong_collection()
    now = datetime.now(timezone.utc).isoformat()
    affected = 0
    for item in wrong_items:
        content = item.get("content") or ""
        ex_id = None
        qid = item.get("qid")
        if qid is not None and str(qid).isdigit():
            ex_id = int(qid)

        existing = _find_duplicate_wrong(col, student_id, module_id, content, ex_id)
        payload = {
            "module_id": module_id,
            "module_name": module_name or "",
            "source": item.get("source") or "module_practice",
            "qtype": item.get("type") or "choice",
            "content": content,
            "options": item.get("options") or {},
            "user_answer": item.get("user_answer") or "",
            "correct_answer": item.get("correct_answer") or "",
            "analysis": item.get("analysis") or "",
            "judge_reason": item.get("judge_reason") or "",
            "reviewed": False,
            "last_wrong_at": now,
        }
        if ex_id:
            payload["ex_id"] = ex_id

        if existing:
            col.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": payload,
                    "$inc": {"wrong_count": 1},
                },
            )
        else:
            doc = {
                "student_id": student_id,
                "dedupe_key": _dedupe_key(student_id, module_id, content, ex_id),
                "wrong_count": 1,
                "created_at": now,
                **payload,
            }
            col.insert_one(doc)
        affected += 1
    return affected


def _list_from_answer_record(student_id: int, limit: int) -> list[dict]:
    rows = db.session.execute(
        text(
            """
            SELECT ar.record_id, ar.user_answer, ar.judge_result, ar.created_at,
                   e.ex_id, e.content, e.answer, e.question_type, e.options,
                   kp.kp_name, sm.module_id, sm.module_name
            FROM answer_record ar
            JOIN exercise e ON e.ex_id = ar.ex_id
            JOIN knowledge_points kp ON kp.kp_id = e.kp_id
            JOIN subject_module sm ON sm.module_id = kp.module_id
            WHERE ar.student_id = :sid AND ar.judge_result = 0
            ORDER BY ar.created_at DESC
            LIMIT :lim
            """
        ),
        {"sid": student_id, "lim": limit},
    ).fetchall()

    items = []
    for row in rows:
        created = row[3]
        options = row[8]
        if isinstance(options, str):
            try:
                import json
                options = json.loads(options)
            except Exception:
                options = {}
        items.append(
            {
                "id": f"quiz-{row[0]}",
                "ex_id": int(row[4]),
                "source": "profile_quiz",
                "source_label": "画像测评",
                "module_id": int(row[10]),
                "module_name": row[11] or "",
                "kp_name": row[9] or "",
                "qtype": row[7] or "choice",
                "content": row[5] or "",
                "options": options if isinstance(options, dict) else {},
                "user_answer": row[1] or "",
                "correct_answer": row[6] or "",
                "analysis": "",
                "judge_reason": "",
                "reviewed": False,
                "created_at": created.isoformat() if created else None,
            }
        )
    return items


def _list_from_mongo(student_id: int, limit: int) -> list[dict]:
    try:
        col = _wrong_collection()
        cursor = (
            col.find({"student_id": student_id})
            .sort("created_at", -1)
            .limit(limit)
        )
    except Exception:
        logger.exception("错题 Mongo 查询失败")
        return []

    items = []
    for doc in cursor:
        items.append(
            {
                "id": str(doc.get("_id")),
                "source": doc.get("source") or "module_practice",
                "source_label": "模块练习",
                "module_id": doc.get("module_id"),
                "module_name": doc.get("module_name") or "",
                "kp_name": "",
                "qtype": doc.get("qtype") or "choice",
                "content": doc.get("content") or "",
                "options": doc.get("options") or {},
                "user_answer": doc.get("user_answer") or "",
                "correct_answer": doc.get("correct_answer") or "",
                "analysis": doc.get("analysis") or "",
                "judge_reason": doc.get("judge_reason") or "",
                "reviewed": bool(doc.get("reviewed")),
                "created_at": doc.get("created_at"),
            }
        )
    return items


def _lookup_exercise_by_id(ex_id: int | None) -> dict | None:
    if not ex_id:
        return None
    ex = Exercise.query.get(int(ex_id))
    if not ex:
        return None
    opts = ex.options_dict()
    return {
        "content": ex.content or "",
        "options": opts if isinstance(opts, dict) else {},
        "answer": str(ex.answer or "").strip(),
    }


def _persist_enriched_fields(item: dict, patch: dict) -> None:
    """将补全后的选项写回 Mongo，避免下次仍显示占位选项。"""
    item_id = str(item.get("id") or "")
    if not item_id or item_id.startswith("quiz-"):
        return
    try:
        from bson import ObjectId

        col = _wrong_collection()
        col.update_one(
            {"_id": ObjectId(item_id), "student_id": item.get("student_id")},
            {
                "$set": {
                    "options": patch.get("options") or {},
                    "correct_answer": patch.get("answer") or item.get("correct_answer"),
                    "content": patch.get("content") or item.get("content"),
                }
            },
        )
    except Exception:
        logger.debug("错题选项回写 Mongo 失败: %s", item_id)


def _enrich_options(item: dict, student_id: int | None = None) -> dict:
    """补全选择题选项，优先从题库/Exercise 恢复真实选项。"""
    qtype = item.get("qtype") or item.get("type") or "choice"
    if qtype == "judge":
        item["qtype"] = "judge"
        return item
    if qtype != "choice":
        return item

    opts = item.get("options")
    if isinstance(opts, dict) and opts and not is_placeholder_options(opts):
        return item

    patch = None
    if item.get("ex_id"):
        patch = _lookup_exercise_by_id(item.get("ex_id"))
    if not patch or is_placeholder_options(patch.get("options")):
        bank_patch = lookup_bank_entry(item.get("module_name") or "", item.get("content") or "")
        if bank_patch:
            patch = bank_patch
    if not patch and item.get("content"):
        content = str(item.get("content") or "")
        row = Exercise.query.filter(Exercise.content == content).first()
        if not row and len(content) >= 8:
            row = Exercise.query.filter(Exercise.content.like(f"%{content[:24]}%")).first()
        if row:
            patch = {
                "content": row.content,
                "options": row.options_dict() or {},
                "answer": str(row.answer or "").strip(),
            }

    if patch and patch.get("options") and not is_placeholder_options(patch.get("options")):
        item["options"] = patch["options"]
        if patch.get("answer"):
            item["correct_answer"] = patch["answer"]
        if patch.get("content"):
            item["content"] = patch["content"]
        if student_id is not None:
            item["student_id"] = student_id
            _persist_enriched_fields(item, patch)
        return item

    item["options"] = {"A": "选项 A", "B": "选项 B", "C": "选项 C", "D": "选项 D"}
    return item


def list_wrong_questions(student_id: int, limit: int = 100) -> dict:
    """合并画像测评错题与模块练习错题，按时间倒序。"""
    quiz_wrong = _list_from_answer_record(student_id, limit)
    practice_wrong = _list_from_mongo(student_id, limit)
    merged = quiz_wrong + practice_wrong
    merged = [_enrich_options(m, student_id) for m in merged]
    merged.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    merged = _dedupe_merged_items(merged)
    merged = merged[:limit]

    module_ids = {int(m["module_id"]) for m in merged if m.get("module_id")}
    module_stats = {}
    for mid in module_ids:
        module_stats[mid] = sum(
            1 for m in merged if int(m.get("module_id") or 0) == mid
        )

    return {
        "student_id": student_id,
        "total": len(merged),
        "items": merged,
        "module_stats": [
            {
                "module_id": mid,
                "module_name": next(
                    (m["module_name"] for m in merged if int(m.get("module_id") or 0) == mid),
                    "",
                ),
                "wrong_count": cnt,
            }
            for mid, cnt in sorted(module_stats.items(), key=lambda x: -x[1])
        ],
    }


def _wrong_item_to_question(item: dict) -> dict:
    qtype = item.get("qtype") or "choice"
    if qtype not in ("choice", "judge", "short", "coding"):
        qtype = "choice"
    return {
        "qid": str(item.get("id") or uuid4()),
        "wrong_item_id": str(item.get("id") or ""),
        "type": qtype,
        "content": item.get("content") or "",
        "options": item.get("options") or {},
        "answer": item.get("correct_answer") or "",
        "analysis": item.get("analysis") or "",
        "module_id": item.get("module_id"),
        "module_name": item.get("module_name") or "",
    }


def build_wrong_redo_questions(
    student_id: int,
    item_ids: list[str] | None = None,
    module_id: int | None = None,
) -> tuple[list[dict], int, str]:
    """将错题转为可重做题目列表。返回 (questions, module_id, module_name)。"""
    data = list_wrong_questions(student_id, limit=200)
    items = data.get("items") or []
    if item_ids:
        id_set = set(item_ids)
        items = [i for i in items if str(i.get("id")) in id_set]
    if module_id is not None:
        mid = int(module_id)
        items = [i for i in items if int(i.get("module_id") or 0) == mid]
    if not items:
        raise ValueError("未找到可重做的错题")

    questions = [_wrong_item_to_question(i) for i in items]
    module_id = int(items[0].get("module_id") or 0)
    module_name = items[0].get("module_name") or ""
    return questions, module_id, module_name


def remove_mongo_wrong(student_id: int, item_id: str) -> bool:
    if not item_id or item_id.startswith("quiz-"):
        return False
    try:
        from bson import ObjectId

        col = _wrong_collection()
        result = col.delete_one({"_id": ObjectId(item_id), "student_id": student_id})
        return result.deleted_count > 0
    except Exception:
        logger.exception("删除 Mongo 错题失败")
        return False


def resolve_quiz_wrong(student_id: int, record_id: int, is_correct: bool) -> bool:
    """画像测评错题重做正确后，更新 answer_record。"""
    if not is_correct:
        return False
    try:
        db.session.execute(
            text(
                "UPDATE answer_record SET judge_result = 1 "
                "WHERE record_id = :rid AND student_id = :sid"
            ),
            {"rid": record_id, "sid": student_id},
        )
        db.session.commit()
        return True
    except Exception:
        logger.exception("更新测评错题记录失败")
        db.session.rollback()
        return False


def apply_wrong_redo_results(student_id: int, results: list[dict]) -> int:
    """错题重做提交后：做对的移出错题本；再次做错则更新原记录不新增。"""
    removed = 0
    now = datetime.now(timezone.utc).isoformat()
    col = _wrong_collection()

    for r in results:
        wid = str(r.get("wrong_item_id") or "").strip()
        if not wid:
            continue

        if r.get("is_correct"):
            if wid.startswith("quiz-"):
                try:
                    record_id = int(wid.replace("quiz-", ""))
                    if resolve_quiz_wrong(student_id, record_id, True):
                        removed += 1
                except ValueError:
                    pass
            elif remove_mongo_wrong(student_id, wid):
                removed += 1
            continue

        if wid.startswith("quiz-"):
            continue

        try:
            from bson import ObjectId

            col.update_one(
                {"_id": ObjectId(wid), "student_id": student_id},
                {
                    "$set": {
                        "user_answer": r.get("user_answer") or "",
                        "judge_reason": r.get("judge_reason") or "",
                        "reviewed": False,
                        "last_wrong_at": now,
                    },
                    "$inc": {"wrong_count": 1},
                },
            )
        except Exception:
            logger.debug("错题重做失败记录更新跳过: %s", wid)

    return removed


def mark_wrong_reviewed(student_id: int, item_id: str) -> bool:
    """标记 Mongo 错题已复习（画像测评错题为只读记录）。"""
    if not item_id or item_id.startswith("quiz-"):
        return True
    try:
        from bson import ObjectId

        col = _wrong_collection()
        result = col.update_one(
            {"_id": ObjectId(item_id), "student_id": student_id},
            {"$set": {"reviewed": True}},
        )
        return result.modified_count > 0
    except Exception:
        logger.exception("标记错题复习失败")
        return False
