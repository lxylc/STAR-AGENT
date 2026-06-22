"""统一习题中心：专项习题、错题重做、路线配套习题、模块练习入口聚合。"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from uuid import uuid4

from models import Exercise, KnowledgePoint, SubjectModule, db
from knowledge_data import EXERCISE_BANK, MODULE_NAMES
from services.module_practice_service import (
    _apply_score_to_profile,
    _judge_choice_or_judge,
    generate_practice_set,
    submit_practice,
)
from services.mongo_client import practice_session_collection
from services.practice_judge_service import (
    build_objective_judge_fields,
    build_outcome_judge_fields,
    judge_coding_answer,
    judge_multi_choice,
    judge_short_answer,
)
from services.tag_navigate_service import _fetch_training_exercises, _pick_primary_kp

logger = logging.getLogger(__name__)

SESSION_TTL_HOURS = 4
_memory_sessions: dict[str, dict] = {}

MODE_LABELS = {
    "special": "专项习题",
    "module": "模块能力训练",
    "wrong": "错题重做",
    "roadmap": "学习路线习题",
}

CHAPTER_STAGES = [
    {"stage": 1, "stage_name": "阶段一·入门奠基", "module_names": MODULE_NAMES[0:3]},
    {"stage": 2, "stage_name": "阶段二·核心语法", "module_names": MODULE_NAMES[3:6]},
    {"stage": 3, "stage_name": "阶段三·进阶能力", "module_names": MODULE_NAMES[6:9]},
    {"stage": 4, "stage_name": "阶段四·实战应用", "module_names": MODULE_NAMES[9:12]},
]


def _save_session(doc: dict) -> str:
    session_id = doc.get("session_id") or str(uuid4())
    doc["session_id"] = session_id
    doc.setdefault("created_at", datetime.utcnow())
    doc.setdefault("expires_at", doc["created_at"] + timedelta(hours=SESSION_TTL_HOURS))
    try:
        practice_session_collection().insert_one(doc)
    except Exception as exc:
        logger.warning("MongoDB 习题会话写入失败，使用内存兜底: %s", exc)
        _memory_sessions[session_id] = doc
    return session_id


def _load_session(session_id: str, student_id: int) -> dict | None:
    doc = None
    try:
        doc = practice_session_collection().find_one(
            {"session_id": session_id, "student_id": student_id}
        )
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


def _public_question(q: dict) -> dict:
    out = {
        "qid": q["qid"],
        "type": q["type"],
        "content": q["content"],
        "options": q.get("options") or {},
    }
    if q.get("wrong_item_id"):
        out["wrong_item_id"] = q["wrong_item_id"]
    return out


def _exercise_to_question(ex: Exercise, idx: int, module_id: int, module_name: str) -> dict:
    kp = KnowledgePoint.query.get(ex.kp_id)
    qtype = ex.question_type or "choice"
    if qtype not in ("choice", "judge", "short", "coding"):
        qtype = "choice"
    return {
        "qid": str(ex.ex_id),
        "type": qtype,
        "content": ex.content,
        "options": ex.options_dict(),
        "answer": ex.answer,
        "analysis": "",
        "module_id": module_id,
        "module_name": module_name,
        "kp_name": kp.kp_name if kp else "",
    }


def _load_static_questions(
    student_id: int,
    module_id: int,
    limit: int = 10,
    kp_id: int | None = None,
    item_ids: list[str] | None = None,
) -> tuple[list[dict], str, int]:
    from models import SubjectModule
    from services.resource_content_builder import collect_module_questions

    mod = SubjectModule.query.get(module_id)
    if not mod:
        raise ValueError(f"模块不存在: {module_id}")

    questions = collect_module_questions(module_id, mod.module_name)
    if kp_id:
        filtered = [q for q in questions if q.get("kp_id") == kp_id]
        if filtered:
            questions = filtered

    if item_ids:
        id_set = {str(x) for x in item_ids}
        picked = [q for q in questions if str(q.get("qid")) in id_set]
        if picked:
            return picked, mod.module_name, module_id
        raise ValueError("未找到指定题目，请返回资源页刷新后重试")

    limit = max(limit, 8)
    if len(questions) > limit:
        rng = random.Random(f"{student_id}:{module_id}:{datetime.utcnow().strftime('%Y%m%d%H')}")
        questions = rng.sample(questions, limit)
    return questions, mod.module_name, module_id


def _count_static_questions(module_id: int, module_name: str) -> int:
    count = Exercise.query.join(KnowledgePoint, Exercise.kp_id == KnowledgePoint.kp_id).filter(
        KnowledgePoint.module_id == module_id
    ).count()
    bank = EXERCISE_BANK.get(module_name) or {}
    for items in bank.values():
        count += len(items)
    from services.resource_content_builder import get_coding_challenge

    if get_coding_challenge(module_name, module_id):
        count += 1
    return count


def _roadmap_module_days(student_id: int) -> dict[int, int]:
    """module_id -> roadmap day（无路线则空 dict）。"""
    try:
        from services.resource_orchestrator_service import build_resource_plan

        plan = build_resource_plan(student_id)
        out: dict[int, int] = {}
        for step in plan.get("roadmap") or []:
            mid = step.get("module_id")
            day = step.get("day")
            if mid is not None and day is not None:
                out[int(mid)] = int(day)
        return out
    except Exception:
        logger.debug("读取学习路线失败", exc_info=True)
        return {}


def _build_chapter_stages(student_id: int) -> list[dict]:
    from services.wrong_question_service import list_wrong_questions
    from services.profile_snapshot_service import get_profile_dashboard
    from services.resource_exercise_service import count_special_questions_by_module
    from services.answer_record_service import natural_week_range

    wrong = list_wrong_questions(student_id, limit=200)
    special_counts = count_special_questions_by_module(student_id)
    wrong_by_module = {
        int(s["module_id"]): int(s.get("wrong_count") or 0)
        for s in (wrong.get("module_stats") or [])
        if s.get("module_id") is not None
    }
    dashboard = get_profile_dashboard(student_id)
    score_map = {
        int(m["module_id"]): m
        for m in (dashboard.get("modules") or [])
        if m.get("module_id") is not None
    }
    roadmap_days = _roadmap_module_days(student_id)

    _, _, week_start_utc, week_end_utc = natural_week_range()
    week_practice_by_module: dict[int, int] = {}
    try:
        from sqlalchemy import text

        rows = db.session.execute(
            text(
                """
                SELECT COALESCE(ar.module_id, kp.module_id) AS module_id, COUNT(*) AS cnt
                FROM answer_record ar
                LEFT JOIN exercise e ON e.ex_id = ar.ex_id
                LEFT JOIN knowledge_points kp ON kp.kp_id = e.kp_id
                WHERE ar.student_id = :sid
                  AND ar.created_at >= :start_at
                  AND ar.created_at < :end_at
                  AND COALESCE(ar.module_id, kp.module_id) IS NOT NULL
                GROUP BY COALESCE(ar.module_id, kp.module_id)
                """
            ),
            {"sid": student_id, "start_at": week_start_utc, "end_at": week_end_utc},
        ).fetchall()
        week_practice_by_module = {int(r[0]): int(r[1]) for r in rows if r[0] is not None}
    except Exception:
        logger.debug("本周章节练习量统计失败", exc_info=True)

    modules = SubjectModule.query.order_by(SubjectModule.module_id).all()
    mod_by_name = {m.module_name: m for m in modules}

    stages_out = []
    chapter_no = 0
    for st in CHAPTER_STAGES:
        chapters = []
        for name in st["module_names"]:
            mod = mod_by_name.get(name)
            if not mod:
                continue
            chapter_no += 1
            meta = score_map.get(mod.module_id, {})
            score = meta.get("final_score")
            q_count = special_counts.get(mod.module_id, 0)
            wrong_cnt = wrong_by_module.get(mod.module_id, 0)
            day = roadmap_days.get(mod.module_id)
            chapters.append(
                {
                    "chapter_no": chapter_no,
                    "module_id": mod.module_id,
                    "module_name": mod.module_name,
                    "final_score": score,
                    "week_practice_count": week_practice_by_module.get(mod.module_id, 0),
                    "stats": {
                        "special": {
                            "question_count": q_count,
                            "available": q_count > 0,
                            "pending_generate": q_count <= 0,
                        },
                        "module": {"available": True},
                        "wrong": {
                            "wrong_count": wrong_cnt,
                            "available": wrong_cnt > 0,
                        },
                        "roadmap": {
                            "day": day,
                            "available": day is not None,
                        },
                    },
                }
            )
        if chapters:
            stages_out.append(
                {
                    "stage": st["stage"],
                    "stage_name": st["stage_name"],
                    "chapters": chapters,
                }
            )
    return stages_out


def get_center_overview(student_id: int) -> dict:
    from services.wrong_question_service import list_wrong_questions
    from services.profile_snapshot_service import get_profile_dashboard
    from services.answer_record_service import get_weekly_practice_overview

    wrong = list_wrong_questions(student_id, limit=200)
    dashboard = get_profile_dashboard(student_id)
    modules = dashboard.get("modules") or []
    weak_modules = [m for m in modules if (m.get("final_score") or 100) < 60]

    entries = [
        {
            "mode": "special",
            "label": "专项习题",
            "desc": "作答一键生成时按薄弱点产出的固定题集（与模块训练不同）",
        },
        {
            "mode": "module",
            "label": "模块能力训练",
            "desc": "AI 智能出题 5–10 题，综合训练模块能力",
        },
        {
            "mode": "wrong",
            "label": "错题重做",
            "desc": f"当前错题 {wrong.get('total', 0)} 道，做对自动移出错题本",
        },
        {
            "mode": "roadmap",
            "label": "学习路线习题",
            "desc": "完成每日路线配套练习题",
        },
    ]
    return {
        "student_id": student_id,
        "wrong_count": wrong.get("total", 0),
        "weak_modules": [
            {"module_id": m["module_id"], "module_name": m["module_name"], "score": m.get("final_score")}
            for m in weak_modules[:6]
        ],
        "weekly_overview": get_weekly_practice_overview(student_id),
        "entries": entries,
        "chapter_stages": _build_chapter_stages(student_id),
    }


def generate_exercise_session(
    student_id: int,
    mode: str,
    module_id: int | None = None,
    item_ids: list[str] | None = None,
    day: int | None = None,
    kp_id: int | None = None,
    resource_id: str | None = None,
) -> dict:
    mode = (mode or "special").strip().lower()

    if isinstance(item_ids, str):
        item_ids = [x.strip() for x in item_ids.split(",") if x.strip()]
    elif isinstance(item_ids, list):
        item_ids = [str(x).strip() for x in item_ids if str(x).strip()]
    else:
        item_ids = None

    if mode == "module":
        if not module_id:
            raise ValueError("模块练习需要 module_id")
        return generate_practice_set(student_id, int(module_id), source="exercise_center")

    if mode == "wrong":
        from services.wrong_question_service import build_wrong_redo_questions

        questions, mod_id, mod_name = build_wrong_redo_questions(
            student_id,
            item_ids or [],
            int(module_id) if module_id is not None else None,
        )
        session_id = _save_session(
            {
                "student_id": student_id,
                "module_id": mod_id,
                "module_name": mod_name,
                "source": "wrong_redo",
                "mode": "wrong",
                "wrong_item_ids": [q.get("wrong_item_id") for q in questions],
                "questions": questions,
            }
        )
        return {
            "session_id": session_id,
            "student_id": student_id,
            "module_id": mod_id,
            "module_name": mod_name,
            "mode": mode,
            "mode_label": MODE_LABELS.get(mode, mode),
            "question_count": len(questions),
            "questions": [_public_question(q) for q in questions],
        }

    if not module_id:
        raise ValueError("需要 module_id")

    if mode in ("special", "roadmap"):
        from services.resource_exercise_service import load_special_exercise_questions

        questions, mod_name, mod_id, res_title, res_db_id = load_special_exercise_questions(
            student_id,
            int(module_id) if module_id else None,
            resource_id,
        )
        session_id = _save_session(
            {
                "student_id": student_id,
                "module_id": mod_id,
                "module_name": mod_name,
                "source": "exercise_center",
                "mode": mode,
                "roadmap_day": day,
                "resource_id": str(res_db_id) if res_db_id else resource_id,
                "from_generated_resource": True,
                "questions": questions,
            }
        )
        from services.behavior_event_service import record_event

        record_event(
            student_id,
            "exercise_center",
            "session_generate",
            {
                "mode": mode,
                "module_id": mod_id,
                "count": len(questions),
                "day": day,
                "resource_id": res_db_id,
                "source": "generated_resource",
            },
        )
        return {
            "session_id": session_id,
            "student_id": student_id,
            "module_id": mod_id,
            "module_name": mod_name,
            "mode": mode,
            "mode_label": MODE_LABELS.get(mode, mode),
            "roadmap_day": day,
            "question_count": len(questions),
            "questions": [_public_question(q) for q in questions],
            "resource_id": res_db_id,
            "resource_title": res_title,
            "from_generated_resource": True,
        }


def _grade_session(session: dict, answers: list[dict]) -> tuple[list[dict], float, int, int]:
    q_map = {str(q["qid"]): q for q in session.get("questions") or []}
    ans_map = {
        str(a.get("qid")): (a.get("answer") or a.get("user_answer") or "") for a in answers
    }
    results = []
    score_points = 0.0
    correct_count = 0
    partial_count = 0
    for qid, q in q_map.items():
        user_ans = str(ans_map.get(qid, "")).strip()
        qtype = q.get("type") or "choice"
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
                q["content"], reference, user_ans, q.get("test_cases")
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
                "wrong_item_id": q.get("wrong_item_id"),
                **judge_fields,
            }
        )
    return results, score_points, correct_count, partial_count


def submit_exercise_session(student_id: int, session_id: str, answers: list[dict]) -> dict:
    session = _load_session(session_id, student_id)
    if not session:
        raise ValueError("练习会话不存在或已过期，请重新加载题目")

    source = session.get("source") or ""
    mode = session.get("mode") or "special"

    if source not in ("wrong_redo", "exercise_center") and mode != "module":
        return submit_practice(student_id, session_id, answers)

    results, score_points, correct_count, partial_count = _grade_session(session, answers)
    total = len(results) or 1
    practice_pct = round(score_points / total * 100)
    module_id = int(session.get("module_id") or 0)
    module_name = session.get("module_name") or ""

    profile_update = {}
    if module_id:
        profile_update = _apply_score_to_profile(
            student_id, module_id, module_name, practice_pct, correct_count, total
        )

    removed_wrong = 0
    if source == "wrong_redo":
        from services.wrong_question_service import apply_wrong_redo_results

        removed_wrong = apply_wrong_redo_results(student_id, results)

    if mode == "roadmap" and session.get("roadmap_day"):
        try:
            from services.profile_snapshot_service import get_profile_dashboard
            from services.roadmap_progress_service import update_roadmap_task

            dashboard = get_profile_dashboard(student_id)
            modules = dashboard.get("modules") or []
            day = int(session["roadmap_day"])
            task_id = f"exercise_{module_id}_{day}"
            if practice_pct >= 60:
                update_roadmap_task(
                    student_id, day, task_id, True, modules, auto=True
                )
        except Exception as exc:
            logger.warning("路线习题任务自动完成失败: %s", exc)

    resource_id = session.get("resource_id")
    if resource_id and practice_pct >= 60:
        try:
            from services.resource_progress_service import mark_resource_status

            mark_resource_status(
                student_id,
                str(resource_id),
                "completed",
                resource_type="exercise",
                module_id=module_id,
                score=practice_pct,
            )
        except Exception as exc:
            logger.warning("资源完成状态写入失败: %s", exc)

    if source != "wrong_redo":
        from services.wrong_question_service import persist_practice_wrong_questions

        persist_practice_wrong_questions(student_id, module_id, module_name, results)

    from services.answer_record_service import persist_practice_answer_records

    persist_practice_answer_records(
        student_id,
        module_id or None,
        results,
        source=f"exercise_center_{mode}" if mode else "exercise_center",
    )

    from services.behavior_event_service import record_event

    record_event(
        student_id,
        "exercise_center",
        "session_submit",
        {
            "mode": mode,
            "module_id": module_id,
            "correct": correct_count,
            "total": total,
            "practice_pct": practice_pct,
            "removed_wrong": removed_wrong,
        },
    )

    try:
        practice_session_collection().delete_one({"session_id": session_id})
    except Exception:
        pass
    _memory_sessions.pop(session_id, None)

    msg = f"完成练习，完全正确 {correct_count} 题"
    if partial_count:
        msg += f"，部分正确 {partial_count} 题"
    msg += f"，共 {total} 题"
    if removed_wrong:
        msg += f"，已移出 {removed_wrong} 道错题"

    return {
        "student_id": student_id,
        "session_id": session_id,
        "module_id": module_id,
        "module_name": module_name,
        "mode": mode,
        "correct_count": correct_count,
        "partial_count": partial_count,
        "total_count": total,
        "practice_score": practice_pct,
        "results": results,
        "profile_update": profile_update,
        "removed_wrong_count": removed_wrong,
        "message": msg,
    }
