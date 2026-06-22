"""学习行为埋点 — 写入 learning_behavior_event，供评估与推送策略消费。"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from models import db

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES = {
    "login",
    "resource_view",
    "resource_generate",
    "push_read",
    "push_click",
    "tutoring_ask",
    "tutoring_media",
    "qa_ask",
    "progress_update",
    "quiz_submit",
    "evaluation_generate",
    "path_plan",
    "path_replan",
    "profile_complete",
    "module_practice",
    "roadmap_task",
    "roadmap_day_complete",
    "resource_view",
    "exercise_center",
}


def record_event(
    student_id: int,
    event_type: str,
    event_source: str | None = None,
    payload: dict | None = None,
) -> bool:
    if event_type not in VALID_EVENT_TYPES:
        logger.warning("未知行为类型: %s", event_type)
    try:
        db.session.execute(
            text(
                "INSERT INTO learning_behavior_event "
                "(student_id, event_type, event_source, payload_json, created_at) "
                "VALUES (:sid, :etype, :src, :payload, NOW())"
            ),
            {
                "sid": student_id,
                "etype": event_type,
                "src": event_source or "frontend",
                "payload": json.dumps(payload or {}, ensure_ascii=False),
            },
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        logger.exception("行为埋点写入失败")
        return False


def collect_behavior_stats(student_id: int, days: int = 30) -> dict:
    """聚合近期行为，供评估指标使用。"""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        rows = db.session.execute(
            text(
                "SELECT event_type, COUNT(*) AS cnt "
                "FROM learning_behavior_event "
                "WHERE student_id = :sid AND created_at >= :since "
                "GROUP BY event_type"
            ),
            {"sid": student_id, "since": since},
        ).fetchall()
    except Exception:
        logger.exception("行为统计查询失败")
        return {"total_events": 0, "by_type": {}, "days": days}

    by_type = {r[0]: int(r[1]) for r in rows}
    total = sum(by_type.values())

    push_read = by_type.get("push_read", 0) + by_type.get("push_click", 0)
    push_total_row = db.session.execute(
        text(
            "SELECT COUNT(*) FROM resource_push_record WHERE student_id = :sid"
        ),
        {"sid": student_id},
    ).fetchone()
    push_total = int(push_total_row[0] or 0) if push_total_row else 0
    push_read_rate = round(push_read / push_total * 100, 1) if push_total else 0.0

    progress_row = db.session.execute(
        text(
            "SELECT COUNT(*), AVG(progress_pct) FROM student_progress "
            "WHERE student_id = :sid"
        ),
        {"sid": student_id},
    ).fetchone()
    progress_count = int(progress_row[0] or 0) if progress_row else 0
    progress_avg = round(float(progress_row[1] or 0), 1) if progress_row and progress_row[1] else 0.0

    return {
        "total_events": total,
        "by_type": by_type,
        "days": days,
        "tutoring_sessions": by_type.get("tutoring_ask", 0),
        "resource_views": by_type.get("resource_view", 0),
        "resource_generates": by_type.get("resource_generate", 0),
        "push_read_rate_pct": push_read_rate,
        "push_records_total": push_total,
        "progress_update_count": by_type.get("progress_update", 0) or progress_count,
        "progress_avg_pct": progress_avg,
        "evaluation_count": by_type.get("evaluation_generate", 0),
        "activity_score": min(100, total * 2 + push_read * 3 + by_type.get("tutoring_ask", 0) * 5),
    }
