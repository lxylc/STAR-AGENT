"""画像数据重置（重新构建）。"""
import logging
from datetime import datetime

from sqlalchemy import text

from models import StudentProfile, db
from services.qa_service import clear_qa_history

logger = logging.getLogger(__name__)


def reset_profile_data(student_id: int) -> dict:
    """
    清空知识点掌握画像及全部基本信息，并将 learning_profile 重置为待构建状态。
    Mongo 对话保留历史，由新 session 隔离。
    """
    kp_deleted = StudentProfile.query.filter_by(student_id=student_id).delete()
    # 答题记录保留作审计；若需一并清空可取消下行注释
    # AnswerRecord.query.filter_by(student_id=student_id).delete()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    row = db.session.execute(
        text(
            "SELECT id FROM learning_profile WHERE student_id = :sid AND deleted = 0 "
            "ORDER BY version DESC LIMIT 1"
        ),
        {"sid": student_id},
    ).fetchone()

    if row:
        db.session.execute(
            text(
                "UPDATE learning_profile SET "
                "grade = NULL, major = NULL, main_subject = NULL, "
                "daily_study_hours = NULL, learn_preference = NULL, learn_goal = NULL, "
                "base_tags = :empty, style_tags = :empty, goal_tags = :empty, behavior_tags = :empty, "
                "knowledge_base = NULL, weak_points = :empty, mastered_points = :empty, "
                "mastery_tags = :empty, raw_extract_json = NULL, profile_status = 'draft', "
                "version = version + 1, updated_at = :now "
                "WHERE id = :id"
            ),
            {"empty": "[]", "now": now, "id": row[0]},
        )

    db.session.commit()
    clear_qa_history(student_id)
    logger.info("画像已重置 student=%s kp_rows=%s", student_id, kp_deleted)
    return {"student_id": student_id, "cleared_kp_rows": kp_deleted, "reset": True}
