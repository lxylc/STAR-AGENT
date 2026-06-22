"""0~100 计分与四维标签派生。"""

MASTERY_BASE_SCORE = {
    "精通": 85,
    "熟练": 70,
    "一般": 45,
    "薄弱": 20,
}

LEVEL_TO_MASTERY = {
    4: "精通",
    3: "熟练",
    2: "一般",
    1: "薄弱",
}


def quiz_score_for_answer(is_correct: bool, difficulty: int = 2) -> int:
    """答题得分 0~15；正确时按难度给分。"""
    if not is_correct:
        return 0
    return min(15, 5 + difficulty * 2)


def clamp_score(score: int) -> int:
    return max(0, min(100, int(score)))


def compute_module_final(base_score: int, quiz_score: int) -> int:
    return clamp_score(base_score + quiz_score)


def mastery_label_from_score(final_score: int) -> str:
    if final_score >= 85:
        return "精通"
    if final_score >= 70:
        return "熟练"
    if final_score >= 45:
        return "一般"
    return "薄弱"


def derive_module_tags(assessment: dict, quiz_correct: bool, final_score: int) -> dict:
    """四维标签派生。"""
    weakness = assessment.get("weakness_type") or "无短板"
    if not quiz_correct:
        weakness = "应用薄弱"

    code_tag = assessment.get("code_practice_feel") or "实操困难"
    if not quiz_correct and assessment.get("mastery_level") in ("精通", "熟练"):
        code_tag = "实操困难"

    return {
        "mastery_level": mastery_label_from_score(final_score),
        "weakness_type": weakness,
        "code_practice_feel": code_tag,
        "practice_frequency": assessment.get("practice_frequency") or "偶尔练习",
    }


def build_module_result(assessment: dict, quiz_correct: bool, difficulty: int = 2) -> dict:
    mastery = assessment.get("mastery_level") or "一般"
    base = MASTERY_BASE_SCORE.get(mastery, 45)
    q_score = quiz_score_for_answer(quiz_correct, difficulty)
    final = compute_module_final(base, q_score)
    tags = derive_module_tags(assessment, quiz_correct, final)
    initial_level = assessment.get("initial_level") or 2

    return {
        "module_id": assessment.get("module_id"),
        "module_name": assessment.get("module_name", ""),
        "mastery_level": tags["mastery_level"],
        "initial_level": initial_level,
        "base_score": base,
        "quiz_score": q_score,
        "final_score": final,
        "correct_count": 1 if quiz_correct else 0,
        "final_level": initial_level if quiz_correct else max(1, initial_level - 1),
        "tags": tags,
        "evidence": assessment.get("evidence", ""),
    }
