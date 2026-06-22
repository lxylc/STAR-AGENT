"""画像自主构建 + MongoDB 对话 API。"""
import logging

from flask import Blueprint, jsonify, request

from config import Config
from models import SubjectModule, db
from services.dialogue_flow_service import (
    abandon_active_sessions,
    compute_phase,
    get_active_session_for_student,
    get_session,
    init_conversational_dialogue,
    process_dialogue_step,
    process_dialogue_text,
    resume_or_init_conversational_dialogue,
)
from services.dialogue_service import (
    DialogueStoreError,
    append_module_assess_card,
    list_messages,
    record_assess_submit,
    record_basic_info_submit,
    record_build_result,
    record_quiz_batch,
    record_quiz_submit,
)
from services.exercise_service import draw_exercises_for_modules, parse_level, submit_and_build_profile
from services.learning_profile_sync import get_mastery_view
from services.mongo_client import ensure_indexes
from services.profile_reset_service import reset_profile_data
from services.profile_service import get_student_profile, update_knowledge_point_level
from services.qa_service import ask_question, get_qa_history, init_qa_dialogue
from services.tutoring_service import (
    ask_tutoring,
    create_tutoring_session,
    get_tutoring_history,
    init_tutoring,
    validate_tutoring_session_id,
)
from services.media_generation_service import generate_tutoring_media
from services.behavior_event_service import record_event
from services.evaluation_service import (
    collect_metrics,
    generate_evaluation,
    get_evaluation_detail,
    list_evaluations,
)
from services.tag_navigate_service import resolve_tag_navigation
from services.module_practice_service import generate_practice_set, submit_practice
from services.exercise_center_service import (
    generate_exercise_session,
    get_center_overview,
    submit_exercise_session,
)
from services.roadmap_progress_service import (
    get_roadmap_progress,
    refresh_current_stage,
    update_roadmap_task,
)
from services.resource_progress_service import get_resource_status_map, mark_resource_status
from services.code_run_service import execute_python_code_interactive
from services.code_practice_service import check_code_practice, submit_code_practice
from services.learning_history_service import get_learning_history
from services.wrong_question_service import list_wrong_questions, mark_wrong_reviewed

logger = logging.getLogger(__name__)

bp = Blueprint("profile_build", __name__, url_prefix="/api/profile-build")


def _module_options():
    modules = SubjectModule.query.order_by(SubjectModule.module_id).all()
    level_options = [
        {"key": k, "level": v, "label": Config.LEVEL_LABELS[v]}
        for k, v in Config.LEVEL_OPTIONS.items()
    ]
    return modules, level_options


@bp.route("/health", methods=["GET"])
def health():
    try:
        ensure_indexes()
        mongo_ok = True
    except Exception as e:
        mongo_ok = False
        logger.warning("MongoDB 不可用: %s", e)
    return jsonify({"status": "ok", "service": "profile-flask", "mongo_ok": mongo_ok})


# ---------- 对话（MongoDB）----------

@bp.route("/dialogue/init/<int:student_id>", methods=["POST"])
def dialogue_init(student_id: int):
    """初始化对话：欢迎语 + 分步内嵌选择题（无独立表单页）。"""
    try:
        modules, level_options = _module_options()
        mod_list = [
            {"module_id": m.module_id, "module_name": m.module_name} for m in modules
        ]
        data = resume_or_init_conversational_dialogue(
            student_id, mod_list, level_options
        )
        return jsonify(data)
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("对话初始化失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/dialogue/text-submit", methods=["POST"])
def dialogue_text_submit():
    """自由文本自评提交。Body: { student_id, session_id, text }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        session_id = data.get("session_id") or str(student_id)
        text = data.get("text", "")
        result = process_dialogue_text(student_id, session_id, text)
        return jsonify(result)
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("文本自评提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/dialogue/step-submit", methods=["POST"])
def dialogue_step_submit():
    """
    对话分步提交：用户点击内嵌选项后推进下一轮。
    Body: { student_id, session_id, value }
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        session_id = data.get("session_id") or str(student_id)
        value = data.get("value")
        if value is None or str(value).strip() == "":
            return jsonify({"error": "请选择一项"}), 400

        result = process_dialogue_step(student_id, session_id, str(value))
        return jsonify(result)
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("对话步骤提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/dialogue/rebuild/<int:student_id>", methods=["POST"])
def dialogue_rebuild(student_id: int):
    """
    重新构建完整画像：清空全部画像数据（含基本信息与标签），开启新对话会话。
    """
    try:
        reset_info = reset_profile_data(student_id)
        abandon_active_sessions(student_id)
        modules, level_options = _module_options()
        mod_list = [
            {"module_id": m.module_id, "module_name": m.module_name} for m in modules
        ]
        data = init_conversational_dialogue(student_id, mod_list, level_options)
        return jsonify({**data, **reset_info, "message": "已重置，请重新完成画像构建"})
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("重新构建失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/dialogue/basic-info-submit", methods=["POST"])
def dialogue_basic_info_submit():
    """
    提交基本情况 → 记录 Mongo → 展示模块自评卡片。
    Body: { student_id, session_id, form: { grade, major, daily_study_hours, learn_preference, learn_goal } }
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        session_id = data.get("session_id") or str(student_id)
        form = data.get("form") or {}
        if not form.get("grade") and not form.get("major"):
            return jsonify({"error": "请至少填写年级或专业"}), 400

        record_basic_info_submit(student_id, session_id, form)
        modules, level_options = _module_options()
        mod_list = [
            {"module_id": m.module_id, "module_name": m.module_name} for m in modules
        ]
        append_module_assess_card(student_id, session_id, mod_list, level_options)

        return jsonify(
            {
                "student_id": student_id,
                "session_id": session_id,
                "phase": "assess",
                "basic_info": form,
                "messages": list_messages(student_id, session_id),
            }
        )
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("基本情况提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/dialogue/history/<int:student_id>", methods=["GET"])
def dialogue_history(student_id: int):
    session_id = request.args.get("session_id")
    sess = get_session(session_id) if session_id else None
    if not sess:
        sess = get_active_session_for_student(student_id)
        if sess:
            session_id = sess["session_id"]
    phase = compute_phase(sess["step"]) if sess else "welcome"
    body = {
        "student_id": student_id,
        "session_id": session_id,
        "phase": phase,
        "step": sess.get("step") if sess else None,
        "context_log": (sess or {}).get("context_log", []),
        "messages": list_messages(student_id, session_id) if session_id else [],
        "expects_text": bool((sess or {}).get("expects_text")),
        "resumed": bool(sess),
    }
    if sess and sess.get("step") == "assess_module":
        body["module_index"] = sess.get("assess_index", 0)
        body["total_modules"] = len(sess.get("modules") or [])
    if sess and sess.get("step") == "quiz":
        qi = len([c for c in sess.get("context_log", []) if c.get("type") == "quiz_answer"])
        body["quiz_index"] = qi
        body["quiz_total"] = len(sess.get("exercises") or [])
    return jsonify(body)


@bp.route("/dialogue/assess-submit", methods=["POST"])
def dialogue_assess_submit():
    """
    提交模块自评 → 记录 Mongo 对话 → 抽选择题。
    Body: { student_id, session_id, assessments: [{module_id, choice}] }
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        session_id = data.get("session_id") or str(student_id)
        assessments = data.get("assessments") or []
        if len(assessments) < 12:
            return jsonify({"error": "请完成全部 12 个模块的自评"}), 400

        modules, level_options = _module_options()
        mod_by_id = {m.module_id: m for m in modules}
        labels = []
        for a in assessments:
            mid = int(a["module_id"])
            choice = a.get("choice", "").upper()
            name = mod_by_id.get(mid).module_name if mid in mod_by_id else str(mid)
            lvl = Config.LEVEL_LABELS.get(parse_level(choice), choice)
            labels.append(f"{name}:{choice}({lvl})")

        record_assess_submit(student_id, session_id, assessments, labels)
        exercises = draw_exercises_for_modules(assessments)
        record_quiz_batch(student_id, session_id, exercises)

        return jsonify(
            {
                "student_id": student_id,
                "session_id": session_id,
                "exercises": exercises,
                "phase": "quiz",
                "messages": list_messages(student_id, session_id),
            }
        )
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("自评提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/dialogue/quiz-submit", methods=["POST"])
def dialogue_quiz_submit():
    """
    提交校验选择题 → 判题 → 画像入库 → 写入对话结果。
    Body: { student_id, session_id, module_assessments, answers: [{ex_id, choice}] }
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data.get("student_id") or 1)
        session_id = data.get("session_id") or str(student_id)
        if not data.get("answers"):
            return jsonify({"error": "answers 不能为空"}), 400
        if not data.get("module_assessments"):
            return jsonify({"error": "module_assessments 不能为空"}), 400

        result = submit_and_build_profile(student_id, data)
        correct_n = sum(1 for j in result["judge_details"] if j["judge_result"] == 1)
        summary = f"共答对 {correct_n}/{len(result['judge_details'])} 题。"
        record_quiz_submit(student_id, session_id, summary)
        record_build_result(
            student_id,
            session_id,
            result["module_results"],
            result["message"],
        )

        return jsonify(
            {
                **result,
                "session_id": session_id,
                "phase": "done",
                "messages": list_messages(student_id, session_id),
            }
        )
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("校验提交失败")
        return jsonify({"error": str(e)}), 500


# ---------- 兼容旧接口 ----------

@bp.route("/modules", methods=["GET"])
def list_modules():
    modules, level_options = _module_options()
    return jsonify(
        {
            "modules": [
                {"module_id": m.module_id, "module_name": m.module_name}
                for m in modules
            ],
            "level_options": level_options,
        }
    )


@bp.route("/draw-exercises", methods=["POST"])
def draw_exercises():
    try:
        data = request.get_json(force=True) or {}
        assessments = data.get("assessments") or []
        exercises = draw_exercises_for_modules(assessments)
        return jsonify({"exercises": exercises, "total": len(exercises)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/submit", methods=["POST"])
def submit_answers():
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data.get("student_id") or 1)
        return jsonify(submit_and_build_profile(student_id, data))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.route("/resources/plan", methods=["POST"])
def resource_plan():
    """
    学情分析智能体：根据画像编排资源生成计划（不直接调用星火）。
    Body: { student_id, module_id?, bundle_mode?, trigger_type? }
    """
    from services.resource_orchestrator_service import build_resource_plan

    try:
        data = request.get_json(force=True) or {}
        result = build_resource_plan(
            int(data["student_id"]),
            data.get("module_id"),
            data.get("bundle_mode", "single"),
            data.get("trigger_type", "profile_button"),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("资源计划编排失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/practice/generate", methods=["POST"])
def practice_generate():
    """
    题库智能体实时生成模块练习（5~10 题）。
    Body: { student_id, module_id, source? }
    """
    try:
        data = request.get_json(force=True) or {}
        result = generate_practice_set(
            int(data["student_id"]),
            int(data["module_id"]),
            data.get("source", "profile"),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("练习出题失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/practice/submit", methods=["POST"])
def practice_submit():
    """
    提交模块练习 → 自动批改 + 画像回写。
    Body: { student_id, session_id, answers: [{ qid, answer }] }
    """
    try:
        data = request.get_json(force=True) or {}
        result = submit_practice(
            int(data["student_id"]),
            data.get("session_id", ""),
            data.get("answers") or [],
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("练习提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/tag/navigate", methods=["POST"])
def tag_navigate():
    """
    标签跳转学习页：根据标签类型返回学习资源、训练题库与页面路由。
    Body: { student_id, tag_type, tag_content, module_id }
    """
    try:
        data = request.get_json(force=True) or {}
        result = resolve_tag_navigation(
            int(data["student_id"]),
            data.get("tag_type", ""),
            data.get("tag_content", ""),
            data.get("module_id"),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("标签跳转失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/tag/navigate", methods=["GET"])
def tag_navigate_get():
    """学习专区/训练页刷新时按 query 重新拉取跳转数据。"""
    try:
        result = resolve_tag_navigation(
            int(request.args["student_id"]),
            request.args.get("tag_type", ""),
            request.args.get("tag_content", ""),
            request.args.get("module_id"),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("标签跳转查询失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/mastery/<int:student_id>", methods=["GET"])
def mastery_view(student_id: int):
    """12 模块掌握视图 + 快照 + 日志 + AI 解读。"""
    from services.profile_snapshot_service import get_profile_dashboard
    return jsonify(get_profile_dashboard(student_id))


@bp.route("/profile/snapshots/<int:student_id>", methods=["GET"])
def profile_snapshots(student_id: int):
    from services.profile_snapshot_service import list_snapshots
    course_id = request.args.get("course_id", Config.COURSE_ID)
    return jsonify({"student_id": student_id, "snapshots": list_snapshots(student_id, course_id)})


@bp.route("/profile/logs/<int:student_id>", methods=["GET"])
def profile_logs(student_id: int):
    from services.profile_snapshot_service import list_change_logs
    course_id = request.args.get("course_id", Config.COURSE_ID)
    return jsonify({"student_id": student_id, "logs": list_change_logs(student_id, course_id)})


@bp.route("/profile/<int:student_id>", methods=["GET"])
def profile_detail(student_id: int):
    items = get_student_profile(student_id)
    return jsonify({"student_id": student_id, "items": items, "total": len(items)})


# ---------- 日常答疑 ----------

@bp.route("/qa/init/<int:student_id>", methods=["POST"])
def qa_init(student_id: int):
    """初始化日常答疑会话。"""
    try:
        return jsonify(init_qa_dialogue(student_id))
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("答疑初始化失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/qa/ask", methods=["POST"])
def qa_ask():
    """
    日常答疑：自由提问，AI 作答并动态更新知识点掌握度。
    Body: { student_id, question }
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        question = data.get("question", "")
        result = ask_question(student_id, question)
        return jsonify(result)
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("答疑提问失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/qa/history/<int:student_id>", methods=["GET"])
def qa_history(student_id: int):
    return jsonify(get_qa_history(student_id))


# ---------- 多模态智能辅导（模块4）----------

@bp.route("/tutoring/init/<int:student_id>", methods=["POST"])
def tutoring_init(student_id: int):
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        return jsonify(init_tutoring(student_id, session_id))
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("智能辅导初始化失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/tutoring/new-session/<int:student_id>", methods=["POST"])
def tutoring_new_session(student_id: int):
    """开启新的辅导对话窗口，旧会话保留但不返回。"""
    try:
        return jsonify(create_tutoring_session(student_id))
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("创建辅导新会话失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/tutoring/ask", methods=["POST"])
def tutoring_ask():
    """
    多模态智能辅导。
    Body: { student_id, question, context?, answer_mode?, session_id? }
    answer_mode: all（文字+图解+B站视频）| text | diagram | video
    context: { knowledge_point, resource_title, resource_excerpt, code_snippet, image_description }
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        question = data.get("question", "")
        context = data.get("context")
        answer_mode = data.get("answer_mode", "all")
        session_id = data.get("session_id")
        result = ask_tutoring(student_id, question, context, answer_mode, session_id)
        return jsonify(result)
    except DialogueStoreError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("智能辅导提问失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/tutoring/history/<int:student_id>", methods=["GET"])
def tutoring_history(student_id: int):
    return jsonify(get_tutoring_history(student_id))


@bp.route("/history/all/<int:student_id>", methods=["GET"])
def learning_history_all(student_id: int):
    """聚合智能辅导、日常答疑、画像构建的历史记录。"""
    try:
        return jsonify(get_learning_history(student_id))
    except Exception as e:
        logger.exception("学习历史查询失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/wrong-questions/<int:student_id>", methods=["GET"])
def wrong_questions_list(student_id: int):
    """错题复习列表。"""
    try:
        limit = int(request.args.get("limit", 100))
        return jsonify(list_wrong_questions(student_id, limit=limit))
    except Exception as e:
        logger.exception("错题列表查询失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/wrong-questions/reviewed", methods=["POST"])
def wrong_questions_mark_reviewed():
    """标记错题已复习。Body: { student_id, item_id }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        item_id = data.get("item_id", "")
        ok = mark_wrong_reviewed(student_id, item_id)
        return jsonify({"student_id": student_id, "item_id": item_id, "ok": ok})
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except Exception as e:
        logger.exception("标记错题复习失败")
        return jsonify({"error": str(e)}), 500


# ---------- 统一习题中心 ----------

@bp.route("/exercise-center/overview/<int:student_id>", methods=["GET"])
def exercise_center_overview(student_id: int):
    try:
        return jsonify(get_center_overview(student_id))
    except Exception as e:
        logger.exception("习题中心概览失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/exercise-center/generate", methods=["POST"])
def exercise_center_generate():
    """
    统一习题出题。
    Body: { student_id, mode, module_id?, item_ids?, day?, kp_id? }
    mode: special | module | wrong | roadmap
    """
    try:
        data = request.get_json(force=True) or {}
        result = generate_exercise_session(
            int(data["student_id"]),
            data.get("mode", "special"),
            data.get("module_id"),
            data.get("item_ids"),
            data.get("day"),
            data.get("kp_id"),
            data.get("resource_id"),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("习题中心出题失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/exercise-center/submit", methods=["POST"])
def exercise_center_submit():
    """统一习题提交批改。Body: { student_id, session_id, answers }"""
    try:
        data = request.get_json(force=True) or {}
        result = submit_exercise_session(
            int(data["student_id"]),
            data.get("session_id", ""),
            data.get("answers") or [],
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("习题中心提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/roadmap/progress/<int:student_id>", methods=["GET"])
def roadmap_progress_get(student_id: int):
    """获取学习路线进度（当前任务阶段）。"""
    try:
        from services.profile_snapshot_service import get_profile_dashboard

        modules = get_profile_dashboard(student_id).get("modules") or []
        return jsonify(get_roadmap_progress(student_id, modules))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("路线进度查询失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/roadmap/task", methods=["POST"])
def roadmap_task_update():
    """
    更新当前阶段子任务完成状态。
    Body: { student_id, day|stage, task_id, completed }
    """
    try:
        data = request.get_json(force=True) or {}
        from services.profile_snapshot_service import get_profile_dashboard

        modules = get_profile_dashboard(int(data["student_id"])).get("modules") or []
        stage = int(data.get("stage") or data.get("day") or 0)
        result = update_roadmap_task(
            int(data["student_id"]),
            stage,
            data.get("task_id", ""),
            bool(data.get("completed")),
            modules,
            auto=bool(data.get("auto")),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("路线任务更新失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/roadmap/advance", methods=["POST"])
def roadmap_advance():
    """当前阶段全部完成后，按最新学情进入下一阶段。"""
    try:
        data = request.get_json(force=True) or {}
        from services.profile_snapshot_service import get_profile_dashboard

        modules = get_profile_dashboard(int(data["student_id"])).get("modules") or []
        result = refresh_current_stage(int(data["student_id"]), modules)
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("路线推进失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/resource-status/<int:student_id>", methods=["GET"])
def resource_status_list(student_id: int):
    """批量查询资源完成状态。"""
    try:
        ids_raw = request.args.get("ids", "")
        resource_ids = [x.strip() for x in ids_raw.split(",") if x.strip()] or None
        return jsonify(get_resource_status_map(student_id, resource_ids))
    except Exception as e:
        logger.exception("资源状态查询失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/resource-status/mark", methods=["POST"])
def resource_status_mark():
    """标记资源已阅/已完成。Body: { student_id, resource_id, status, resource_type?, module_id?, score? }"""
    try:
        data = request.get_json(force=True) or {}
        result = mark_resource_status(
            int(data["student_id"]),
            str(data["resource_id"]),
            str(data.get("status", "viewed")),
            resource_type=data.get("resource_type"),
            module_id=data.get("module_id"),
            score=data.get("score"),
        )
        return jsonify(result)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("资源状态标记失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/code/run", methods=["POST"])
def code_run():
    """运行 Python 代码案例。Body: { student_id, code, resource_id? }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        code = data.get("code", "")
        result = execute_python_code_interactive(code)
        record_event(
            student_id,
            "code_practice",
            "code_run",
            {
                "ok": result.get("ok"),
                "resource_id": data.get("resource_id"),
                "code_len": len(code or ""),
            },
        )
        return jsonify({"student_id": student_id, **result})
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except Exception as e:
        logger.exception("代码运行失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/code/check", methods=["POST"])
def code_check():
    """代码实操验收：运行代码并按用例逐项判题。Body: { student_id, code, module_id?, module_name?, content?, resource_id? }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        module_id = data.get("module_id")
        if module_id is not None:
            module_id = int(module_id)
        result = check_code_practice(
            student_id=student_id,
            code=data.get("code", ""),
            module_id=module_id,
            module_name=data.get("module_name"),
            content=data.get("content"),
            resource_id=data.get("resource_id"),
        )
        record_event(
            student_id,
            "code_practice",
            "code_check",
            {
                "resource_id": data.get("resource_id"),
                "module_id": module_id,
                "passed": result.get("passed"),
                "can_submit": result.get("can_submit"),
            },
        )
        return jsonify(result)
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except Exception as e:
        logger.exception("代码验收失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/code/submit", methods=["POST"])
def code_submit():
    """代码实操提交：验收通过后回写画像。Body: { student_id, code, module_id?, module_name?, content?, resource_id? }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        module_id = data.get("module_id")
        if module_id is not None:
            module_id = int(module_id)
        result = submit_code_practice(
            student_id=student_id,
            code=data.get("code", ""),
            module_id=module_id,
            module_name=data.get("module_name"),
            content=data.get("content"),
            resource_id=data.get("resource_id"),
        )
        return jsonify(result), (200 if result.get("ok") else 400)
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except Exception as e:
        logger.exception("代码实操提交失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/tutoring/generate-media", methods=["POST"])
def tutoring_generate_media():
    """
    为已有辅导回答生成真实图片与语音。
    Body: { student_id, answer } 或 { student_id, message_id }（暂仅支持传 answer）
    """
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        answer = data.get("answer")
        if not answer:
            return jsonify({"error": "请提供 answer 对象"}), 400
        enriched = generate_tutoring_media(student_id, answer)
        message_id = data.get("message_id")
        if message_id:
            from services.dialogue_service import update_message_payload

            sid = data.get("session_id")
            if sid:
                sid = validate_tutoring_session_id(student_id, sid)
            else:
                from services.tutoring_service import resolve_tutoring_session_id

                sid = resolve_tutoring_session_id(student_id)

            update_message_payload(
                student_id,
                sid,
                message_id,
                enriched,
            )
        record_event(student_id, "tutoring_media", "tutoring", {"has_slides": bool(enriched.get("video_slides"))})
        return jsonify({"student_id": student_id, "answer": enriched, "persisted": bool(message_id)})
    except Exception as e:
        logger.exception("多媒体生成失败")
        return jsonify({"error": str(e)}), 500


# ---------- 行为埋点 ----------

@bp.route("/behavior/track", methods=["POST"])
def behavior_track():
    """记录学习行为事件。Body: { student_id, event_type, event_source?, payload? }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        event_type = data.get("event_type", "")
        if not event_type:
            return jsonify({"error": "event_type 必填"}), 400
        ok = record_event(
            student_id,
            event_type,
            data.get("event_source"),
            data.get("payload"),
        )
        return jsonify({"ok": ok, "student_id": student_id, "event_type": event_type})
    except Exception as e:
        logger.exception("行为埋点失败")
        return jsonify({"error": str(e)}), 500


# ---------- 学习效果评估（模块5）----------

@bp.route("/evaluation/metrics/<int:student_id>", methods=["GET"])
def evaluation_metrics(student_id: int):
    course_id = request.args.get("course_id", Config.COURSE_ID)
    return jsonify(collect_metrics(student_id, course_id))


@bp.route("/evaluation/generate", methods=["POST"])
def evaluation_generate():
    """生成评估报告并根据结果给出调整建议。Body: { student_id, use_ai? }"""
    try:
        data = request.get_json(force=True) or {}
        student_id = int(data["student_id"])
        course_id = data.get("course_id", Config.COURSE_ID)
        use_ai = data.get("use_ai", True)
        return jsonify(generate_evaluation(student_id, course_id, use_ai))
    except Exception as e:
        logger.exception("评估报告生成失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/evaluation/list/<int:student_id>", methods=["GET"])
def evaluation_list(student_id: int):
    limit = int(request.args.get("limit", 10))
    return jsonify({"student_id": student_id, "items": list_evaluations(student_id, limit)})


@bp.route("/evaluation/adjustment-preview", methods=["POST"])
def evaluation_adjustment_preview():
    """评估调整预览。Body: { adjustment }"""
    try:
        from services.evaluation_adjust_service import build_adjustment_preview

        data = request.get_json(force=True) or {}
        return jsonify(build_adjustment_preview(data.get("adjustment")))
    except Exception as e:
        logger.exception("评估调整预览失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/evaluation/apply-sync", methods=["POST"])
def evaluation_apply_sync():
    """
    评估应用后同步 Flask 学习方案（每日路线聚焦）。
    Body: { student_id, eval_id?, adjustment, java_ok? }
    """
    try:
        from services.evaluation_adjust_service import apply_evaluation_sync

        data = request.get_json(force=True) or {}
        log = apply_evaluation_sync(
            int(data["student_id"]),
            data.get("eval_id"),
            data.get("adjustment") or {},
            bool(data.get("java_ok", True)),
        )
        return jsonify(log)
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
    except Exception as e:
        logger.exception("评估应用同步失败")
        return jsonify({"error": str(e)}), 500


@bp.route("/evaluation/apply-log/<int:student_id>", methods=["GET"])
def evaluation_apply_log(student_id: int):
    from services.evaluation_adjust_service import get_latest_apply_log

    log = get_latest_apply_log(student_id)
    return jsonify({"student_id": student_id, "log": log})


@bp.route("/evaluation/<int:eval_id>", methods=["GET"])
def evaluation_detail(eval_id: int):
    detail = get_evaluation_detail(eval_id)
    if not detail:
        return jsonify({"error": "评估报告不存在"}), 404
    return jsonify(detail)


@bp.route("/v1/courses/<course_id>/profile/basic/<int:student_id>", methods=["GET"])
def reserved_basic_info(course_id: str, student_id: int):
    """预留：获取用户基础信息+学习偏好。"""
    from sqlalchemy import text
    row = db.session.execute(
        text("SELECT real_name, grade, major, learn_preferences FROM student WHERE id=:id"),
        {"id": student_id},
    ).fetchone()
    if not row:
        return jsonify({"code": 404, "course_id": course_id, "message": "用户不存在"}), 404
    return jsonify({
        "code": 0,
        "course_id": course_id,
        "data": {
            "student_id": student_id,
            "real_name": row[0],
            "grade": row[1],
            "major": row[2],
            "learn_preferences": row[3],
        },
    })


@bp.route("/v1/courses/<course_id>/profile/full/<int:student_id>", methods=["GET"])
def reserved_full_profile(course_id: str, student_id: int):
    """预留：获取全维度画像数据。"""
    mastery = get_mastery_view(student_id)
    items = get_student_profile(student_id)
    return jsonify({"code": 0, "course_id": course_id, "data": {"mastery": mastery, "items": items}})


@bp.route("/v1/courses/<course_id>/profile/logs/<int:student_id>", methods=["GET"])
def reserved_profile_logs(course_id: str, student_id: int):
    """预留：获取画像快照与变更日志。"""
    from sqlalchemy import text
    snaps = db.session.execute(
        text(
            "SELECT id, scores_json, tags_json, created_at FROM profile_snapshot "
            "WHERE student_id=:sid AND course_id=:cid ORDER BY id DESC LIMIT 10"
        ),
        {"sid": student_id, "cid": course_id},
    ).fetchall()
    logs = db.session.execute(
        text(
            "SELECT field_name, old_value, new_value, source, created_at FROM profile_change_log "
            "WHERE student_id=:sid AND course_id=:cid ORDER BY id DESC LIMIT 50"
        ),
        {"sid": student_id, "cid": course_id},
    ).fetchall()
    return jsonify({
        "code": 0,
        "course_id": course_id,
        "data": {
            "snapshots": [dict(zip(["id", "scores_json", "tags_json", "created_at"], r)) for r in snaps],
            "change_logs": [dict(zip(["field_name", "old_value", "new_value", "source", "created_at"], r)) for r in logs],
        },
    })


@bp.route("/profile/update", methods=["POST", "PUT", "PATCH"])
def profile_update():
    try:
        data = request.get_json(force=True) or {}
        result = update_knowledge_point_level(
            int(data["student_id"]),
            int(data["kp_id"]),
            int(data["master_level"]),
            data.get("reason", ""),
        )
        return jsonify(result)
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400


# ---------- 管理员班级学情 ----------

@bp.route("/admin/class-overview", methods=["POST"])
def admin_class_overview():
    """班级学情总览：四卡片统计 + 12 模块均分。"""
    try:
        data = request.get_json(force=True) or {}
        student_ids = [int(x) for x in (data.get("student_ids") or [])]
        from services.admin_stats_service import get_class_overview
        return jsonify(get_class_overview(student_ids))
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400


@bp.route("/admin/students-stats", methods=["POST"])
def admin_students_stats():
    """批量获取学生学情均分与最近活跃时间。"""
    try:
        data = request.get_json(force=True) or {}
        student_ids = [int(x) for x in (data.get("student_ids") or [])]
        from services.admin_stats_service import get_students_learning_stats
        stats = get_students_learning_stats(student_ids)
        return jsonify({"students": stats})
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"参数错误: {e}"}), 400
