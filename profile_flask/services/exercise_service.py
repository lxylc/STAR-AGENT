"""出题与答题业务（选择题）。"""
import logging
import random

from models import AnswerRecord, Exercise, KnowledgePoint, SubjectModule, db
from services.learning_profile_sync import sync_to_learning_profile
from services.profile_service import sync_module_level_to_knowledge_points
from services.scoring import build_module_result

logger = logging.getLogger(__name__)


def parse_level(choice: str) -> int:
    """将 A/B/C/D 或数字转为 1-4 等级。"""
    from config import Config

    c = (choice or "").strip().upper()
    if c in Config.LEVEL_OPTIONS:
        return Config.LEVEL_OPTIONS[c]
    try:
        n = int(c)
        if 1 <= n <= 4:
            return n
    except ValueError:
        pass
    if c in Config.MASTERY_TO_LEVEL:
        return Config.MASTERY_TO_LEVEL[c]
    raise ValueError(f"无效等级选项: {choice}")


def exercise_to_dto(ex: Exercise, module_id: int, module_name: str, kp_name: str, initial: int) -> dict:
    return {
        "ex_id": ex.ex_id,
        "module_id": module_id,
        "module_name": module_name,
        "kp_id": ex.kp_id,
        "kp_name": kp_name,
        "content": ex.content,
        "difficulty": ex.difficulty,
        "initial_level": initial,
        "question_type": ex.question_type or "choice",
        "options": ex.options_dict(),
    }


def judge_choice_answer(ex: Exercise, user_answer: str) -> bool:
    ua = (user_answer or "").strip().upper()
    correct = (ex.answer or "").strip().upper()
    if not ua or not correct:
        return False
    return ua[0] == correct[0]


def _initial_level(item: dict) -> int:
    if "initial_level" in item:
        return int(item["initial_level"])
    if "mastery_level" in item:
        from config import Config
        return Config.MASTERY_TO_LEVEL.get(item["mastery_level"], 2)
    return parse_level(item.get("choice", "B"))


def draw_exercises_for_modules(assessments: list[dict]) -> list[dict]:
    """每模块固定 1 题，共 12 题；高掌握→综合题(难度3-4)，低掌握→基础题(1-2)。"""
    exercises_out = []
    for item in assessments:
        module_id = int(item["module_id"])
        initial = _initial_level(item)
        target_diff = 4 if initial >= 4 else 3 if initial == 3 else 2 if initial == 2 else 1

        kp_ids = [r.kp_id for r in KnowledgePoint.query.filter_by(module_id=module_id).all()]
        if not kp_ids:
            logger.warning("模块 %s 无知识点", module_id)
            continue

        pool = Exercise.query.filter(
            Exercise.kp_id.in_(kp_ids), Exercise.difficulty == target_diff
        ).all()
        if not pool:
            pool = Exercise.query.filter(Exercise.kp_id.in_(kp_ids)).all()
        if not pool:
            continue

        ex = random.choice(pool)
        mod = SubjectModule.query.get(module_id)
        kp = KnowledgePoint.query.get(ex.kp_id)
        exercises_out.append(
            exercise_to_dto(
                ex,
                module_id,
                mod.module_name if mod else "",
                kp.kp_name if kp else "",
                initial,
            )
        )
    return exercises_out


def submit_and_build_profile(student_id: int, payload: dict) -> dict:
    """提交答案 → 0~100 计分 → 画像入库。"""
    from services.behavior_event_service import record_event
    assessments = payload.get("module_assessments") or []
    answers = payload.get("answers") or []

    assess_by_module = {int(a["module_id"]): a for a in assessments}
    module_quiz_result: dict[int, bool] = {mid: False for mid in assess_by_module}
    judge_details = []

    for ans in answers:
        ex_id = int(ans["ex_id"])
        user_answer = (ans.get("user_answer") or ans.get("choice") or "").strip()
        ex = Exercise.query.get(ex_id)
        if not ex:
            continue

        kp = KnowledgePoint.query.get(ex.kp_id)
        module_id = kp.module_id if kp else None
        is_correct = judge_choice_answer(ex, user_answer)

        db.session.add(
            AnswerRecord(
                student_id=student_id,
                ex_id=ex_id,
                user_answer=user_answer.upper()[:1] if user_answer else "",
                judge_result=1 if is_correct else 0,
            )
        )
        if module_id is not None:
            module_quiz_result[module_id] = is_correct

        judge_details.append(
            {
                "ex_id": ex_id,
                "module_id": module_id,
                "user_answer": user_answer,
                "correct_answer": ex.answer,
                "judge_result": 1 if is_correct else 0,
                "judge_label": "正确" if is_correct else "错误",
            }
        )

    db.session.commit()

    module_results = []
    total_synced = 0
    for module_id, assessment in assess_by_module.items():
        quiz_correct = module_quiz_result.get(module_id, False)
        difficulty = 3 if assessment.get("initial_level", 2) >= 3 else 2
        result = build_module_result(assessment, quiz_correct, difficulty)
        synced = sync_module_level_to_knowledge_points(
            student_id, module_id, result["final_level"]
        )
        total_synced += synced
        module_results.append({**result, "synced_kp_count": synced})

    lp_sync = sync_to_learning_profile(
        student_id,
        module_results,
        payload.get("basic_info"),
    )
    record_event(
        student_id,
        "quiz_submit",
        "profile_build",
        {"module_count": len(module_results), "answer_count": len(answers)},
    )
    record_event(student_id, "profile_complete", "profile_build", {"modules": len(module_results)})

    return {
        "student_id": student_id,
        "module_results": module_results,
        "judge_details": judge_details,
        "total_synced_kp": total_synced,
        "learning_profile_sync": lp_sync,
        "message": "学习画像已生成并同步至「我的画像」",
    }
