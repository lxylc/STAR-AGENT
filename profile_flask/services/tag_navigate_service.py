"""学情标签跳转：解析模块/知识点并返回学习资源、训练题与前端路由。"""
from __future__ import annotations

import logging
from urllib.parse import urlencode

from sqlalchemy import text

from config import Config
from models import Exercise, KnowledgePoint, StudentProfile, SubjectModule, db

logger = logging.getLogger(__name__)

TAG_TYPES = frozenset({"weakness", "code", "practice"})
SUBJECT = "Python程序设计"
MAX_RESOURCES = 20
MAX_EXERCISES = 10


def _pick_primary_kp(module_id: int, student_id: int) -> tuple[KnowledgePoint | None, int]:
    kps = (
        KnowledgePoint.query.filter_by(module_id=module_id)
        .order_by(KnowledgePoint.kp_id)
        .all()
    )
    if not kps:
        return None, 1

    kp_ids = [k.kp_id for k in kps]
    profiles = {
        row.kp_id: row.master_level
        for row in StudentProfile.query.filter(
            StudentProfile.student_id == student_id,
            StudentProfile.kp_id.in_(kp_ids),
        ).all()
    }
    kps.sort(key=lambda k: (profiles.get(k.kp_id, 1), k.kp_id))
    kp = kps[0]
    return kp, profiles.get(kp.kp_id, 1)


def _fetch_learning_resources(student_id: int, kp_name: str, tag_type: str) -> list[dict]:
    type_pref = None
    if tag_type == "weakness":
        type_pref = "lecture"
    elif tag_type == "code":
        type_pref = "courseware"

    try:
        rows = db.session.execute(
            text(
                "SELECT id, resource_type, title, knowledge_point, subject, created_at "
                "FROM learning_resource "
                "WHERE student_id = :sid AND deleted = 0 "
                "AND subject = :subject "
                "AND (knowledge_point = :kp OR knowledge_point LIKE :kp_like "
                "     OR :kp LIKE CONCAT('%', knowledge_point, '%')) "
                "ORDER BY created_at DESC LIMIT :lim"
            ),
            {
                "sid": student_id,
                "subject": SUBJECT,
                "kp": kp_name,
                "kp_like": f"%{kp_name}%",
                "lim": MAX_RESOURCES,
            },
        ).fetchall()
    except Exception as exc:
        logger.warning("查询 learning_resource 失败: %s", exc)
        return []

    items = []
    for row in rows:
        items.append(
            {
                "id": row[0],
                "resource_type": row[1],
                "title": row[2],
                "knowledge_point": row[3],
                "subject": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
            }
        )

    if type_pref:
        preferred = [r for r in items if r["resource_type"] == type_pref]
        others = [r for r in items if r["resource_type"] != type_pref]
        return preferred + others
    return items


def _fetch_training_exercises(
    module_id: int, kp_id: int, tag_type: str, master_level: int
) -> list[dict]:
    if tag_type == "practice":
        target_diffs = [1, 2] if master_level <= 2 else [2, 3]
    elif tag_type == "code":
        target_diffs = [2, 3, 4]
    else:
        target_diffs = [1, 2]

    pool = (
        Exercise.query.filter(
            Exercise.kp_id == kp_id, Exercise.difficulty.in_(target_diffs)
        )
        .limit(MAX_EXERCISES)
        .all()
    )
    if not pool:
        pool = Exercise.query.filter_by(kp_id=kp_id).limit(MAX_EXERCISES).all()
    if not pool:
        pool = (
            Exercise.query.join(KnowledgePoint, Exercise.kp_id == KnowledgePoint.kp_id)
            .filter(KnowledgePoint.module_id == module_id)
            .limit(MAX_EXERCISES)
            .all()
        )

    mod = SubjectModule.query.get(module_id)
    mod_name = mod.module_name if mod else ""
    out = []
    for ex in pool:
        kp = KnowledgePoint.query.get(ex.kp_id)
        out.append(
            {
                "ex_id": ex.ex_id,
                "kp_id": ex.kp_id,
                "kp_name": kp.kp_name if kp else "",
                "module_id": module_id,
                "module_name": mod_name,
                "content": ex.content,
                "difficulty": ex.difficulty,
                "question_type": ex.question_type or "choice",
                "options": ex.options_dict(),
            }
        )
    return out


def _build_query(
    student_id: int,
    module_id: int,
    kp_id: int,
    tag_type: str,
    tag_content: str,
) -> str:
    return urlencode(
        {
            "studentId": student_id,
            "moduleId": module_id,
            "kpId": kp_id,
            "tagType": tag_type,
            "tagContent": tag_content,
        }
    )


def resolve_tag_navigation(
    student_id: int,
    tag_type: str,
    tag_content: str,
    module_id: int | None,
) -> dict:
    tag_type = (tag_type or "").strip().lower()
    tag_content = (tag_content or "").strip()
    if tag_type not in TAG_TYPES:
        raise ValueError(f"无效标签类型: {tag_type}")
    if not tag_content:
        raise ValueError("标签内容不能为空")
    if module_id is None:
        raise ValueError("缺少关联模块 ID，无法跳转")

    module_id = int(module_id)
    mod = SubjectModule.query.get(module_id)
    if not mod:
        raise ValueError(f"模块不存在: {module_id}")

    kp, master_level = _pick_primary_kp(module_id, student_id)
    if not kp:
        raise ValueError(f"模块「{mod.module_name}」暂无知识点数据")

    learning_resources = _fetch_learning_resources(student_id, kp.kp_name, tag_type)
    training_exercises = _fetch_training_exercises(
        module_id, kp.kp_id, tag_type, master_level
    )

    q = _build_query(student_id, module_id, kp.kp_id, tag_type, tag_content)
    tutorial_route = f"/learn/zone?{q}"
    practice_route = (
        f"/learn/exercise-center?studentId={student_id}&moduleId={module_id}"
        f"&mode=special&tagType={tag_type}&tagContent={tag_content}"
    )
    module_practice_route = f"/learn/exercise-center?studentId={student_id}&moduleId={module_id}&mode=module"
    route_path = practice_route

    return {
        "student_id": student_id,
        "tag_type": tag_type,
        "tag_content": tag_content,
        "module_id": module_id,
        "module_name": mod.module_name,
        "kp_id": kp.kp_id,
        "kp_name": kp.kp_name,
        "course_id": Config.COURSE_ID,
        "learning_resources": learning_resources,
        "training_exercises": training_exercises,
        "route_path": route_path,
        "tutorial_route": tutorial_route,
        "practice_route": practice_route,
        "module_practice_route": module_practice_route,
    }
