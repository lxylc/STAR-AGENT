"""代码案例实操：运行、验收判题、提交回写画像。"""
from __future__ import annotations

import logging

from models import SubjectModule
from services.code_run_service import execute_python_code_interactive
from services.module_practice_service import apply_single_coding_practice
from services.practice_judge_service import judge_coding_answer, run_coding_tests_detailed
from services.resource_content_builder import get_coding_challenge, parse_test_cases_from_markdown

logger = logging.getLogger(__name__)


def _resolve_challenge(module_id: int | None, module_name: str | None, content: str | None) -> dict:
    mid = int(module_id or 0)
    name = (module_name or "").strip()
    if mid:
        mod = SubjectModule.query.get(mid)
        if mod and not name:
            name = mod.module_name
    challenge = get_coding_challenge(name, mid) if name else None
    parsed_cases = parse_test_cases_from_markdown(content or "")
    if challenge:
        cases = challenge.get("test_cases") or []
        if not cases and parsed_cases:
            challenge = {**challenge, "test_cases": parsed_cases}
        return challenge
    return {
        "content": "完成代码实操练习",
        "answer": "",
        "test_cases": parsed_cases,
        "analysis": "根据题目要求实现并通过全部验收用例。",
    }


def check_code_practice(
    student_id: int,
    code: str,
    module_id: int | None = None,
    module_name: str | None = None,
    content: str | None = None,
    resource_id: str | None = None,
) -> dict:
    challenge = _resolve_challenge(module_id, module_name, content)
    run_result = execute_python_code_interactive(code)
    check_result = run_coding_tests_detailed(code, challenge.get("test_cases"))
    all_passed = check_result.get("all_passed")
    return {
        "student_id": student_id,
        "resource_id": resource_id,
        "module_id": module_id,
        "question": challenge.get("content") or "",
        "run": run_result,
        "check": check_result,
        "passed": bool(all_passed) if all_passed is not None else run_result.get("ok"),
        "can_submit": bool(all_passed),
        "message": check_result.get("summary") or (
            "代码可运行，但未配置验收用例" if run_result.get("ok") else run_result.get("error")
        ),
    }


def submit_code_practice(
    student_id: int,
    code: str,
    module_id: int | None = None,
    module_name: str | None = None,
    content: str | None = None,
    resource_id: str | None = None,
) -> dict:
    challenge = _resolve_challenge(module_id, module_name, content)
    test_cases = challenge.get("test_cases") or []
    outcome = judge_coding_answer(
        challenge.get("content") or "",
        challenge.get("answer") or "",
        code,
        test_cases,
    )
    check_result = run_coding_tests_detailed(code, test_cases)

    if not outcome.is_correct:
        from services.behavior_event_service import record_event

        record_event(
            student_id,
            "code_practice",
            "code_submit_fail",
            {
                "resource_id": resource_id,
                "module_id": module_id,
                "reason": outcome.reason,
                "passed_cases": sum(1 for c in check_result.get("cases") or [] if c.get("passed")),
                "total_cases": len(check_result.get("cases") or []),
            },
        )
        return {
            "ok": False,
            "student_id": student_id,
            "resource_id": resource_id,
            "module_id": module_id,
            "check": check_result,
            "judge_label": "未通过",
            "judge_reason": outcome.reason,
            "message": outcome.reason or "代码未通过验收，请修改后重试",
        }

    profile_update = {}
    if module_id:
        profile_update = apply_single_coding_practice(student_id, int(module_id))

    from services.behavior_event_service import record_event

    record_event(
        student_id,
        "code_practice",
        "code_submit_pass",
        {
            "resource_id": resource_id,
            "module_id": module_id,
            "judge_reason": outcome.reason,
            **profile_update,
        },
    )

    delta = profile_update.get("score_delta")
    new_score = profile_update.get("new_score")
    module_label = module_name or profile_update.get("module_name") or "本模块"
    msg = f"恭喜！「{module_label}」代码实操验收通过"
    if delta is not None and delta > 0:
        msg += f"，模块掌握度 +{delta} 分（当前 {new_score} 分）"
    elif new_score is not None:
        msg += f"（当前 {new_score} 分）"

    return {
        "ok": True,
        "student_id": student_id,
        "resource_id": resource_id,
        "module_id": module_id,
        "check": check_result,
        "judge_label": "通过",
        "judge_reason": outcome.reason,
        "profile_update": profile_update,
        "message": msg,
    }
