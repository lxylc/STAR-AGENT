"""对话式学习画像 — 分步状态机（内嵌选择题，逐轮推进）。"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from config import Config
from services.dialogue_scripts import (
    ASSESS_OFF_TOPIC,
    ASSESS_RECORDED,
    ASSESS_TOO_SHORT,
    ASSESS_WEAK_HINT,
    MODULE_ASSESS_DONE,
    MODULE_ASSESS_GLOBAL,
    QUIZ_DONE,
    QUIZ_INTRO,
    QUIZ_NEXT,
    SPARK_FALLBACK,
    WELCOME,
    level_options_dto,
    module_assess_prompt,
    quiz_feedback,
    quiz_question_prompt,
)
from services.spark_extract import default_assessment_fallback, extract_module_assessment
from services.dialogue_service import (
    append_message,
    list_messages,
    mark_choice_card_submitted,
    record_build_result,
)
from services.exercise_service import (
    draw_exercises_for_modules,
    parse_level,
    submit_and_build_profile,
)
from services.mongo_client import get_db, ensure_indexes

logger = logging.getLogger(__name__)

SESSION_COL = "profile_dialogue_session"


def _sessions():
    return get_db()[SESSION_COL]


def _ensure_session_indexes():
    ensure_indexes()
    col = _sessions()
    col.create_index("session_id", unique=True)
    col.create_index([("student_id", 1), ("created_at", -1)])


def get_session(session_id: str) -> dict | None:
    doc = _sessions().find_one({"session_id": session_id})
    if doc:
        doc.pop("_id", None)
    return doc


def save_session(state: dict) -> None:
    _ensure_session_indexes()
    state["updated_at"] = _utc_now()
    _sessions().update_one(
        {"session_id": state["session_id"]},
        {"$set": state},
        upsert=True,
    )


def get_active_session_for_student(student_id: int) -> dict | None:
    """返回该学生未完成的最新构建会话（用于恢复进度）。"""
    _ensure_session_indexes()
    doc = _sessions().find_one(
        {"student_id": student_id, "step": {"$ne": "done"}, "abandoned": {"$ne": True}},
        sort=[("updated_at", -1), ("created_at", -1)],
    )
    if doc:
        doc.pop("_id", None)
    return doc


def abandon_active_sessions(student_id: int) -> int:
    """放弃进行中的会话（重新构建前调用）。"""
    _ensure_session_indexes()
    result = _sessions().update_many(
        {"student_id": student_id, "step": {"$ne": "done"}},
        {"$set": {"step": "done", "abandoned": True, "updated_at": _utc_now()}},
    )
    return result.modified_count


def compute_phase(step: str) -> str:
    if step == "done":
        return "done"
    if step == "welcome":
        return "welcome"
    if step in (
        "basic_grade",
        "basic_major",
        "basic_hours",
        "basic_preference",
        "basic_goal",
    ):
        return "basic"
    if step == "assess_module":
        return "assess"
    if step == "quiz":
        return "quiz"
    return "welcome"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_context(state: dict, round_type: str, **fields) -> None:
    """记录每轮对话选择与结果，供会话恢复与审计。"""
    entry = {
        "round": len(state.get("context_log", [])) + 1,
        "type": round_type,
        "step": state.get("step"),
        "at": _utc_now(),
        **fields,
    }
    state.setdefault("context_log", []).append(entry)
    save_session(state)


def _response(state: dict) -> dict:
    sid = state["session_id"]
    student_id = state["student_id"]
    step = state["step"]
    phase = compute_phase(step)
    resp = {
        "student_id": student_id,
        "session_id": sid,
        "phase": phase,
        "step": step,
        "context_log": state.get("context_log", []),
        "messages": list_messages(student_id, sid),
        "expects_text": bool(state.get("expects_text")),
    }
    if step == "assess_module":
        resp["module_index"] = state.get("assess_index", 0)
        resp["total_modules"] = len(state.get("modules") or [])
    if step == "quiz":
        qi = len([c for c in state.get("context_log", []) if c.get("type") == "quiz_answer"])
        resp["quiz_index"] = qi
        resp["quiz_total"] = len(state.get("exercises") or [])
    return resp


def _append_choice_card(
    student_id: int,
    session_id: str,
    content: str,
    step_key: str,
    options: list[dict],
    extra: dict | None = None,
) -> None:
    payload = {
        "submitted": False,
        "step_key": step_key,
        "options": options,
        **(extra or {}),
    }
    append_message(
        student_id,
        "assistant",
        "choice_card",
        content,
        payload=payload,
        session_id=session_id,
    )


def _user_choice_bubble(student_id: int, session_id: str, text: str) -> None:
    append_message(student_id, "user", "text", text, session_id=session_id)


def resume_or_init_conversational_dialogue(
    student_id: int,
    modules: list,
    level_options: list | None = None,
    basic_defaults: dict | None = None,
) -> dict:
    """有未完成会话则恢复，否则新建欢迎对话。"""
    active = get_active_session_for_student(student_id)
    if active:
        return {**_response(active), "resumed": True}
    return init_conversational_dialogue(
        student_id, modules, level_options, basic_defaults
    )


def init_conversational_dialogue(
    student_id: int,
    modules: list,
    level_options: list | None = None,
    basic_defaults: dict | None = None,
) -> dict:
    """初始化：欢迎语 + 开始按钮。"""
    _ensure_session_indexes()
    session_id = f"{student_id}-{uuid4().hex[:8]}"
    now = _utc_now()
    defaults = basic_defaults or {}
    level_opts = level_options or level_options_dto()

    state = {
        "session_id": session_id,
        "student_id": student_id,
        "step": "welcome",
        "modules": modules,
        "level_options": level_opts,
        "basic_info": {
            "grade": defaults.get("grade", ""),
            "major": defaults.get("major", ""),
            "daily_study_hours": defaults.get("daily_study_hours"),
            "learn_preference": defaults.get("learn_preference", ""),
            "learn_goal": defaults.get("learn_goal", ""),
        },
        "assessments": [],
        "exercises": [],
        "answers": [],
        "assess_index": 0,
        "quiz_index": 0,
        "assess_retry": 0,
        "expects_text": False,
        "context_log": [],
        "created_at": now,
        "updated_at": now,
    }
    save_session(state)
    _log_context(state, "session_start", action="init")

    append_message(student_id, "assistant", "text", WELCOME, session_id=session_id)
    _append_choice_card(
        student_id,
        session_id,
        "准备好了吗？点击开始吧～",
        "welcome_start",
        [{"value": "start", "label": "好的，开始吧"}],
    )
    return _response(state)


def _finish_assess_and_start_quiz(state: dict) -> dict:
    sid = state["session_id"]
    student_id = state["student_id"]
    state["step"] = "quiz"
    state["quiz_index"] = 0
    state["exercises"] = draw_exercises_for_modules(state["assessments"])
    state["answers"] = []
    save_session(state)

    append_message(
        student_id, "assistant", "text", MODULE_ASSESS_DONE, session_id=sid
    )
    append_message(student_id, "assistant", "text", QUIZ_INTRO, session_id=sid)
    return _append_quiz_card(state)


def _append_quiz_card(state: dict) -> dict:
    sid = state["session_id"]
    student_id = state["student_id"]
    idx = state["quiz_index"]
    exercises = state["exercises"]
    if idx >= len(exercises):
        return _finalize_profile(state)

    ex = exercises[idx]
    prompt = quiz_question_prompt(idx + 1, ex["content"], ex.get("module_name", ""))
    _append_choice_card(
        student_id,
        sid,
        prompt,
        "quiz_answer",
        [
            {"value": k, "label": f"{k}. {label}"}
            for k, label in (ex.get("options") or {}).items()
        ],
        extra={
            "quiz_index": idx,
            "exercise": ex,
        },
    )
    return _response(state)


def _after_quiz_answer(state: dict, choice: str) -> dict:
    sid = state["session_id"]
    student_id = state["student_id"]
    idx = state["quiz_index"]
    ex = state["exercises"][idx]
    choice = choice.upper()

    mark_choice_card_submitted(student_id, sid, choice)
    _user_choice_bubble(student_id, sid, f"我选择：{choice}")

    state["answers"].append(
        {
            "ex_id": ex["ex_id"],
            "choice": choice,
            "user_answer": choice,
        }
    )
    _log_context(
        state,
        "quiz_answer",
        ex_id=ex["ex_id"],
        module_name=ex.get("module_name"),
        choice=choice,
        quiz_index=idx,
    )

    state["quiz_index"] = idx + 1
    save_session(state)

    if state["quiz_index"] < len(state["exercises"]):
        append_message(
            student_id, "assistant", "text", QUIZ_NEXT, session_id=sid
        )
        return _append_quiz_card(state)
    return _finalize_profile(state)


def _finalize_profile(state: dict) -> dict:
    sid = state["session_id"]
    student_id = state["student_id"]
    state["step"] = "done"
    save_session(state)

    payload = {
        "student_id": student_id,
        "module_assessments": state["assessments"],
        "answers": state["answers"],
        "basic_info": state["basic_info"],
    }
    result = submit_and_build_profile(student_id, payload)

    append_message(student_id, "assistant", "text", QUIZ_DONE, session_id=sid)
    record_build_result(
        student_id,
        sid,
        result["module_results"],
        result["message"],
    )
    _log_context(
        state,
        "profile_done",
        module_results=result["module_results"],
        judge_count=len(result.get("judge_details", [])),
    )
    return {
        **_response(state),
        "module_results": result["module_results"],
        "message": result["message"],
    }


def process_dialogue_step(
    student_id: int, session_id: str, value: str
) -> dict:
    """处理用户一次选择（点击选项）。"""
    state = get_session(session_id)
    if not state:
        raise ValueError("会话不存在或已过期，请重新开始")
    if state["student_id"] != student_id:
        raise ValueError("学生会话不匹配")

    step = state["step"]
    val = (value or "").strip()

    if step == "welcome":
        if val != "start":
            raise ValueError("请点击「好的，开始吧」")
        mark_choice_card_submitted(student_id, session_id, val)
        _user_choice_bubble(student_id, session_id, "好的，开始吧！")
        _log_context(state, "welcome_start", action="start")
        return _start_assess(state)

    if step == "quiz":
        opts = (state["exercises"][state["quiz_index"]].get("options") or {}).keys()
        if val.upper() not in [k.upper() for k in opts]:
            raise ValueError("请选择有效答案")
        return _after_quiz_answer(state, val)

    if step == "done":
        return _response(state)

    raise ValueError(f"当前步骤无法提交: {step}")


def _start_assess(state: dict) -> dict:
    """跳过聊天内基本信息，直接进入自由文本自评。"""
    sid = state["session_id"]
    student_id = state["student_id"]
    state["assess_index"] = 0
    state["step"] = "assess_module"
    state["assess_retry"] = 0
    save_session(state)
    append_message(student_id, "assistant", "text", MODULE_ASSESS_GLOBAL, session_id=sid)
    return _append_module_assess_prompt(state)


def _append_module_assess_prompt(state: dict) -> dict:
    sid = state["session_id"]
    student_id = state["student_id"]
    idx = state["assess_index"]
    modules = state["modules"]
    if idx >= len(modules):
        return _finish_assess_and_start_quiz(state)

    mod = modules[idx]
    mod_name = mod["module_name"]
    prompt = module_assess_prompt(mod_name)
    append_message(
        student_id,
        "assistant",
        "text",
        prompt,
        session_id=sid,
        payload={"module_index": idx, "module_id": mod["module_id"], "module_name": mod_name, "expects_text": True},
    )
    state["expects_text"] = True
    save_session(state)
    return {**_response(state), "expects_text": True, "module_index": idx, "total_modules": len(modules)}


def process_dialogue_text(student_id: int, session_id: str, text: str) -> dict:
    """处理自由文本自评。"""
    state = get_session(session_id)
    if not state:
        raise ValueError("会话不存在或已过期，请重新开始")
    if state["student_id"] != student_id:
        raise ValueError("学生会话不匹配")
    if state["step"] != "assess_module":
        raise ValueError("当前阶段不需要文本自评")

    sid = state["session_id"]
    idx = state["assess_index"]
    mod = state["modules"][idx]
    mod_id = mod["module_id"]
    mod_name = mod["module_name"]
    cleaned = (text or "").strip()

    append_message(student_id, "user", "text", cleaned, session_id=sid)

    if not cleaned:
        append_message(student_id, "assistant", "text", ASSESS_TOO_SHORT, session_id=sid)
        return {**_response(state), "expects_text": True, "retry": True}

    result = extract_module_assessment(mod_id, mod_name, cleaned)
    if not result.get("valid"):
        reason = result.get("reason") or "too_vague"
        if reason in ("spark_error", "parse_error"):
            state["assess_retry"] = state.get("assess_retry", 0) + 1
            if state["assess_retry"] >= 2:
                append_message(student_id, "assistant", "text", SPARK_FALLBACK, session_id=sid)
                data = default_assessment_fallback(mod_id, mod_name)
                data["free_text"] = cleaned
                state["assessments"].append(data)
                _log_context(
                    state,
                    "module_assess_text",
                    module_id=mod_id,
                    module_name=mod_name,
                    mastery_level=data.get("mastery_level"),
                    extract_reason="spark_default",
                )
                append_message(student_id, "assistant", "text", ASSESS_RECORDED, session_id=sid)
                state["assess_index"] = idx + 1
                state["assess_retry"] = 0
                state["expects_text"] = False
                save_session(state)
                if state["assess_index"] >= len(state["modules"]):
                    return _finish_assess_and_start_quiz(state)
                return _append_module_assess_prompt(state)
            append_message(student_id, "assistant", "text", SPARK_FALLBACK, session_id=sid)
            save_session(state)
            return {**_response(state), "expects_text": True, "retry": True}

        state["assess_retry"] = state.get("assess_retry", 0) + 1
        if reason == "off_topic":
            hint = result.get("reject_hint") or ASSESS_OFF_TOPIC
        else:
            hint = result.get("reject_hint") or ASSESS_TOO_SHORT
        append_message(student_id, "assistant", "text", hint, session_id=sid)
        save_session(state)
        return {**_response(state), "expects_text": True, "retry": True}

    data = result["data"]
    data["free_text"] = cleaned
    state["assessments"].append(data)
    _log_context(
        state,
        "module_assess_text",
        module_id=mod_id,
        module_name=mod_name,
        mastery_level=data.get("mastery_level"),
        extract_reason=result.get("reason"),
    )
    append_message(student_id, "assistant", "text", ASSESS_RECORDED, session_id=sid)

    state["assess_index"] = idx + 1
    state["assess_retry"] = 0
    state["expects_text"] = False
    save_session(state)

    if state["assess_index"] >= len(state["modules"]):
        return _finish_assess_and_start_quiz(state)
    return _append_module_assess_prompt(state)
