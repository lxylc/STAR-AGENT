"""学习资源完成状态：已阅 / 已完成（习题）。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from services.mongo_client import ensure_indexes, get_db

logger = logging.getLogger(__name__)

RESOURCE_PROGRESS_COL = "resource_progress"
VALID_STATUSES = frozenset({"viewed", "completed"})


def _ensure_resource_progress_indexes(col):
    """确保 (student_id, resource_id) 复合唯一索引；移除误建的 student_id 单字段唯一索引。"""
    for idx in col.list_indexes():
        key = idx.get("key") or {}
        if idx.get("name") == "_id_":
            continue
        # 旧版误建：仅 student_id 唯一，会导致同一学生只能标记一条资源
        if list(key.keys()) == ["student_id"] and idx.get("unique"):
            col.drop_index(idx["name"])
            logger.info("已移除错误的 resource_progress 索引: %s", idx["name"])
    col.create_index([("student_id", 1), ("resource_id", 1)], unique=True)


def _collection():
    ensure_indexes()
    col = get_db()[RESOURCE_PROGRESS_COL]
    _ensure_resource_progress_indexes(col)
    return col


def mark_resource_status(
    student_id: int,
    resource_id: str,
    status: str,
    *,
    resource_type: str | None = None,
    module_id: int | None = None,
    score: int | None = None,
) -> dict:
    if not resource_id:
        raise ValueError("缺少 resource_id")
    if status not in VALID_STATUSES:
        raise ValueError(f"无效状态: {status}")

    now = datetime.now(timezone.utc).isoformat()
    col = _collection()
    existing = col.find_one({"student_id": student_id, "resource_id": resource_id}) or {}
    doc = {
        "student_id": student_id,
        "resource_id": resource_id,
        "status": status,
        "resource_type": resource_type or existing.get("resource_type"),
        "module_id": module_id if module_id is not None else existing.get("module_id"),
        "score": score if score is not None else existing.get("score"),
        "updated_at": now,
    }
    if status == "viewed" and not existing.get("viewed_at"):
        doc["viewed_at"] = now
    elif status == "completed":
        doc["completed_at"] = now
        if not existing.get("viewed_at"):
            doc["viewed_at"] = now

    col.update_one(
        {"student_id": student_id, "resource_id": resource_id},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return doc


def get_resource_status_map(student_id: int, resource_ids: list[str] | None = None) -> dict[str, dict]:
    col = _collection()
    query: dict = {"student_id": student_id}
    if resource_ids:
        query["resource_id"] = {"$in": [str(r) for r in resource_ids]}
    rows = col.find(query, {"_id": 0})
    return {r["resource_id"]: r for r in rows}
