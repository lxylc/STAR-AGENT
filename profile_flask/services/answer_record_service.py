"""答题记录：习题提交持久化与自然周学情统计。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from models import AnswerRecord, Exercise, db

logger = logging.getLogger(__name__)

TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")


def ensure_answer_record_schema() -> None:
    """为已有库补充 module_id / source 字段，并允许 ex_id 为空。"""
    stmts = [
        "ALTER TABLE answer_record MODIFY ex_id INT NULL",
        "ALTER TABLE answer_record ADD COLUMN module_id INT NULL COMMENT '所属模块'",
        "ALTER TABLE answer_record ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'profile_quiz'",
        "ALTER TABLE answer_record ADD INDEX idx_student_created (student_id, created_at)",
    ]
    for sql in stmts:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            msg = str(exc)
            if "Duplicate column" in msg or "1060" in msg or "Duplicate key name" in msg or "1061" in msg:
                continue
            logger.debug("answer_record 迁移跳过: %s", exc)


def _resolve_ex_id(qid) -> int | None:
    if qid is None:
        return None
    s = str(qid).strip()
    if not s.isdigit():
        return None
    ex_id = int(s)
    if Exercise.query.get(ex_id):
        return ex_id
    return None


def persist_practice_answer_records(
    student_id: int,
    module_id: int | None,
    results: list[dict],
    source: str = "exercise_center",
) -> int:
    """将单次练习的逐题结果写入 answer_record。"""
    if not results:
        return 0
    ensure_answer_record_schema()
    count = 0
    for item in results:
        ex_id = _resolve_ex_id(item.get("qid"))
        is_correct = bool(item.get("is_correct"))
        db.session.add(
            AnswerRecord(
                student_id=student_id,
                ex_id=ex_id,
                module_id=module_id,
                user_answer=(item.get("user_answer") or "")[:2000],
                judge_result=1 if is_correct else 0,
                source=source,
            )
        )
        count += 1
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("答题记录写入失败")
        return 0
    return count


def natural_week_range(now: datetime | None = None) -> tuple[datetime, datetime, datetime, datetime]:
    """
    自然周：周一 0:00 ~ 周日 24:00（Asia/Shanghai）。
    返回 (week_start_local, week_end_local, week_start_utc_naive, week_end_utc_naive)。
    """
    local_now = now or datetime.now(TZ_SHANGHAI)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=TZ_SHANGHAI)
    else:
        local_now = local_now.astimezone(TZ_SHANGHAI)

    week_start = (local_now - timedelta(days=local_now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)
    week_start_utc = week_start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    week_end_utc = week_end.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return week_start, week_end, week_start_utc, week_end_utc


def get_weekly_practice_overview(student_id: int) -> dict:
    """基于 answer_record 统计本周四项学情指标（时间区间由后端定义）。"""
    ensure_answer_record_schema()
    week_start, week_end, start_utc, end_utc = natural_week_range()

    summary = db.session.execute(
        text(
            """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(judge_result), 0) AS correct,
                   COALESCE(SUM(CASE WHEN judge_result = 0 THEN 1 ELSE 0 END), 0) AS wrong_count
            FROM answer_record
            WHERE student_id = :sid
              AND created_at >= :start_at
              AND created_at < :end_at
            """
        ),
        {"sid": student_id, "start_at": start_utc, "end_at": end_utc},
    ).fetchone()

    total = int(summary[0] or 0) if summary else 0
    correct = int(summary[1] or 0) if summary else 0
    wrong_count = int(summary[2] or 0) if summary else 0
    accuracy_pct = round(correct / total * 100, 1) if total else 0.0

    weak_row = db.session.execute(
        text(
            """
            SELECT COALESCE(ar.module_id, kp.module_id) AS module_id,
                   sm.module_name,
                   COUNT(*) AS wrong_cnt
            FROM answer_record ar
            LEFT JOIN exercise e ON e.ex_id = ar.ex_id
            LEFT JOIN knowledge_points kp ON kp.kp_id = e.kp_id
            LEFT JOIN subject_module sm ON sm.module_id = COALESCE(ar.module_id, kp.module_id)
            WHERE ar.student_id = :sid
              AND ar.judge_result = 0
              AND ar.created_at >= :start_at
              AND ar.created_at < :end_at
              AND COALESCE(ar.module_id, kp.module_id) IS NOT NULL
            GROUP BY COALESCE(ar.module_id, kp.module_id), sm.module_name
            ORDER BY wrong_cnt DESC
            LIMIT 1
            """
        ),
        {"sid": student_id, "start_at": start_utc, "end_at": end_utc},
    ).fetchone()

    weak_module = None
    if weak_row and weak_row[0] is not None:
        weak_module = {
            "module_id": int(weak_row[0]),
            "module_name": weak_row[1] or "",
            "wrong_count": int(weak_row[2] or 0),
        }

    week_end_display = week_end - timedelta(seconds=1)
    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end_display.strftime("%Y-%m-%d"),
        "week_label": (
            f"{week_start.strftime('%Y-%m-%d')}（周一）~ "
            f"{week_end_display.strftime('%Y-%m-%d')}（周日）"
        ),
        "time_rule": "自然周：周一 0:00 ~ 周日 24:00（北京时间）",
        "total_count": total,
        "accuracy_pct": accuracy_pct,
        "weak_module": weak_module,
        "new_wrong_count": wrong_count,
    }
