"""将 student_profile 同步到 Spring Boot 使用的 learning_profile 主表。"""
import json
import logging
from datetime import datetime

from sqlalchemy import text

from config import Config
from models import db
from services.dialogue_scripts import PREFERENCE_LABELS
from services.profile_service import get_student_profile

logger = logging.getLogger(__name__)

LEVEL_TO_MASTERY_TAG = {1: "薄弱", 2: "一般", 3: "熟练", 4: "精通"}
MAIN_SUBJECT = "Python程序设计"


def _build_knowledge_base(module_results: list[dict]) -> str:
    parts = []
    for mr in module_results:
        parts.append(
            f"「{mr['module_name']}」：{mr.get('mastery_level', '')}，"
            f"分数 {mr.get('final_score', mr.get('final_level', ''))}，"
            f"校验{'正确' if mr.get('correct_count') else '错误'}"
        )
    return (
        "通过对话式模块自评与分层选择题校验生成。"
        + "；".join(parts)
        + "。各模块等级已同步至下属细分知识点。"
    )


def _load_student_basic_info(student_id: int) -> dict:
    """从 student 表读取个人设置中的基础信息。"""
    row = db.session.execute(
        text(
            "SELECT real_name, grade, major, learn_preferences FROM student "
            "WHERE id = :id AND deleted = 0"
        ),
        {"id": student_id},
    ).fetchone()
    if not row:
        return {}
    prefs_raw = row[3]
    learn_pref = prefs_raw
    if prefs_raw:
        try:
            parsed = json.loads(prefs_raw)
            if isinstance(parsed, list) and parsed:
                learn_pref = "、".join(str(p) for p in parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "real_name": row[0] or "",
        "grade": row[1] or "",
        "major": row[2] or "",
        "learn_preference": learn_pref or "",
        "learn_preferences": prefs_raw or "",
    }


def _merge_basic_info(student_id: int, basic_info: dict | None) -> dict:
    """对话未采集基本信息时，回退到 student 表（个人设置）。"""
    merged = dict(basic_info or {})
    from_student = _load_student_basic_info(student_id)
    for key, val in from_student.items():
        if val and not merged.get(key) and not merged.get(key.replace("_", "")):
            merged[key] = val
    if not merged.get("learn_preference") and merged.get("learn_preferences"):
        try:
            parsed = json.loads(merged["learn_preferences"])
            if isinstance(parsed, list) and parsed:
                merged["learn_preference"] = "、".join(str(p) for p in parsed)
        except (json.JSONDecodeError, TypeError):
            merged["learn_preference"] = merged["learn_preferences"]
    return merged


def _build_profile_tags(basic_info: dict | None) -> tuple[list, list, list]:
    """由对话收集的基本信息生成 base/style/goal 标签。"""
    info = basic_info or {}
    base_tags = []
    if info.get("grade"):
        base_tags.append(info["grade"])
    if info.get("major"):
        base_tags.append(info["major"])

    style_tags = []
    pref = info.get("learn_preference") or info.get("learn_preferences")
    if pref:
        try:
            parsed = json.loads(pref)
            if isinstance(parsed, list):
                style_tags.extend(str(p) for p in parsed if p)
            else:
                style_tags.append(PREFERENCE_LABELS.get(pref, pref))
        except (json.JSONDecodeError, TypeError):
            style_tags.append(PREFERENCE_LABELS.get(pref, pref))

    goal_tags = []
    goal = info.get("learn_goal") or info.get("goal_tag")
    if goal:
        goal_tags.append(goal)

    return base_tags, style_tags, goal_tags


def sync_to_learning_profile(
    student_id: int,
    module_results: list[dict],
    basic_info: dict | None = None,
) -> dict:
    """
    画像构建完成后，写入 learning_profile，供「我的画像」页面读取。
    """
    basic_info = _merge_basic_info(student_id, basic_info)
    items = get_student_profile(student_id)
    if not items:
        logger.warning("student=%s 无 student_profile，跳过 learning_profile 同步", student_id)
        return {"synced": False}

    mastered = [i["kp_name"] for i in items if i["master_level"] >= 3]
    weak = [i["kp_name"] for i in items if i["master_level"] <= 2]
    mastery_tags = [
        {
            "subject": mr["module_name"],
            "level": mr.get("mastery_level")
            or LEVEL_TO_MASTERY_TAG.get(mr.get("final_level", 2), "一般"),
        }
        for mr in module_results
    ]
    knowledge_base = _build_knowledge_base(module_results)
    if basic_info:
        extra = []
        if basic_info.get("grade"):
            extra.append(f"年级：{basic_info['grade']}")
        if basic_info.get("major"):
            extra.append(f"专业：{basic_info['major']}")
        if basic_info.get("learn_goal"):
            extra.append(f"目标：{basic_info['learn_goal']}")
        if extra:
            knowledge_base = "；".join(extra) + "。" + knowledge_base

    raw_payload = {
        "source": "profile_build",
        "basic_info": basic_info or {},
        "module_results": module_results,
        "knowledge_points": items,
    }
    raw_json = json.dumps(raw_payload, ensure_ascii=False)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    base_tags, style_tags, goal_tags = _build_profile_tags(basic_info)

    row = db.session.execute(
        text(
            "SELECT id, version FROM learning_profile "
            "WHERE student_id = :sid AND deleted = 0 "
            "ORDER BY version DESC LIMIT 1"
        ),
        {"sid": student_id},
    ).fetchone()

    params = {
        "kb": knowledge_base,
        "wp": json.dumps(weak, ensure_ascii=False),
        "mp": json.dumps(mastered, ensure_ascii=False),
        "mt": json.dumps(mastery_tags, ensure_ascii=False),
        "raw": raw_json,
        "now": now,
        "grade": (basic_info or {}).get("grade"),
        "major": (basic_info or {}).get("major"),
        "hours": (basic_info or {}).get("daily_study_hours"),
        "pref": (basic_info or {}).get("learn_preference"),
        "goal": (basic_info or {}).get("learn_goal"),
        "base_tags": json.dumps(base_tags, ensure_ascii=False),
        "style_tags": json.dumps(style_tags, ensure_ascii=False),
        "goal_tags": json.dumps(goal_tags, ensure_ascii=False),
    }

    if row:
        db.session.execute(
            text(
                "UPDATE learning_profile SET "
                "main_subject = :subject, knowledge_base = :kb, "
                "weak_points = :wp, mastered_points = :mp, mastery_tags = :mt, "
                "raw_extract_json = :raw, profile_status = 'completed', "
                "grade = :grade, major = :major, "
                "daily_study_hours = :hours, learn_preference = :pref, "
                "learn_goal = :goal, base_tags = :base_tags, "
                "style_tags = :style_tags, goal_tags = :goal_tags, "
                "version = version + 1, updated_at = :now "
                "WHERE id = :id"
            ),
            {**params, "subject": MAIN_SUBJECT, "id": row[0]},
        )
        profile_id = row[0]
    else:
        db.session.execute(
            text(
                "INSERT INTO learning_profile "
                "(student_id, main_subject, grade, major, knowledge_base, weak_points, "
                "mastered_points, mastery_tags, daily_study_hours, learn_preference, "
                "learn_goal, base_tags, style_tags, goal_tags, raw_extract_json, "
                "profile_status, version, deleted, created_at, updated_at) "
                "VALUES (:sid, :subject, :grade, :major, :kb, :wp, :mp, :mt, :hours, :pref, :goal, "
                ":base_tags, :style_tags, :goal_tags, :raw, 'completed', 1, 0, :now, :now)"
            ),
            {**params, "sid": student_id, "subject": MAIN_SUBJECT},
        )
        profile_id = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

    db.session.commit()
    logger.info("learning_profile 已同步 student=%s profile_id=%s", student_id, profile_id)

    try:
        from services.profile_snapshot_service import save_profile_snapshot
        save_profile_snapshot(student_id, module_results)
    except Exception as exc:
        logger.warning("快照保存失败（表可能未迁移）: %s", exc)

    return {
        "synced": True,
        "profile_id": profile_id,
        "mastered_count": len(mastered),
        "weak_count": len(weak),
    }


def sync_mastery_from_student_profile(student_id: int) -> dict:
    """
    日常答疑等动态更新后，将 student_profile 同步至 learning_profile 的
    weak_points / mastered_points / mastery_tags（不覆盖基本信息）。
    """
    items = get_student_profile(student_id)
    if not items:
        return {"synced": False}

    mastered = [i["kp_name"] for i in items if i["master_level"] >= 3]
    weak = [i["kp_name"] for i in items if i["master_level"] <= 2]

    module_levels: dict[int, dict] = {}
    for item in items:
        mid = item["module_id"]
        if mid not in module_levels:
            module_levels[mid] = {
                "name": item["module_name"],
                "levels": [],
            }
        module_levels[mid]["levels"].append(item["master_level"])
    mastery_tags = [
        {
            "subject": module_levels[mid]["name"],
            "level": LEVEL_TO_MASTERY_TAG.get(
                max(1, min(4, round(sum(module_levels[mid]["levels"]) / len(module_levels[mid]["levels"])))),
                "一般",
            ),
        }
        for mid in sorted(module_levels.keys())
    ]

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    row = db.session.execute(
        text(
            "SELECT id FROM learning_profile "
            "WHERE student_id = :sid AND deleted = 0 "
            "ORDER BY version DESC LIMIT 1"
        ),
        {"sid": student_id},
    ).fetchone()
    if not row:
        return {"synced": False}

    db.session.execute(
        text(
            "UPDATE learning_profile SET "
            "weak_points = :wp, mastered_points = :mp, mastery_tags = :mt, "
            "version = version + 1, updated_at = :now "
            "WHERE id = :id"
        ),
        {
            "wp": json.dumps(weak, ensure_ascii=False),
            "mp": json.dumps(mastered, ensure_ascii=False),
            "mt": json.dumps(mastery_tags, ensure_ascii=False),
            "now": now,
            "id": row[0],
        },
    )
    db.session.commit()

    path_sync = {"synced": False}
    try:
        from services.path_sync_client import sync_path_from_profile
        path_sync = sync_path_from_profile(student_id, MAIN_SUBJECT)
    except Exception:
        logger.debug("路径同步跳过", exc_info=True)

    return {
        "synced": True,
        "mastered_count": len(mastered),
        "weak_count": len(weak),
        "path_sync": path_sync,
        "path_sync_recommended": True,
    }


def get_mastery_view(student_id: int) -> dict:
    """按模块分组返回知识点掌握与 0~100 分数（供「我的画像」展示）。"""
    from services.profile_snapshot_service import _load_raw_module_results

    items = get_student_profile(student_id)
    module_meta = {
        int(m["module_id"]): m
        for m in _load_raw_module_results(student_id)
    }

    if not items and not module_meta:
        return {
            "student_id": student_id,
            "has_profile": False,
            "modules": [],
            "summary": {"total_kp": 0, "mastered_count": 0, "weak_count": 0, "module_count": 0},
        }

    modules_map: dict[int, dict] = {}
    for item in items:
        mid = item["module_id"]
        if mid not in modules_map:
            meta = module_meta.get(mid, {})
            modules_map[mid] = {
                "module_id": mid,
                "module_name": item["module_name"],
                "final_level": item["master_level"],
                "final_level_label": Config.LEVEL_LABELS.get(item["master_level"], ""),
                "final_score": meta.get("final_score"),
                "base_score": meta.get("base_score"),
                "quiz_score": meta.get("quiz_score"),
                "mastery_level": meta.get("mastery_level"),
                "tags": meta.get("tags") or {},
                "knowledge_points": [],
            }
        lvl = item["master_level"]
        modules_map[mid]["knowledge_points"].append(
            {
                "kp_id": item["kp_id"],
                "kp_name": item["kp_name"],
                "master_level": lvl,
                "level_label": Config.LEVEL_LABELS.get(lvl, ""),
            }
        )

    if not modules_map and module_meta:
        from models import SubjectModule
        for mid, meta in sorted(module_meta.items(), key=lambda x: x[0]):
            mod = SubjectModule.query.get(mid)
            name = mod.module_name if mod else meta.get("module_name", str(mid))
            modules_map[mid] = {
                "module_id": mid,
                "module_name": name,
                "final_level": meta.get("final_level", 2),
                "final_level_label": Config.LEVEL_LABELS.get(meta.get("final_level", 2), ""),
                "final_score": meta.get("final_score"),
                "base_score": meta.get("base_score"),
                "quiz_score": meta.get("quiz_score"),
                "mastery_level": meta.get("mastery_level"),
                "tags": meta.get("tags") or {},
                "knowledge_points": [],
            }

    modules = sorted(modules_map.values(), key=lambda m: m["module_id"])
    for mod in modules:
        mid = mod["module_id"]
        if mid in module_meta:
            meta = module_meta[mid]
            mod["final_score"] = meta.get("final_score", mod.get("final_score"))
            mod["base_score"] = meta.get("base_score")
            mod["quiz_score"] = meta.get("quiz_score")
            mod["mastery_level"] = meta.get("mastery_level")
            mod["tags"] = meta.get("tags") or mod.get("tags") or {}
        levels = [kp["master_level"] for kp in mod["knowledge_points"]]
        if levels:
            avg = round(sum(levels) / len(levels))
            mod["final_level"] = avg
            mod["final_level_label"] = Config.LEVEL_LABELS.get(avg, "")
        if mod.get("final_score") is None and mod.get("mastery_level"):
            from services.scoring import MASTERY_BASE_SCORE
            mod["final_score"] = MASTERY_BASE_SCORE.get(mod["mastery_level"], 45)

    if items:
        mastered_count = sum(1 for i in items if i["master_level"] >= 3)
        weak_count = sum(1 for i in items if i["master_level"] <= 2)
    else:
        mastered_count = sum(1 for m in modules if (m.get("final_score") or 0) >= 70)
        weak_count = sum(1 for m in modules if (m.get("final_score") or 0) < 45)

    return {
        "student_id": student_id,
        "has_profile": bool(modules),
        "modules": modules,
        "summary": {
            "total_kp": len(items),
            "module_count": len(modules),
            "mastered_count": mastered_count,
            "weak_count": weak_count,
            "avg_score": round(
                sum(m.get("final_score") or 0 for m in modules) / len(modules), 1
            )
            if modules
            else 0,
        },
    }
