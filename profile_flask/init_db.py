"""初始化知识点树、选择题题库；用法: python init_db.py [--refresh-exercises]"""
import argparse
import logging

from sqlalchemy import text

from app import create_app
from knowledge_data import EXERCISE_BANK, KNOWLEDGE_TREE
from models import AnswerRecord, Exercise, KnowledgePoint, StudentProfile, SubjectModule, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_exercise_columns():
    """为已有库补充选择题字段。"""
    stmts = [
        "ALTER TABLE exercise ADD COLUMN question_type VARCHAR(16) NOT NULL DEFAULT 'choice'",
        "ALTER TABLE exercise ADD COLUMN options JSON NULL",
    ]
    for sql in stmts:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            if "Duplicate column" in str(exc) or "1060" in str(exc):
                continue
            logger.debug("迁移跳过: %s", exc)


def seed(refresh_exercises: bool = False, refresh_all: bool = False):
    app = create_app()
    with app.app_context():
        migrate_exercise_columns()

        if refresh_all:
            # 按外键依赖顺序删除，避免 1451 约束错误
            for table in (AnswerRecord, StudentProfile, Exercise, KnowledgePoint, SubjectModule):
                table.query.delete()
            db.session.commit()
            logger.info("已清空 subject_module / knowledge_points / exercise 及关联记录")

        if refresh_exercises:
            deleted_records = AnswerRecord.query.delete()
            deleted = Exercise.query.delete()
            db.session.commit()
            logger.info("已清空题库，删除答题记录 %s 条、题目 %s 条", deleted_records, deleted)

        for module_name, kp_list in KNOWLEDGE_TREE.items():
            mod = SubjectModule.query.filter_by(module_name=module_name).first()
            if not mod:
                mod = SubjectModule(module_name=module_name)
                db.session.add(mod)
                db.session.flush()

            kp_map = {}
            for kp_name in kp_list:
                kp = KnowledgePoint.query.filter_by(
                    kp_name=kp_name, module_id=mod.module_id
                ).first()
                if not kp:
                    kp = KnowledgePoint(kp_name=kp_name, module_id=mod.module_id)
                    db.session.add(kp)
                    db.session.flush()
                kp_map[kp_name] = kp.kp_id

            bank = EXERCISE_BANK.get(module_name, {})
            for difficulty, questions in bank.items():
                for kp_name, content, options, answer_key in questions:
                    kp_id = kp_map.get(kp_name)
                    if not kp_id:
                        continue
                    exists = Exercise.query.filter_by(
                        kp_id=kp_id, content=content, difficulty=difficulty
                    ).first()
                    if exists:
                        exists.options = options
                        exists.answer = answer_key
                        exists.question_type = "choice"
                        continue
                    db.session.add(
                        Exercise(
                            kp_id=kp_id,
                            content=content,
                            difficulty=difficulty,
                            answer=answer_key,
                            question_type="choice",
                            options=options,
                        )
                    )
        db.session.commit()
        logger.info(
            "种子完成: modules=%s, kps=%s, exercises=%s",
            SubjectModule.query.count(),
            KnowledgePoint.query.count(),
            Exercise.query.count(),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-exercises",
        action="store_true",
        help="清空并重建选择题题库",
    )
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="清空模块/知识点/题库后重建",
    )
    args = parser.parse_args()
    seed(refresh_exercises=args.refresh_exercises or args.refresh_all, refresh_all=args.refresh_all)
