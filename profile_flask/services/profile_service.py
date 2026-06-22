"""学生知识点掌握画像读写。"""
from __future__ import annotations

import logging

from config import Config
from models import KnowledgePoint, StudentProfile, SubjectModule, db

logger = logging.getLogger(__name__)


def _clamp_level(level: int) -> int:
    return max(1, min(4, int(level)))


def get_student_profile(student_id: int) -> list[dict]:
    """返回学生全部知识点掌握记录（按模块、知识点排序）。"""
    rows = (
        db.session.query(StudentProfile, KnowledgePoint, SubjectModule)
        .join(KnowledgePoint, StudentProfile.kp_id == KnowledgePoint.kp_id)
        .join(SubjectModule, KnowledgePoint.module_id == SubjectModule.module_id)
        .filter(StudentProfile.student_id == student_id)
        .order_by(SubjectModule.module_id, KnowledgePoint.kp_id)
        .all()
    )
    items = []
    for profile, kp, mod in rows:
        items.append(
            {
                "profile_id": profile.profile_id,
                "student_id": profile.student_id,
                "kp_id": kp.kp_id,
                "kp_name": kp.kp_name,
                "module_id": mod.module_id,
                "module_name": mod.module_name,
                "master_level": profile.master_level,
                "level_label": Config.LEVEL_LABELS.get(profile.master_level, ""),
                "update_time": profile.update_time.isoformat()
                if profile.update_time
                else None,
            }
        )
    return items


def update_knowledge_point_level(
    student_id: int,
    kp_id: int,
    master_level: int,
    reason: str = "",
) -> dict:
    """更新单个知识点掌握等级，不存在则创建。"""
    level = _clamp_level(master_level)
    kp = KnowledgePoint.query.get(kp_id)
    if not kp:
        raise ValueError(f"知识点不存在: {kp_id}")

    row = StudentProfile.query.filter_by(student_id=student_id, kp_id=kp_id).first()
    old_level = row.master_level if row else None

    if row:
        row.master_level = level
    else:
        row = StudentProfile(student_id=student_id, kp_id=kp_id, master_level=level)
        db.session.add(row)

    db.session.flush()

    if old_level != level:
        try:
            from services.profile_snapshot_service import log_profile_change

            log_profile_change(
                student_id,
                f"kp:{kp.kp_name}",
                str(old_level) if old_level is not None else None,
                str(level),
                reason or "manual_update",
            )
        except Exception as exc:
            logger.warning("写入画像变更日志失败: %s", exc)
            db.session.commit()

    db.session.commit()

    mod = SubjectModule.query.get(kp.module_id)
    return {
        "student_id": student_id,
        "kp_id": kp_id,
        "kp_name": kp.kp_name,
        "module_id": kp.module_id,
        "module_name": mod.module_name if mod else "",
        "old_level": old_level,
        "new_level": level,
        "level_label": Config.LEVEL_LABELS.get(level, ""),
        "reason": reason,
    }


def sync_module_level_to_knowledge_points(
    student_id: int,
    module_id: int,
    final_level: int,
) -> int:
    """将模块下全部知识点同步为同一掌握等级，返回更新条数。"""
    level = _clamp_level(final_level)
    kps = KnowledgePoint.query.filter_by(module_id=module_id).all()
    if not kps:
        logger.warning("模块 %s 无知识点，跳过同步", module_id)
        return 0

    synced = 0
    for kp in kps:
        row = StudentProfile.query.filter_by(
            student_id=student_id, kp_id=kp.kp_id
        ).first()
        if row:
            if row.master_level != level:
                row.master_level = level
                synced += 1
        else:
            db.session.add(
                StudentProfile(
                    student_id=student_id,
                    kp_id=kp.kp_id,
                    master_level=level,
                )
            )
            synced += 1

    db.session.commit()
    logger.info(
        "student=%s module=%s 同步知识点等级=%s count=%s",
        student_id,
        module_id,
        level,
        synced,
    )
    return synced
