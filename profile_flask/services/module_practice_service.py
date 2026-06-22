"""轻量化模块练习：题库智能体出题 → 自由作答 → 自动批改 → 画像回写。"""
from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime, timedelta
from uuid import uuid4

from config import Config
from models import Exercise, KnowledgePoint, StudentProfile, SubjectModule, db
from services.learning_profile_sync import get_mastery_view, sync_mastery_from_student_profile
from services.mongo_client import practice_session_collection
from services.profile_service import sync_module_level_to_knowledge_points
from services.scoring import clamp_score, mastery_label_from_score
from services.practice_judge_service import (
    _format_option_label,
    _match_option_key,
    build_objective_judge_fields,
    build_outcome_judge_fields,
    judge_coding_answer,
    judge_multi_choice,
    judge_short_answer,
)
from services.question_quality_service import filter_valid_questions, is_valid_choice_question
from services.spark_client import SparkClientError, SparkLiteClient

logger = logging.getLogger(__name__)

QUESTION_TYPES = frozenset({"choice", "judge", "short", "coding"})
MIN_QUESTIONS = 5
MAX_QUESTIONS = 10
SESSION_TTL_HOURS = 4

# MongoDB 不可用时的进程内兜底（开发环境）
_memory_sessions: dict[str, dict] = {}

GENERATE_PROMPT = """你是 Python 程序设计课程的题库智能体（EXAM），为大学生生成专项练习。
模块：{module_name}
当前掌握分：{current_score}/100
难度侧重：{difficulty_hint}
知识点参考：{kp_names}

请生成 {count} 道题，题型必须包含：单选题(choice)、判断题(judge)、简答题(short)、编程题(coding)各至少1道。

【单选题硬性要求】
1. options 必须是 4 个互不相同的完整选项内容，禁止用 A/B/C/D 或「选项A」等占位文字。
2. answer 必须是 options 中唯一正确的选项字母（A/B/C/D）。
3. 题干与选项、答案必须逻辑自洽，确保只有一个正确答案。

只输出合法 JSON，不要 markdown 包裹：
{{
  "questions": [
    {{
      "qid": "1",
      "type": "choice",
      "content": "Python 中，以下哪个不是合法的变量名？",
      "options": {{"A":"2name", "B":"_count", "C":"my_var", "D":"class"}},
      "answer": "A",
      "analysis": "变量名不能以数字开头；class 是关键字但选项 D 写的是 class 作为标识符示例"
    }},
    {{
      "qid": "2",
      "type": "judge",
      "content": "判断题干",
      "answer": "对",
      "analysis": "解析"
    }},
    {{
      "qid": "3",
      "type": "short",
      "content": "简答题干",
      "answer": "参考答案要点",
      "analysis": "解析"
    }},
    {{
      "qid": "4",
      "type": "coding",
      "content": "编程题要求（需编写可运行函数）",
      "answer": "def example():\n    pass",
      "test_cases": [
        {{"call": "example()", "expected": null}}
      ],
      "analysis": "思路解析"
    }}
  ]
}}
answer 字段：choice 为 A/B/C/D；judge 为「对」或「错」。
编程题必须提供 test_cases（至少2组 call/expected），call 为可执行 Python 表达式。"""


def _score_to_level(score: int) -> int:
    if score >= 85:
        return 4
    if score >= 70:
        return 3
    if score >= 45:
        return 2
    return 1


def _difficulty_hint(score: int | None) -> str:
    if score is None or score < 45:
        return "以基础巩固为主，题目偏易"
    if score >= 85:
        return "以拔高挑战为主，题目偏难"
    return "基础与提升均衡"


def _module_context(student_id: int, module_id: int) -> dict:
    mod = SubjectModule.query.get(module_id)
    if not mod:
        raise ValueError(f"模块不存在: {module_id}")

    mastery = get_mastery_view(student_id)
    mod_data = next(
        (m for m in mastery.get("modules", []) if int(m.get("module_id") or 0) == module_id),
        None,
    )
    current_score = int(mod_data.get("final_score") or 45) if mod_data else 45

    kps = KnowledgePoint.query.filter_by(module_id=module_id).order_by(KnowledgePoint.kp_id).all()
    kp_names = "、".join(k.kp_name for k in kps[:8]) or mod.module_name

    return {
        "module_id": module_id,
        "module_name": mod.module_name,
        "current_score": current_score,
        "difficulty_hint": _difficulty_hint(current_score),
        "kp_names": kp_names,
    }


def _clean_json_text(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```json\s*", "", t)
        t = re.sub(r"^```\s*", "", t)
        t = re.sub(r"```\s*$", "", t)
    start = t.find("{")
    end = t.rfind("}")
    return t[start : end + 1] if start >= 0 and end > start else t


def _normalize_question(raw: dict, idx: int) -> dict | None:
    qtype = (raw.get("type") or "choice").strip().lower()
    if qtype not in QUESTION_TYPES:
        qtype = "choice"
    content = (raw.get("content") or raw.get("question") or "").strip()
    if not content:
        return None
    answer = (raw.get("answer") or "").strip()
    if isinstance(answer, list):
        answer = "".join(str(a) for a in answer)
    analysis = (raw.get("analysis") or "").strip()
    options = raw.get("options")
    if isinstance(options, list):
        options = {chr(65 + i): str(v) for i, v in enumerate(options)}
    if qtype == "choice":
        if not isinstance(options, dict):
            return None
        candidate = {
            "type": "choice",
            "content": content,
            "options": options,
            "answer": answer,
        }
        if not is_valid_choice_question(candidate):
            return None
    if qtype == "judge" and answer in ("T", "true", "True", "正确"):
        answer = "对"
    if qtype == "judge" and answer in ("F", "false", "False", "错误"):
        answer = "错"
    test_cases = raw.get("test_cases")
    if isinstance(test_cases, list):
        test_cases = [tc for tc in test_cases if isinstance(tc, dict)]
    else:
        test_cases = None
    return {
        "qid": str(raw.get("qid") or idx + 1),
        "type": qtype,
        "content": content,
        "options": options if qtype == "choice" else None,
        "answer": answer,
        "analysis": analysis,
        "test_cases": test_cases,
    }


def _generate_via_spark(ctx: dict, count: int) -> list[dict]:
    client = SparkLiteClient()
    prompt = GENERATE_PROMPT.format(
        module_name=ctx["module_name"],
        current_score=ctx["current_score"],
        difficulty_hint=ctx["difficulty_hint"],
        kp_names=ctx["kp_names"],
        count=count,
    )
    raw = client.chat(prompt, max_tokens=4096)
    data = json.loads(_clean_json_text(raw))
    questions = []
    for i, q in enumerate(data.get("questions") or []):
        norm = _normalize_question(q, i)
        if norm and norm.get("answer"):
            questions.append(norm)
    return filter_valid_questions(
        questions,
        module_name=ctx.get("module_name") or "",
        module_id=ctx.get("module_id"),
    )


def _fallback_from_db(module_id: int, count: int) -> list[dict]:
    """星火不可用时从本地题库抽题并补全题型。"""
    kp_ids = [k.kp_id for k in KnowledgePoint.query.filter_by(module_id=module_id).all()]
    pool = []
    if kp_ids:
        pool = Exercise.query.filter(Exercise.kp_id.in_(kp_ids)).all()
    if not pool:
        pool = Exercise.query.limit(20).all()
    random.shuffle(pool)

    templates = [
        ("judge", "Python 中 list 是可变类型。", "对", "list 支持原地修改。", None),
        ("short", "简述 Python 中 if __name__ == '__main__' 的作用。", "标识模块被直接运行时的入口。", "用于区分导入与直接执行。", None),
    ]
    mod = SubjectModule.query.get(module_id)
    mod_name = mod.module_name if mod else ""
    from services.resource_content_builder import get_coding_challenge

    coding_q = get_coding_challenge(mod_name, module_id)
    if coding_q:
        templates.append(
            (
                "coding",
                coding_q["content"],
                coding_q["answer"],
                coding_q.get("analysis") or "",
                coding_q.get("test_cases"),
            )
        )
    questions: list[dict] = []
    choice_idx = 0
    for ex in pool:
        if choice_idx >= max(0, count - len(templates)):
            break
        candidate = {
            "qid": str(choice_idx + 1),
            "type": "choice",
            "content": ex.content,
            "options": ex.options_dict(),
            "answer": (ex.answer or "A").strip().upper()[:1],
            "analysis": "请参考课程讲义复习相关知识点。",
            "test_cases": None,
        }
        if not is_valid_choice_question(candidate):
            continue
        questions.append(candidate)
        choice_idx += 1
    base = len(questions)
    for j, tpl in enumerate(templates):
        if base + j >= count:
            break
        qtype, content, answer, analysis, test_cases = tpl
        questions.append(
            {
                "qid": str(base + j + 1),
                "type": qtype,
                "content": content,
                "options": None,
                "answer": answer,
                "analysis": analysis,
                "test_cases": test_cases,
            }
        )
    return questions[:count]


def _public_question(q: dict) -> dict:
    """下发前端时不含标准答案与测试用例详情。"""
    out = {
        "qid": q["qid"],
        "type": q["type"],
        "content": q["content"],
        "options": q.get("options"),
    }
    if q.get("type") == "coding" and q.get("test_cases"):
        out["has_auto_test"] = True
        out["test_count"] = len(q["test_cases"])
    return out


def _save_session(
    student_id: int,
    module_id: int,
    module_name: str,
    questions: list[dict],
    source: str,
    extra: dict | None = None,
) -> str:
    session_id = str(uuid4())
    now = datetime.utcnow()
    doc = {
        "session_id": session_id,
        "student_id": student_id,
        "module_id": module_id,
        "module_name": module_name,
        "source": source,
        "questions": questions,
        "created_at": now,
        "expires_at": now + timedelta(hours=SESSION_TTL_HOURS),
    }
    if extra:
        doc.update(extra)
    try:
        practice_session_collection().insert_one(doc)
    except Exception as exc:
        logger.warning("MongoDB 练习会话写入失败，使用内存兜底: %s", exc)
        _memory_sessions[session_id] = doc
    return session_id


def _load_session(session_id: str, student_id: int) -> dict | None:
    doc = None
    try:
        doc = practice_session_collection().find_one({"session_id": session_id, "student_id": student_id})
    except Exception:
        doc = _memory_sessions.get(session_id)
    if not doc:
        doc = _memory_sessions.get(session_id)
    if not doc or int(doc.get("student_id") or 0) != student_id:
        return None
    if doc.get("expires_at") and doc["expires_at"] < datetime.utcnow():
        _memory_sessions.pop(session_id, None)
        return None
    return doc


def generate_practice_set(
    student_id: int,
    module_id: int,
    source: str = "profile",
    *,
    question_count: int | None = None,
    session_extra: dict | None = None,
) -> dict:
    ctx = _module_context(student_id, module_id)
    count = question_count if question_count is not None else random.randint(MIN_QUESTIONS, MAX_QUESTIONS)
    count = max(2, min(count, MAX_QUESTIONS))
    min_required = min(2, count) if question_count is not None else MIN_QUESTIONS
    questions: list[dict] = []
    agent = "EXAM"

    try:
        questions = _generate_via_spark(ctx, count)
        if len(questions) < min_required:
            raise SparkClientError("生成题量不足")
    except Exception as exc:
        logger.warning("星火出题失败，使用本地题库兜底: %s", exc)
        agent = "EXAM_FALLBACK"
        questions = _fallback_from_db(module_id, count)

    if len(questions) > count:
        questions = questions[:count]

    session_id = _save_session(
        student_id, module_id, ctx["module_name"], questions, source, extra=session_extra
    )

    from services.behavior_event_service import record_event

    event_type = "exercise_center" if source == "exercise_center" else "module_practice"
    record_event(
        student_id,
        event_type,
        "session_generate" if source == "exercise_center" else "practice_generate",
        {"module_id": module_id, "count": len(questions), "agent": agent, "source": source},
    )

    out = {
        "session_id": session_id,
        "student_id": student_id,
        "module_id": module_id,
        "module_name": ctx["module_name"],
        "current_score": ctx["current_score"],
        "question_count": len(questions),
        "questions": [_public_question(q) for q in questions],
        "agent": agent,
        "source": source,
        "ai_generated": agent == "EXAM",
    }
    if session_extra:
        out.update({k: v for k, v in session_extra.items() if k in ("mode", "mode_label", "roadmap_day")})
    return out


def _judge_choice_or_judge(
    correct: str,
    user: str,
    qtype: str,
    options: dict | None = None,
) -> tuple[bool, str]:
    c = (correct or "").strip()
    u = (user or "").strip()
    if not u:
        return False, "未作答"
    if qtype == "judge":
        c_norm = "对" if c.upper() in ("对", "T", "TRUE", "正确", "是", "YES") else "错"
        u_norm = "对" if u.upper() in ("对", "T", "TRUE", "正确", "是", "YES") else "错"
        ok = c_norm == u_norm
        return ok, "判断正确" if ok else f"应为「{c_norm}」"

    correct_key = _match_option_key(c, options)
    user_key = _match_option_key(u, options)

    if user_key and correct_key:
        ok = user_key == correct_key
        correct_label = _format_option_label(correct_key, options)
        return ok, "选择正确" if ok else f"正确答案为 {correct_label}"

    c_up = c.upper()
    u_up = u.upper()
    c_letter = c_up[0] if c_up else ""
    u_letter = u_up[0] if u_up else ""

    if isinstance(options, dict) and options:
        opt_keys = {str(k).upper(): k for k in options.keys()}
        user_key = opt_keys.get(u_up) or opt_keys.get(u_letter)
        if user_key is not None:
            opt_text = str(options.get(user_key, "")).strip().upper()
            if c_up == str(user_key).upper() or c_up == u_up:
                return True, "选择正确"
            if opt_text and (c_up == opt_text or c_letter == str(user_key).upper()):
                return True, "选择正确"
            if opt_text and (c_up in opt_text or opt_text in c_up):
                return True, "选择正确"

    ok = u_letter == c_letter and c_letter
    correct_label = _format_option_label(correct_key, options) if correct_key else c_letter
    return ok, "选择正确" if ok else f"正确答案为 {correct_label}"


def submit_practice(student_id: int, session_id: str, answers: list[dict]) -> dict:
    session = _load_session(session_id, student_id)
    if not session:
        raise ValueError("练习会话不存在或已过期，请重新生成题目")

    q_map = {str(q["qid"]): q for q in session.get("questions") or []}
    ans_map = {str(a.get("qid")): (a.get("answer") or a.get("user_answer") or "") for a in answers}

    results = []
    score_points = 0.0
    correct_count = 0
    partial_count = 0
    for qid, q in q_map.items():
        user_ans = str(ans_map.get(qid, "")).strip()
        qtype = q["type"]
        reference = q.get("answer") or ""

        if qtype in ("choice", "judge"):
            is_correct, judge_reason = _judge_choice_or_judge(
                reference, user_ans, qtype, q.get("options")
            )
            judge_fields = build_objective_judge_fields(is_correct, judge_reason)
        elif qtype == "multi_choice":
            is_correct, judge_reason = judge_multi_choice(reference, user_ans, q.get("options"))
            judge_fields = build_objective_judge_fields(is_correct, judge_reason)
        elif qtype == "coding":
            outcome = judge_coding_answer(
                q["content"],
                reference,
                user_ans,
                q.get("test_cases"),
            )
            judge_fields = build_outcome_judge_fields(outcome)
        else:
            outcome = judge_short_answer(q["content"], reference, user_ans)
            judge_fields = build_outcome_judge_fields(outcome)

        score_points += judge_fields["score_weight"]
        if judge_fields["is_correct"]:
            correct_count += 1
        elif judge_fields["is_partial"]:
            partial_count += 1

        results.append(
            {
                "qid": qid,
                "type": qtype,
                "content": q["content"],
                "options": q.get("options") or {},
                "user_answer": user_ans,
                "correct_answer": reference,
                "analysis": q.get("analysis") or "",
                **judge_fields,
            }
        )

    total = len(q_map) or 1
    practice_pct = round(score_points / total * 100)
    module_id = int(session["module_id"])
    module_name = session.get("module_name") or ""

    profile_update = _apply_score_to_profile(student_id, module_id, module_name, practice_pct, correct_count, total)

    from services.behavior_event_service import record_event

    record_event(
        student_id,
        "module_practice",
        "practice_submit",
        {
            "module_id": module_id,
            "correct": correct_count,
            "total": total,
            "practice_pct": practice_pct,
            **profile_update,
        },
    )

    from services.wrong_question_service import persist_practice_wrong_questions

    persist_practice_wrong_questions(student_id, module_id, module_name, results)

    from services.answer_record_service import persist_practice_answer_records

    source = "exercise_center" if session.get("source") == "exercise_center" else "module_practice"
    persist_practice_answer_records(student_id, module_id, results, source=source)

    try:
        practice_session_collection().delete_one({"session_id": session_id})
    except Exception:
        pass
    _memory_sessions.pop(session_id, None)

    return {
        "student_id": student_id,
        "session_id": session_id,
        "module_id": module_id,
        "module_name": module_name,
        "correct_count": correct_count,
        "partial_count": partial_count,
        "total_count": total,
        "practice_score": practice_pct,
        "results": results,
        "profile_update": profile_update,
        "message": (
            f"完成「{module_name}」练习，完全正确 {correct_count} 题"
            + (f"，部分正确 {partial_count} 题" if partial_count else "")
            + f"，共 {total} 题"
        ),
    }


def _load_module_results(student_id: int) -> list[dict]:
    from sqlalchemy import text

    row = db.session.execute(
        text(
            "SELECT raw_extract_json FROM learning_profile "
            "WHERE student_id = :sid AND deleted = 0 ORDER BY version DESC LIMIT 1"
        ),
        {"sid": student_id},
    ).fetchone()
    if not row or not row[0]:
        return []
    try:
        payload = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return list(payload.get("module_results") or [])
    except (json.JSONDecodeError, TypeError):
        return []


def _apply_score_to_profile(
    student_id: int,
    module_id: int,
    module_name: str,
    practice_pct: int,
    correct_count: int,
    total: int,
) -> dict:
    """练习得分加权回写模块分数与知识点等级。"""
    from sqlalchemy import text

    from services.profile_snapshot_service import log_profile_change

    module_results = _load_module_results(student_id)
    old_score = None
    target = None
    for mr in module_results:
        if int(mr.get("module_id") or 0) == module_id:
            target = mr
            old_score = int(mr.get("final_score") or 0)
            break

    if target is None:
        mod = SubjectModule.query.get(module_id)
        target = {
            "module_id": module_id,
            "module_name": module_name or (mod.module_name if mod else ""),
            "base_score": 45,
            "quiz_score": 0,
            "final_score": 45,
            "mastery_level": "一般",
            "final_level": 2,
            "tags": {},
        }
        module_results.append(target)
        old_score = int(target.get("final_score") or 45)

    old_score = old_score if old_score is not None else int(target.get("final_score") or 45)
    new_score = clamp_score(round(old_score * 0.65 + practice_pct * 0.35))
    new_mastery = mastery_label_from_score(new_score)
    new_level = _score_to_level(new_score)

    target["final_score"] = new_score
    target["mastery_level"] = new_mastery
    target["final_level"] = new_level
    target["practice_bonus"] = practice_pct
    target["last_practice"] = {
        "correct": correct_count,
        "total": total,
        "at": datetime.utcnow().isoformat(),
    }

    synced = sync_module_level_to_knowledge_points(student_id, module_id, new_level)

    row = db.session.execute(
        text(
            "SELECT id, raw_extract_json FROM learning_profile "
            "WHERE student_id = :sid AND deleted = 0 ORDER BY version DESC LIMIT 1"
        ),
        {"sid": student_id},
    ).fetchone()

    if row:
        try:
            payload = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
        except (json.JSONDecodeError, TypeError):
            payload = {}
        payload["module_results"] = module_results
        payload.setdefault("knowledge_points", [])
        db.session.execute(
            text(
                "UPDATE learning_profile SET raw_extract_json = :raw, updated_at = :now "
                "WHERE id = :id"
            ),
            {
                "raw": json.dumps(payload, ensure_ascii=False),
                "now": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "id": row[0],
            },
        )
        db.session.commit()

    log_profile_change(
        student_id,
        f"module_score:{module_name}",
        str(old_score),
        str(new_score),
        "module_practice",
    )

    lp_sync = sync_mastery_from_student_profile(student_id)

    return {
        "old_score": old_score,
        "new_score": new_score,
        "score_delta": new_score - old_score,
        "mastery_level": new_mastery,
        "synced_kp_count": synced,
        "learning_profile_sync": lp_sync,
    }


def apply_single_coding_practice(student_id: int, module_id: int) -> dict:
    """单道代码实操验收通过后，回写模块掌握度。"""
    mod = SubjectModule.query.get(module_id)
    module_name = mod.module_name if mod else ""
    result = _apply_score_to_profile(student_id, module_id, module_name, 100, 1, 1)
    result["module_name"] = module_name
    return result
