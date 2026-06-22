"""个性化学习路线：当前任务阶段制，完成后按最新学情推进下一阶段。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from services.mongo_client import ensure_indexes, get_db

logger = logging.getLogger(__name__)

ROADMAP_COL = "roadmap_progress"


def _collection():
    ensure_indexes()
    col = get_db()[ROADMAP_COL]
    col.create_index([("student_id", 1)], unique=True)
    return col


def _build_stage_tasks(module_id: int, module_name: str, stage_no: int) -> list[dict]:
    return [
        {
            "id": f"lecture_{module_id}_{stage_no}",
            "type": "lecture",
            "title": f"阅读「{module_name}」精简讲义与易错点",
            "auto": False,
        },
        {
            "id": f"code_{module_id}_{stage_no}",
            "type": "code",
            "title": "观看 1 个优秀代码案例",
            "auto": False,
        },
        {
            "id": f"exercise_{module_id}_{stage_no}",
            "type": "exercise",
            "title": "完成本轮专项巩固题（3–5 道）",
            "auto": True,
        },
    ]


def _pick_next_module(modules: list[dict], completed_module_ids: set[int]) -> dict | None:
    scored = [m for m in modules if m.get("module_id") is not None and m.get("final_score") is not None]
    for m in sorted(scored, key=lambda x: float(x["final_score"])):
        mid = int(m["module_id"])
        if mid not in completed_module_ids:
            return m
    return None


def _is_stage_complete(task_map: dict, task_defs: list[dict]) -> bool:
    if not task_defs:
        return False
    for t in task_defs:
        tid = t.get("id") or ""
        if not task_map.get(tid, {}).get("completed"):
            return False
    return True


def _active_task_id(task_defs: list[dict], task_map: dict) -> str | None:
    """当前应进行的任务（按 lecture → code → exercise 顺序）。"""
    for t in task_defs:
        tid = t.get("id") or ""
        if not task_map.get(tid, {}).get("completed"):
            return tid
    return None


def _repair_current_if_needed(doc: dict, modules: list[dict]) -> dict:
    """旧数据或异常状态下补建 current 阶段。"""
    if doc.get("current"):
        return doc
    completed_set = set(int(x) for x in doc.get("completed_module_ids") or [])
    next_mod = _pick_next_module(modules, completed_set)
    if not next_mod:
        return doc
    stage_no = len(completed_set) + 1
    mid = int(next_mod["module_id"])
    name = next_mod.get("module_name") or ""
    tasks = _build_stage_tasks(mid, name, stage_no)
    task_map = {t["id"]: {"completed": False, "completed_at": None} for t in tasks}
    doc["stage_no"] = stage_no
    doc["current"] = {
        "stage_no": stage_no,
        "module_id": mid,
        "module_name": name,
        "tasks": task_map,
        "completed": False,
        "completed_at": None,
    }
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    _collection().update_one({"student_id": doc["student_id"]}, {"$set": doc}, upsert=True)
    return doc


def _ensure_doc(student_id: int, modules: list[dict]) -> dict:
    col = _collection()
    doc = col.find_one({"student_id": student_id})
    if doc:
        doc.pop("_id", None)
        doc["student_id"] = student_id
        return _repair_current_if_needed(doc, modules)

    next_mod = _pick_next_module(modules, set())
    if not next_mod:
        doc = {
            "student_id": student_id,
            "stage_no": 0,
            "completed_module_ids": [],
            "history": [],
            "current": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        col.insert_one(doc)
        doc.pop("_id", None)
        return doc

    mid = int(next_mod["module_id"])
    name = next_mod.get("module_name") or ""
    stage_no = 1
    tasks = _build_stage_tasks(mid, name, stage_no)
    task_map = {t["id"]: {"completed": False, "completed_at": None} for t in tasks}
    doc = {
        "student_id": student_id,
        "stage_no": stage_no,
        "completed_module_ids": [],
        "history": [],
        "current": {
            "stage_no": stage_no,
            "module_id": mid,
            "module_name": name,
            "tasks": task_map,
            "completed": False,
            "completed_at": None,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    col.insert_one(doc)
    doc.pop("_id", None)
    return doc


def _advance_to_next_stage(doc: dict, modules: list[dict]) -> dict:
    current = doc.get("current") or {}
    mid = current.get("module_id")
    if mid is not None:
        completed = list(doc.get("completed_module_ids") or [])
        if int(mid) not in completed:
            completed.append(int(mid))
        doc["completed_module_ids"] = completed
        history = list(doc.get("history") or [])
        history.append(
            {
                "stage_no": current.get("stage_no"),
                "module_id": mid,
                "module_name": current.get("module_name"),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        doc["history"] = history[-20:]

    completed_set = set(int(x) for x in doc.get("completed_module_ids") or [])
    next_mod = _pick_next_module(modules, completed_set)
    if not next_mod:
        doc["current"] = None
        doc["stage_no"] = len(completed_set)
        return doc

    stage_no = len(completed_set) + 1
    nmid = int(next_mod["module_id"])
    nname = next_mod.get("module_name") or ""
    tasks = _build_stage_tasks(nmid, nname, stage_no)
    task_map = {t["id"]: {"completed": False, "completed_at": None} for t in tasks}
    doc["stage_no"] = stage_no
    doc["current"] = {
        "stage_no": stage_no,
        "module_id": nmid,
        "module_name": nname,
        "tasks": task_map,
        "completed": False,
        "completed_at": None,
    }
    return doc


def build_current_roadmap(student_id: int, modules: list[dict]) -> list[dict]:
    """供资源计划使用的当前阶段（单条）。"""
    doc = _ensure_doc(student_id, modules)
    current = doc.get("current")
    if not current:
        return []
    stage_no = int(current.get("stage_no") or 1)
    return [
        {
            "stage": stage_no,
            "day": stage_no,
            "module_id": current.get("module_id"),
            "module_name": current.get("module_name"),
            "tasks": _build_stage_tasks(
                int(current["module_id"]),
                current.get("module_name") or "",
                stage_no,
            ),
        }
    ]


def get_roadmap_progress(student_id: int, modules: list[dict]) -> dict:
    doc = _ensure_doc(student_id, modules)
    current = doc.get("current")
    completed_stages = len(doc.get("completed_module_ids") or [])
    history = doc.get("history") or []

    current_out = None
    if current:
        task_defs = _build_stage_tasks(
            int(current["module_id"]),
            current.get("module_name") or "",
            int(current.get("stage_no") or 1),
        )
        task_map = current.get("tasks") or {}
        tasks_out = []
        active_task = None
        completed_count = 0
        for i, t in enumerate(task_defs):
            tid = t.get("id") or ""
            prog = task_map.get(tid) or {"completed": False}
            done = bool(prog.get("completed"))
            if done:
                completed_count += 1
            item = {**t, "completed": done, "order": i + 1}
            tasks_out.append(item)
            if not done and active_task is None:
                active_task = item
        stage_done = _is_stage_complete(task_map, task_defs)
        current_out = {
            "stage": int(current.get("stage_no") or 1),
            "day": int(current.get("stage_no") or 1),
            "module_id": current.get("module_id"),
            "module_name": current.get("module_name"),
            "stage_completed": stage_done,
            "day_completed": stage_done,
            "unlocked": True,
            "tasks": tasks_out,
            "active_task": active_task,
            "tasks_completed_count": completed_count,
            "tasks_total": len(task_defs),
        }

    has_next = _pick_next_module(
        modules,
        set(int(x) for x in doc.get("completed_module_ids") or []),
    ) is not None or (current and not current.get("completed"))

    return {
        "student_id": student_id,
        "completed_stages": completed_stages,
        "completed_days": completed_stages,
        "total_stages": completed_stages + (1 if current_out and not current_out["stage_completed"] else 0),
        "total_days": completed_stages + (1 if current_out else 0),
        "has_next": has_next,
        "current_stage": current_out,
        "current": current_out,
        "days": [current_out] if current_out else [],
        "history": history[-5:],
    }


def update_roadmap_task(
    student_id: int,
    stage: int,
    task_id: str,
    completed: bool,
    modules: list[dict],
    auto: bool = False,
) -> dict:
    if not task_id:
        raise ValueError("缺少 task_id")

    doc = _ensure_doc(student_id, modules)
    current = doc.get("current")
    if not current:
        raise ValueError("当前无进行中的学习任务，请刷新资源计划")

    if int(stage) != int(current.get("stage_no") or 0):
        raise ValueError("任务阶段已更新，请刷新页面")

    tasks = current.setdefault("tasks", {})
    task_defs = _build_stage_tasks(
        int(current["module_id"]),
        current.get("module_name") or "",
        int(current.get("stage_no") or 1),
    )

    if completed:
        expected = _active_task_id(task_defs, tasks)
        if expected and task_id != expected:
            raise ValueError("请按顺序完成当前任务，不要跳过")

    now = datetime.now(timezone.utc).isoformat()
    tasks[task_id] = {
        "completed": bool(completed),
        "completed_at": now if completed else None,
        "auto": auto,
    }

    stage_was_complete = bool(current.get("completed"))
    stage_now_complete = _is_stage_complete(tasks, task_defs)
    current["completed"] = stage_now_complete
    current["completed_at"] = now if stage_now_complete else None
    doc["current"] = current
    doc["updated_at"] = now

    from services.behavior_event_service import record_event

    record_event(
        student_id,
        "roadmap_task",
        "task_complete" if completed else "task_undo",
        {"stage": stage, "task_id": task_id, "auto": auto},
    )

    advanced = False
    if stage_now_complete and not stage_was_complete:
        record_event(
            student_id,
            "roadmap_day_complete",
            "roadmap_progress",
            {
                "stage": stage,
                "module_id": current.get("module_id"),
                "module_name": current.get("module_name"),
            },
        )
        doc = _advance_to_next_stage(doc, modules)
        advanced = True

    _collection().update_one(
        {"student_id": student_id},
        {"$set": doc},
        upsert=True,
    )

    result = get_roadmap_progress(student_id, modules)
    result["advanced"] = advanced
    return result


def refresh_current_stage(student_id: int, modules: list[dict]) -> dict:
    """手动按最新学情刷新当前阶段（仅当当前阶段已全部完成时有效）。"""
    doc = _ensure_doc(student_id, modules)
    current = doc.get("current")
    if current and not current.get("completed"):
        raise ValueError("请先完成当前全部任务，再进入下一阶段")

    if current and current.get("completed"):
        doc = _advance_to_next_stage(doc, modules)
    elif not current:
        doc = _advance_to_next_stage(doc, modules)

    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    _collection().update_one({"student_id": student_id}, {"$set": doc}, upsert=True)
    return get_roadmap_progress(student_id, modules)
