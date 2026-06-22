"""评估调整预览与应用同步 — 打通学习方案每日路线。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from services.mongo_client import ensure_indexes, get_db

logger = logging.getLogger(__name__)

APPLY_LOG_COL = "evaluation_apply_log"
TYPE_LABELS = {"lecture": "讲义", "exercise": "习题", "courseware": "课件", "exam_summary": "考点"}


def _collection():
    ensure_indexes()
    col = get_db()[APPLY_LOG_COL]
    col.create_index([("student_id", 1), ("applied_at", -1)])
    return col


def build_adjustment_preview(adjustment: dict | None) -> dict:
    """生成「确认应用」前的调整预览（不调 Java）。"""
    adj = adjustment or {}
    weak = adj.get("weak_modules") or []
    prefer = adj.get("prefer_resource_types") or ["lecture", "exercise"]

    priority_changes = [
        {
            "module_name": name,
            "from_priority": "常规",
            "to_priority": "优先学习",
            "action": "提升路径优先级",
        }
        for name in weak
    ]
    if not priority_changes:
        priority_changes = [
            {
                "module_name": "当前进行中模块",
                "from_priority": "常规",
                "to_priority": "适度加强",
                "action": "微调路径优先级",
            }
        ]

    roadmap_notes = []
    for name in weak[:4]:
        roadmap_notes.append(f"「{name}」每日学习任务将侧重{'、'.join(TYPE_LABELS.get(t, t) for t in prefer[:2])}")

    return {
        "weak_modules": weak,
        "priority_changes": priority_changes,
        "push_strategy": adj.get("push_strategy") or "按薄弱模块倾斜推送学习资源",
        "path_adjustment": adj.get("path_adjustment") or "提升薄弱模块路径优先级",
        "prefer_resource_types": prefer,
        "prefer_resource_labels": [TYPE_LABELS.get(t, t) for t in prefer],
        "estimated_push_count": max(1, len(weak)),
        "roadmap_notes": roadmap_notes or ["维持当前学习节奏，按方案稳步推进"],
        "recommended_actions": adj.get("recommended_actions") or [],
    }


def set_evaluation_focus(
    student_id: int,
    eval_id: int | None,
    weak_modules: list[str],
    prefer_resource_types: list[str],
) -> None:
    """将评估结论写入路线进度，供学习方案读取。"""
    from services.roadmap_progress_service import _collection as roadmap_col

    now = datetime.now(timezone.utc).isoformat()
    roadmap_col().update_one(
        {"student_id": student_id},
        {
            "$set": {
                "evaluation_focus": {
                    "eval_id": eval_id,
                    "weak_modules": weak_modules,
                    "prefer_resource_types": prefer_resource_types,
                    "applied_at": now,
                },
                "updated_at": now,
            }
        },
        upsert=True,
    )


def get_evaluation_focus(student_id: int) -> dict | None:
    from services.roadmap_progress_service import _collection as roadmap_col

    doc = roadmap_col().find_one({"student_id": student_id})
    if not doc:
        return None
    return doc.get("evaluation_focus")


def record_apply_log(
    student_id: int,
    eval_id: int | None,
    adjustment: dict,
    java_ok: bool,
    roadmap_synced: bool,
) -> dict:
    preview = build_adjustment_preview(adjustment)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "student_id": student_id,
        "eval_id": eval_id,
        "applied_at": now,
        "weak_modules": preview.get("weak_modules"),
        "prefer_resource_types": preview.get("prefer_resource_types"),
        "push_strategy": preview.get("push_strategy"),
        "path_adjustment": preview.get("path_adjustment"),
        "java_path_applied": java_ok,
        "roadmap_synced": roadmap_synced,
        "summary": (
            f"已提升 {len(preview.get('weak_modules') or [])} 个薄弱模块优先级，"
            f"刷新约 {preview.get('estimated_push_count')} 条资源推送"
        ),
    }
    _collection().insert_one(doc)
    doc.pop("_id", None)
    return doc


def get_latest_apply_log(student_id: int) -> dict | None:
    doc = _collection().find_one({"student_id": student_id}, sort=[("applied_at", -1)])
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


def apply_evaluation_sync(
    student_id: int,
    eval_id: int | None,
    adjustment: dict | None,
    java_ok: bool = True,
) -> dict:
    adj = adjustment or {}
    weak = adj.get("weak_modules") or []
    prefer = adj.get("prefer_resource_types") or ["lecture", "exercise"]
    set_evaluation_focus(student_id, eval_id, weak, prefer)
    log = record_apply_log(student_id, eval_id, adj, java_ok, roadmap_synced=True)

    from services.behavior_event_service import record_event

    record_event(
        student_id,
        "evaluation_apply",
        "evaluation_adjust",
        {"eval_id": eval_id, "weak_count": len(weak), "java_ok": java_ok},
    )
    return log
