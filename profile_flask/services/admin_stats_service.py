"""管理员班级学情汇总：基于答题记录、画像与评估数据自动聚合。"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from models import SubjectModule, db
from services.answer_record_service import natural_week_range
from services.learning_profile_sync import get_mastery_view
from services.profile_snapshot_service import _load_raw_module_results

TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")
ACTIVE_DAYS = 7


def _format_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M")


def _student_last_active(student_id: int) -> datetime | None:
    row = db.session.execute(
        text(
            """
            SELECT MAX(created_at) FROM answer_record WHERE student_id = :sid
            """
        ),
        {"sid": student_id},
    ).fetchone()
    last = row[0] if row and row[0] else None
    try:
        row2 = db.session.execute(
            text(
                """
                SELECT MAX(created_at) FROM learning_behavior_event WHERE student_id = :sid
                """
            ),
            {"sid": student_id},
        ).fetchone()
        if row2 and row2[0]:
            if last is None or row2[0] > last:
                last = row2[0]
    except Exception:
        db.session.rollback()
    return last


def get_students_learning_stats(student_ids: list[int]) -> dict[int, dict]:
    """返回各学生的整体学情均分与最近活跃时间。"""
    result: dict[int, dict] = {}
    for sid in student_ids:
        mastery = get_mastery_view(sid)
        avg_score = mastery.get("summary", {}).get("avg_score", 0) or 0
        last_dt = _student_last_active(sid)
        result[sid] = {
            "avg_score": avg_score,
            "last_active_at": _format_dt(last_dt),
            "has_profile": mastery.get("has_profile", False),
        }
    return result


def _aggregate_weak_knowledge_points(student_ids: list[int], limit: int = 3) -> list[dict]:
    if not student_ids:
        return []
    placeholders = ", ".join(f":sid{i}" for i in range(len(student_ids)))
    params = {f"sid{i}": sid for i, sid in enumerate(student_ids)}
    rows = db.session.execute(
        text(
            f"""
            SELECT kp.kp_name,
                   sm.module_name,
                   AVG(sp.master_level) AS avg_level,
                   SUM(CASE WHEN sp.master_level <= 2 THEN 1 ELSE 0 END) AS weak_count,
                   COUNT(*) AS student_count
            FROM student_profile sp
            JOIN knowledge_points kp ON kp.kp_id = sp.kp_id
            JOIN subject_module sm ON sm.module_id = kp.module_id
            WHERE sp.student_id IN ({placeholders})
            GROUP BY kp.kp_id, kp.kp_name, sm.module_name
            HAVING weak_count > 0
            ORDER BY avg_level ASC, weak_count DESC
            LIMIT :lim
            """
        ),
        {**params, "lim": limit},
    ).fetchall()
    return [
        {
            "kp_name": r[0],
            "module_name": r[1],
            "avg_level": round(float(r[2] or 0), 1),
            "weak_count": int(r[3] or 0),
        }
        for r in rows
    ]


def _aggregate_module_scores(student_ids: list[int]) -> list[dict]:
    modules = SubjectModule.query.order_by(SubjectModule.module_id).all()
    module_names = {m.module_id: m.module_name for m in modules}
    score_sums: dict[int, list[float]] = {m.module_id: [] for m in modules}

    for sid in student_ids:
        raw = _load_raw_module_results(sid)
        if raw:
            for item in raw:
                mid = int(item.get("module_id") or 0)
                score = item.get("final_score")
                if mid and score is not None:
                    score_sums.setdefault(mid, []).append(float(score))
        else:
            mastery = get_mastery_view(sid)
            for mod in mastery.get("modules") or []:
                mid = int(mod.get("module_id") or 0)
                score = mod.get("final_score")
                if mid and score is not None:
                    score_sums.setdefault(mid, []).append(float(score))

    result = []
    for mid in sorted(module_names.keys()):
        scores = score_sums.get(mid) or []
        result.append(
            {
                "module_id": mid,
                "module_name": module_names[mid],
                "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
                "student_count": len(scores),
            }
        )
    return result


def get_class_overview(student_ids: list[int]) -> dict:
    """班级学情总览四卡片 + 12 模块条形汇总数据。"""
    if not student_ids:
        return {
            "total_students": 0,
            "active_count": 0,
            "class_avg_score": 0,
            "top3_weak_kps": [],
            "weekly_question_count": 0,
            "module_scores": _aggregate_module_scores([]),
        }

    stats_map = get_students_learning_stats(student_ids)
    now_local = datetime.now(TZ_SHANGHAI)
    active_threshold = now_local - timedelta(days=ACTIVE_DAYS)

    active_count = 0
    score_list = []
    for sid, st in stats_map.items():
        if st.get("has_profile") and st.get("avg_score"):
            score_list.append(float(st["avg_score"]))
        last_str = st.get("last_active_at")
        if last_str:
            try:
                last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_SHANGHAI)
                if last_dt >= active_threshold:
                    active_count += 1
            except ValueError:
                pass

    _, _, start_utc, end_utc = natural_week_range()
    placeholders = ", ".join(f":sid{i}" for i in range(len(student_ids)))
    params = {f"sid{i}": sid for i, sid in enumerate(student_ids)}
    weekly_row = db.session.execute(
        text(
            f"""
            SELECT COUNT(*) FROM answer_record
            WHERE student_id IN ({placeholders})
              AND created_at >= :start_at AND created_at < :end_at
            """
        ),
        {**params, "start_at": start_utc, "end_at": end_utc},
    ).fetchone()
    weekly_count = int(weekly_row[0] or 0) if weekly_row else 0

    return {
        "total_students": len(student_ids),
        "active_count": active_count,
        "class_avg_score": round(sum(score_list) / len(score_list), 1) if score_list else 0,
        "top3_weak_kps": _aggregate_weak_knowledge_points(student_ids, 3),
        "weekly_question_count": weekly_count,
        "module_scores": _aggregate_module_scores(student_ids),
    }
