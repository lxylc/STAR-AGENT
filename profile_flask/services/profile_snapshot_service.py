"""画像快照、变更日志与 AI 解读。"""
import json
import logging
from datetime import datetime

from sqlalchemy import text

from config import Config
from models import db

logger = logging.getLogger(__name__)


def _load_raw_module_results(student_id: int) -> list[dict]:
    row = db.session.execute(
        text(
            "SELECT raw_extract_json FROM learning_profile "
            "WHERE student_id = :sid AND deleted = 0 AND profile_status = 'completed' "
            "ORDER BY version DESC LIMIT 1"
        ),
        {"sid": student_id},
    ).fetchone()
    if not row or not row[0]:
        return []
    try:
        payload = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return payload.get("module_results") or []
    except (json.JSONDecodeError, TypeError):
        return []


def build_ai_interpretation(module_results: list[dict]) -> str:
    """规则选型 + 模板填充（话术 18）。"""
    if not module_results:
        return "请先完成学习测评，生成专属画像。"

    scores = [
        {
            "name": m.get("module_name", ""),
            "score": int(m.get("final_score") or 0),
            "practice": (m.get("tags") or {}).get("practice_frequency", ""),
        }
        for m in module_results
    ]
    weak = [s for s in scores if s["score"] < 45]
    low_practice = sum(1 for s in scores if s["practice"] == "很少练习")

    if len(weak) >= 3:
        names = "、".join(
            s["name"]
            for s in sorted(weak, key=lambda x: x["score"])[:3]
        )
        return f"【{names}】是你的主要短板，可以优先巩固这几块内容。"

    if low_practice >= max(4, len(scores) // 3):
        return "你的基础语法掌握不错，但代码实操练习偏少，建议多动手编写案例。"

    avg = sum(s["score"] for s in scores) / len(scores) if scores else 0
    if avg >= 70 and len(weak) <= 1:
        return "你的各模块掌握较为均衡，保持日常练习即可稳步提升。"

    if weak:
        names = "、".join(s["name"] for s in weak[:2])
        return f"整体基础尚可，建议重点加强【{names}】等模块的实操练习。"
    return "你的各模块掌握较为均衡，保持日常练习即可稳步提升。"


def log_profile_change(
    student_id: int,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
    source: str,
    course_id: str | None = None,
) -> None:
    cid = course_id or Config.COURSE_ID
    db.session.execute(
        text(
            "INSERT INTO profile_change_log "
            "(student_id, course_id, field_name, old_value, new_value, source) "
            "VALUES (:sid, :cid, :field, :old, :new, :src)"
        ),
        {
            "sid": student_id,
            "cid": cid,
            "field": field_name,
            "old": old_value,
            "new": new_value,
            "src": source,
        },
    )
    db.session.commit()


def save_profile_snapshot(
    student_id: int,
    module_results: list[dict],
    course_id: str | None = None,
) -> dict:
    """完整重测完成后写入快照（日常微调不写快照）。"""
    cid = course_id or Config.COURSE_ID
    scores = {
        str(m.get("module_id")): {
            "module_name": m.get("module_name"),
            "base_score": m.get("base_score"),
            "quiz_score": m.get("quiz_score"),
            "final_score": m.get("final_score"),
            "mastery_level": m.get("mastery_level"),
        }
        for m in module_results
    }
    tags = {
        str(m.get("module_id")): m.get("tags") or {}
        for m in module_results
    }
    radar = {
        "indicators": [m.get("module_name", "") for m in module_results],
        "values": [int(m.get("final_score") or 0) for m in module_results],
    }
    interpretation = build_ai_interpretation(module_results)

    db.session.execute(
        text(
            "INSERT INTO profile_snapshot "
            "(student_id, course_id, scores_json, tags_json, radar_json) "
            "VALUES (:sid, :cid, :scores, :tags, :radar)"
        ),
        {
            "sid": student_id,
            "cid": cid,
            "scores": json.dumps(scores, ensure_ascii=False),
            "tags": json.dumps(tags, ensure_ascii=False),
            "radar": json.dumps({**radar, "interpretation": interpretation}, ensure_ascii=False),
        },
    )
    db.session.commit()
    log_profile_change(
        student_id,
        "profile_snapshot",
        None,
        f"assessment_complete_{datetime.utcnow().isoformat()}",
        "assessment",
        cid,
    )
    logger.info("画像快照已保存 student=%s modules=%s", student_id, len(module_results))
    return {"saved": True, "interpretation": interpretation}


def list_snapshots(student_id: int, course_id: str | None = None, limit: int = 10) -> list[dict]:
    cid = course_id or Config.COURSE_ID
    try:
        rows = db.session.execute(
            text(
                "SELECT id, scores_json, tags_json, radar_json, created_at FROM profile_snapshot "
                "WHERE student_id = :sid AND course_id = :cid ORDER BY id DESC LIMIT :lim"
            ),
            {"sid": student_id, "cid": cid, "lim": limit},
        ).fetchall()
    except Exception as exc:
        logger.warning("读取快照失败（表可能未迁移）: %s", exc)
        return []
    out = []
    for r in rows:
        radar = {}
        try:
            radar = json.loads(r[3]) if r[3] else {}
        except json.JSONDecodeError:
            pass
        out.append(
            {
                "id": r[0],
                "scores": json.loads(r[1]) if r[1] else {},
                "tags": json.loads(r[2]) if r[2] else {},
                "radar": radar,
                "interpretation": radar.get("interpretation", ""),
                "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
            }
        )
    return out


def list_change_logs(student_id: int, course_id: str | None = None, limit: int = 50) -> list[dict]:
    cid = course_id or Config.COURSE_ID
    try:
        rows = db.session.execute(
            text(
                "SELECT field_name, old_value, new_value, source, created_at FROM profile_change_log "
                "WHERE student_id = :sid AND course_id = :cid ORDER BY id DESC LIMIT :lim"
            ),
            {"sid": student_id, "cid": cid, "lim": limit},
        ).fetchall()
    except Exception as exc:
        logger.warning("读取变更日志失败（表可能未迁移）: %s", exc)
        return []
    return [
        {
            "field_name": r[0],
            "old_value": r[1],
            "new_value": r[2],
            "source": r[3],
            "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
        }
        for r in rows
    ]


def get_profile_dashboard(student_id: int) -> dict:
    """画像详情页聚合：掌握视图 + 解读 + 快照 + 日志。"""
    from services.learning_profile_sync import get_mastery_view

    mastery = get_mastery_view(student_id)
    module_results = _load_raw_module_results(student_id)
    interpretation = build_ai_interpretation(module_results)
    return {
        **mastery,
        "ai_interpretation": interpretation,
        "snapshots": list_snapshots(student_id),
        "change_logs": list_change_logs(student_id),
        "module_results": module_results,
    }
