"""学情分析智能体：根据画像与模块掌握度编排资源生成计划。"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from config import Config
from knowledge_data import MODULE_NAMES
from services.profile_snapshot_service import get_profile_dashboard

logger = logging.getLogger(__name__)

SUBJECT = "Python程序设计"
BUNDLE_MODES = frozenset({"single", "weak_bundle", "strong_bundle", "full"})
TRIGGER_TYPES = frozenset(
    {"profile_button", "tag_click", "chart_click", "assessment_complete"}
)

# 过渡期：编排五智能体 → Java 三智能体
AGENT_TO_JAVA = {
    "ANALYSIS": None,
    "THEORY": "LECTURE",
    "PRACTICE": "COURSEWARE",
    "EXAM": "EXERCISE",
    "INTEGRATE": None,
}

LEVEL_TIER = {
    1: "basic",
    2: "basic",
    3: "balanced",
    4: "advanced",
}


def _module_by_id(modules: list[dict], module_id: int) -> dict | None:
    for m in modules:
        if int(m.get("module_id") or 0) == module_id:
            return m
    return None


def _score_band(score: int | float | None) -> str:
    if score is None:
        return "weak"
    s = float(score)
    if s >= 85:
        return "strong"
    if s >= 45:
        return "normal"
    return "weak"


def _difficulty_profile(band: str) -> dict[str, Any]:
    if band == "weak":
        return {
            "tier": "basic_heavy",
            "basic_ratio": 0.7,
            "advanced_ratio": 0.3,
            "focus": ["theory", "basic_exam"],
            "content_focus": "理论讲解与基础巩固",
            "style_hint": "图文图解、分点列举",
        }
    if band == "strong":
        return {
            "tier": "advanced_heavy",
            "basic_ratio": 0.3,
            "advanced_ratio": 0.7,
            "focus": ["practice", "challenge_exam"],
            "content_focus": "实战案例与高阶挑战",
            "style_hint": "代码实战、综合项目",
        }
    return {
        "tier": "balanced",
        "basic_ratio": 0.4,
        "advanced_ratio": 0.4,
        "focus": ["theory", "practice", "exam"],
        "content_focus": "理论、实操与习题均衡",
        "style_hint": "讲义+案例+练习组合",
    }


def _kp_for_module(module_name: str) -> str:
    """模块主知识点（与知识图谱 / 资源 subject-kp 对齐）。"""
    if module_name in MODULE_NAMES:
        return f"{module_name}-基础"
    return module_name or "Python程序设计"


def _get_evaluation_focus_detail(student_id: int) -> dict:
    try:
        from services.evaluation_adjust_service import get_evaluation_focus

        return get_evaluation_focus(student_id) or {}
    except Exception:
        logger.debug("读取评估聚焦失败", exc_info=True)
        return {}


def _get_evaluation_focus_modules(student_id: int) -> set[str]:
    focus = _get_evaluation_focus_detail(student_id)
    if focus.get("weak_modules"):
        return set(focus["weak_modules"])
    return set()


def _sort_modules_with_eval_priority(
    target_modules: list[dict], eval_focus: set[str]
) -> list[dict]:
    def sort_key(mod: dict) -> tuple:
        name = mod.get("module_name") or ""
        score = float(mod.get("final_score") or 0)
        if name in eval_focus:
            return (0, score)
        if _score_band(mod.get("final_score")) == "strong":
            return (2, -score)
        return (1, score)

    return sorted(target_modules, key=sort_key)


def _resolve_target_modules(
    modules: list[dict], module_id: int | None, bundle_mode: str
) -> list[dict]:
    if bundle_mode == "single" and module_id is not None:
        m = _module_by_id(modules, module_id)
        return [m] if m else []

    scored = [m for m in modules if m.get("final_score") is not None]
    if bundle_mode == "weak_bundle" or (bundle_mode == "single" and module_id is None):
        return sorted(scored, key=lambda x: float(x["final_score"]))[:3]
    if bundle_mode == "strong_bundle":
        return sorted(scored, key=lambda x: float(x["final_score"]), reverse=True)[:2]
    if bundle_mode == "full":
        weak = sorted(scored, key=lambda x: float(x["final_score"]))[:4]
        return weak if weak else scored[:4]
    # 默认：最薄弱 1 个模块
    if scored:
        return [min(scored, key=lambda x: float(x["final_score"]))]
    return []


def _agents_for_module(mod: dict, diff: dict) -> list[str]:
    tags = mod.get("tags") or {}
    agents = ["THEORY", "PRACTICE", "EXAM"]
    weakness = tags.get("weakness_type") or ""
    if weakness in ("理解薄弱", "记忆薄弱"):
        agents = ["THEORY", "EXAM", "PRACTICE"]
    elif tags.get("code_practice_feel") in ("实操困难", "应用薄弱"):
        agents = ["PRACTICE", "THEORY", "EXAM"]
    elif tags.get("practice_frequency") == "很少练习":
        agents = ["PRACTICE", "EXAM", "THEORY"]
    if diff["tier"] == "advanced_heavy":
        agents = ["PRACTICE", "EXAM", "THEORY"]
    return agents


def _java_agent_types(agent_codes: list[str]) -> list[str]:
    out = []
    for code in agent_codes:
        mapped = AGENT_TO_JAVA.get(code)
        if mapped and mapped not in out:
            out.append(mapped)
    return out or ["LECTURE", "EXERCISE", "COURSEWARE"]


def _build_roadmap(student_id: int, all_modules: list[dict]) -> list[dict]:
    """当前任务阶段（单模块 3 项任务），完成后自动推进下一阶段。"""
    from services.roadmap_progress_service import build_current_roadmap

    return build_current_roadmap(student_id, all_modules)


def _priority_for_module(mp: dict, eval_focus: set[str], *, is_ai: bool = False) -> dict:
    name = mp.get("module_name") or ""
    score = mp.get("final_score")
    if name in eval_focus:
        return {
            "priority_tier": "eval",
            "priority_order": 0,
            "priority_label": "评估补强",
            "recommend_reason": f"学习效果评估已将「{name}」列为优先补强模块（当前 {score} 分）",
        }
    if mp.get("score_band") == "strong":
        return {
            "priority_tier": "extend",
            "priority_order": 3,
            "priority_label": "拓展自选",
            "recommend_reason": f"「{name}」掌握较好（{score} 分），推送进阶拓展内容",
        }
    if is_ai:
        return {
            "priority_tier": "ai",
            "priority_order": 2,
            "priority_label": "AI协同生成",
            "recommend_reason": f"星火多智能体为「{name}」协同生成定制资源",
        }
    return {
        "priority_tier": "profile",
        "priority_order": 1,
        "priority_label": "学情推荐",
        "recommend_reason": f"画像实时匹配：「{name}」得分 {score}，属薄弱/待巩固模块",
    }


def _build_preview_resources(
    module_plans: list[dict], eval_focus: set[str], student_id: int, plan_seed: int
) -> list[dict]:
    """按薄弱模块生成可读讲义、代码案例与习题预览（最多 3 个模块）。"""
    from services.resource_content_builder import (
        build_courseware_markdown,
        build_exercise_preview_bundle,
        build_lecture_markdown,
    )

    previews = []
    for mp in module_plans[:3]:
        name = mp.get("module_name") or "模块"
        mid = mp.get("module_id")
        kp = mp.get("knowledge_point") or name
        score = mp.get("final_score")
        weakness = mp.get("weakness_tag") or ""
        focus = mp.get("content_focus") or "基础巩固"
        prio = _priority_for_module(mp, eval_focus)
        base = {
            "knowledgePoint": kp,
            "module_id": mid,
            "module_name": name,
            "module_score": score,
            "preview": True,
            **prio,
        }
        exercise_bundle = build_exercise_preview_bundle(
            mid, name, student_id, f"{plan_seed}:{mid}", count=3, score=score, focus=focus
        )
        previews.extend(
            [
                {
                    "id": f"preview-lecture-{mid}",
                    "resourceType": "lecture",
                    "title": f"【薄弱补强】{name} 知识点讲义",
                    "content": build_lecture_markdown(name, score, weakness, focus),
                    **base,
                },
                {
                    "id": f"preview-courseware-{mid}",
                    "resourceType": "courseware",
                    "title": f"【{name}】优秀代码案例",
                    "content": build_courseware_markdown(name, mid, score, weakness, focus),
                    **base,
                },
                {
                    "id": f"preview-exercise-{mid}",
                    "resourceType": "exercise",
                    "title": f"【{name}】专项习题（待一键生成）",
                    "content": exercise_bundle["content"],
                    "pending_generate": True,
                    **base,
                },
            ]
        )
    previews.sort(key=lambda x: (x.get("priority_order", 9), float(x.get("module_score") or 999)))
    return previews


def _pick_rotating_items(items: list[str], plan_seed: int, limit: int = 3) -> list[str]:
    """按 plan_seed 从候选中轮换选取，刷新资源时小贴士会变化。"""
    if not items:
        return []
    if len(items) <= limit:
        return items
    keyed = [
        (hashlib.md5(f"{plan_seed}:{i}:{t}".encode()).hexdigest(), t)
        for i, t in enumerate(items)
    ]
    keyed.sort()
    return [t for _, t in keyed[:limit]]


def _roadmap_task_tip(active_task: dict | None, module_name: str) -> str | None:
    if not active_task or not module_name:
        return None
    ttype = active_task.get("type")
    if ttype == "lecture":
        return (
            f"路径进行中：先阅读【{module_name}】讲义并标记已阅，"
            f"再进入代码案例与专项习题。"
        )
    if ttype == "code":
        return (
            f"路径进行中：观看【{module_name}】优秀代码案例，"
            f"对照规范写法理解实现思路后再标记已阅。"
        )
    if ttype == "exercise":
        return (
            f"路径进行中：完成【{module_name}】本轮专项巩固题，"
            f"错题会自动进入错题复习。"
        )
    return None


def _weakness_tip(module_name: str, weakness: str, content_focus: str) -> str | None:
    if not module_name or not weakness or weakness == "无短板":
        return None
    hints = {
        "理解薄弱": f"「{module_name}」理解偏弱，建议先通读讲义、画知识结构，再做题巩固。",
        "应用薄弱": f"「{module_name}」应用偏弱，建议多看优秀代码案例并跟做一遍。",
        "记忆薄弱": f"「{module_name}」记忆偏弱，建议用「讲义→案例→习题」三轮重复记忆。",
    }
    return hints.get(weakness) or f"「{module_name}」需加强{content_focus}，按路径三项任务顺序推进。"


def _build_tips(
    student_id: int,
    modules: list[dict],
    summary: dict,
    module_plans: list[dict],
    eval_focus: set[str],
    plan_seed: int,
) -> list[str]:
    """基于画像、评估聚焦、路径进度生成个性化小贴士；刷新时按 plan_seed 轮换展示。"""
    candidates: list[str] = []

    # 1. 学习路径当前任务
    try:
        from services.roadmap_progress_service import get_roadmap_progress

        progress = get_roadmap_progress(student_id, modules)
        current = progress.get("current_stage") or progress.get("current")
        if current:
            mod_name = current.get("module_name") or "当前模块"
            tip = _roadmap_task_tip(current.get("active_task"), mod_name)
            if tip:
                candidates.append(tip)
            done = progress.get("completed_stages") or progress.get("completed_days") or 0
            total = current.get("tasks_total") or 3
            done_in_stage = current.get("tasks_completed_count") or 0
            if done > 0:
                candidates.append(
                    f"你已完成 {done} 个学习阶段；本阶段【{mod_name}】进度 {done_in_stage}/{total} 项。"
                )
            elif done_in_stage > 0:
                candidates.append(
                    f"本阶段【{mod_name}】已完成 {done_in_stage}/{total} 项，继续推进剩余任务。"
                )
    except Exception:
        logger.debug("读取路径进度生成小贴士失败", exc_info=True)

    # 2. 本批优先模块（module_plans）
    for mp in module_plans[:3]:
        name = mp.get("module_name") or "模块"
        score = mp.get("final_score")
        focus = mp.get("content_focus") or "基础巩固"
        weakness = mp.get("weakness_tag") or ""
        if name in eval_focus:
            candidates.append(
                f"评估补强：优先攻克「{name}」（当前 {score} 分），"
                f"建议完成讲义→案例→习题全套资源。"
            )
        else:
            candidates.append(
                f"画像薄弱：「{name}」得分 {score}，本批侧重{focus}，"
                f"可先打开对应知识点讲义。"
            )
        wt = _weakness_tip(name, weakness, focus)
        if wt:
            candidates.append(wt)

    # 3. 练习频次偏低的具体模块
    low_practice = [
        m.get("module_name")
        for m in modules
        if (m.get("tags") or {}).get("practice_frequency") == "很少练习"
        and m.get("module_name")
    ]
    if low_practice:
        names = "、".join(low_practice[:2])
        extra = f"等 {len(low_practice)} 个" if len(low_practice) > 2 else ""
        candidates.append(
            f"「{names}」{extra}模块练习偏少，建议本周在习题中心完成至少 1 组专项练习。"
        )

    # 4. 掌握较好模块 → 拓展建议
    strong_mods = sorted(
        [m for m in modules if _score_band(m.get("final_score")) == "strong"],
        key=lambda x: float(x.get("final_score") or 0),
        reverse=True,
    )
    if strong_mods:
        top = strong_mods[0]
        candidates.append(
            f"「{top.get('module_name')}」掌握较好（{top.get('final_score')} 分），"
            f"可浏览拓展链接或挑战高阶编程题。"
        )

    # 5. 整体均分档位
    avg = summary.get("avg_score")
    if avg is not None:
        avg_f = float(avg)
        if avg_f < 50:
            candidates.append(
                f"整体均分 {avg_f:.0f}，建议按学习路径顺序推进，"
                f"每完成一模块回到画像页查看分数变化。"
            )
        elif avg_f < 75:
            candidates.append(
                f"整体均分 {avg_f:.0f}，薄弱模块优先补强，"
                f"已掌握模块可适度拓展。"
            )
        else:
            candidates.append(
                f"整体均分 {avg_f:.0f}，基础较扎实，"
                f"可加大专项习题与代码案例深度阅读。"
            )

    # 6. 评估偏好资源类型
    try:
        eval_detail = _get_evaluation_focus_detail(student_id)
        prefer = eval_detail.get("prefer_resource_types") or []
        prefer_labels = {"lecture": "讲义", "exercise": "习题", "courseware": "代码案例"}
        if prefer:
            labels = "、".join(prefer_labels.get(t, t) for t in prefer[:2])
            candidates.append(f"评估建议优先使用{labels}类资源进行本轮补强。")
    except Exception:
        pass

    if not candidates:
        candidates.append("按学习路径顺序推进：讲义 → 代码案例 → 专项习题，完成后刷新资源获取新推荐。")

    # 去重并保持顺序
    seen: set[str] = set()
    unique: list[str] = []
    for tip in candidates:
        if tip not in seen:
            seen.add(tip)
            unique.append(tip)

    return _pick_rotating_items(unique, plan_seed, limit=3)


def build_resource_plan(
    student_id: int,
    module_id: int | None = None,
    bundle_mode: str = "weak_bundle",
    trigger_type: str = "profile_button",
) -> dict[str, Any]:
    """
    学情分析智能体主入口：输出资源需求清单，供前端调 Java 生成或展示。
    """
    bundle_mode = (bundle_mode or "single").strip().lower()
    if bundle_mode not in BUNDLE_MODES:
        raise ValueError(f"无效 bundle_mode: {bundle_mode}")
    trigger_type = (trigger_type or "profile_button").strip().lower()
    if trigger_type not in TRIGGER_TYPES:
        trigger_type = "profile_button"

    dashboard = get_profile_dashboard(student_id)
    modules = dashboard.get("modules") or []
    summary = dashboard.get("summary") or {}

    if not modules:
        raise ValueError("暂无模块掌握数据，请先完成画像测评")

    target_modules = _resolve_target_modules(modules, module_id, bundle_mode)
    if not target_modules:
        raise ValueError("未找到目标模块，请指定 module_id 或先完成测评")

    eval_focus = _get_evaluation_focus_modules(student_id)
    eval_detail = _get_evaluation_focus_detail(student_id)
    target_modules = _sort_modules_with_eval_priority(target_modules, eval_focus)

    module_plans = []
    knowledge_points = []
    for mod in target_modules:
        band = _score_band(mod.get("final_score"))
        if mod.get("module_name") in eval_focus:
            band = "weak"
        diff = _difficulty_profile(band)
        agents = _agents_for_module(mod, diff)
        kp = _kp_for_module(mod.get("module_name") or "")
        knowledge_points.append(kp)
        prio = _priority_for_module(
            {
                "module_name": mod.get("module_name"),
                "final_score": mod.get("final_score"),
                "score_band": band,
            },
            eval_focus,
        )
        module_plans.append(
            {
                "module_id": mod.get("module_id"),
                "module_name": mod.get("module_name"),
                "final_score": mod.get("final_score"),
                "mastery_level": mod.get("mastery_level"),
                "score_band": band,
                "difficulty": diff,
                "agents": agents,
                "java_agent_types": _java_agent_types(agents),
                "knowledge_point": kp,
                "content_focus": diff["content_focus"],
                "style_hint": diff["style_hint"],
                "weakness_tag": (mod.get("tags") or {}).get("weakness_type"),
                "is_evaluation_focus": mod.get("module_name") in eval_focus,
                **prio,
            }
        )

    primary = module_plans[0]
    weak_label = primary.get("weakness_tag") or "待巩固知识点"
    summary_line = (
        f"当前为你生成【{primary['module_name']}】等 {len(module_plans)} 个模块的专属资源，"
        f"你的短板为「{weak_label}」，侧重{primary['content_focus']}。"
    )

    eval_focus = _get_evaluation_focus_modules(student_id)
    profile_native_weak = [
        m.get("module_name")
        for m in modules
        if m.get("module_name")
        and m.get("module_name") not in eval_focus
        and _score_band(m.get("final_score")) == "weak"
    ]
    batch_eval_count = sum(1 for mp in module_plans if mp.get("is_evaluation_focus"))
    batch_profile_count = len(module_plans) - batch_eval_count
    batch_profile_modules = [
        mp.get("module_name")
        for mp in module_plans
        if mp.get("module_name") and not mp.get("is_evaluation_focus")
    ]
    basis_weak = list(eval_focus) + [w for w in profile_native_weak if w not in eval_focus]

    if batch_eval_count or batch_profile_count:
        recommend_summary = (
            f"本批优先推送 {batch_eval_count} 个评估补强模块、"
            f"{batch_profile_count} 个学情推荐模块的配套资源（共 {len(module_plans)} 个模块）。"
        )
        if len(eval_focus) > batch_eval_count:
            recommend_summary += (
                f" 评估共标记 {len(eval_focus)} 个薄弱模块，"
                f"本批按得分优先覆盖其中 {batch_eval_count} 个。"
            )
    elif profile_native_weak:
        recommend_summary = (
            f"根据画像薄弱模块匹配 {len(module_plans)} 个模块的实时推荐资源。"
        )
    else:
        recommend_summary = summary_line

    if trigger_type == "assessment_complete" and eval_focus:
        batch_eval_names = [
            mp.get("module_name")
            for mp in module_plans
            if mp.get("is_evaluation_focus") and mp.get("module_name")
        ]
        focus_hint = "、".join(batch_eval_names[:3]) or "、".join(list(eval_focus)[:3])
        recommend_summary = (
            f"已根据最新评估调整，本批优先补强：{focus_hint}"
            f"{' 等模块' if len(batch_eval_names) > 3 or len(eval_focus) > 3 else ''}。"
        )
        if len(eval_focus) > len(batch_eval_names):
            recommend_summary += f"（评估共 {len(eval_focus)} 个薄弱模块，本批覆盖 {len(batch_eval_names)} 个）"

    import time

    plan_seed = int(time.time())

    return {
        "student_id": student_id,
        "course_id": Config.COURSE_ID,
        "subject": SUBJECT,
        "trigger_type": trigger_type,
        "bundle_mode": bundle_mode,
        "summary_line": summary_line,
        "recommend_summary": recommend_summary,
        "basis": {
            "source": "用户画像",
            "weak_modules": basis_weak[:5],
            "profile_weak_modules": profile_native_weak[:5],
            "batch_profile_modules": batch_profile_modules[:5],
            "batch_eval_count": batch_eval_count,
            "batch_profile_count": batch_profile_count,
            "avg_score": summary.get("avg_score"),
            "evaluation_adjusted": bool(eval_focus),
            "evaluation_focus_modules": list(eval_focus) if eval_focus else [],
            "prefer_resource_types": eval_detail.get("prefer_resource_types") or [],
        },
        "module_plans": module_plans,
        "knowledge_points": knowledge_points,
        "generate_request": {
            "studentId": student_id,
            "subject": SUBJECT,
            "batch": len(knowledge_points) > 1,
            "knowledgePoint": knowledge_points[0] if len(knowledge_points) == 1 else None,
            "knowledgePoints": knowledge_points if len(knowledge_points) > 1 else None,
            "agentTypes": _java_agent_types(
                list({a for p in module_plans for a in p["agents"]})
            ),
        },
        "roadmap": _build_roadmap(student_id, modules),
        "roadmap_hint": "按学情顺序推送任务：完成一项后显示下一项；本模块三项全部完成后自动进入下一薄弱模块。",
        "plan_seed": plan_seed,
        "tips": _build_tips(student_id, modules, summary, module_plans, eval_focus, plan_seed),
        "external_links": [
            {
                "title": "Python 官方文档",
                "url": "https://docs.python.org/zh-cn/3/",
            },
            {
                "title": "菜鸟教程 Python3",
                "url": "https://www.runoob.com/python3/python3-tutorial.html",
            },
        ],
        "preview_resources": _build_preview_resources(module_plans, eval_focus, student_id, plan_seed),
        "frontend_route": "/resource/personalized",
        "generation_note": (
            "实时推送：画像得分与薄弱标签即时匹配系统推荐；"
            "评估定向：应用评估调整后薄弱模块权重提升；"
            "AI 协同：星火多智能体分工生成讲义/代码/习题（需 Java 后端）。"
        ),
        "push_modes": [
            {
                "key": "realtime",
                "title": "实时推送",
                "desc": "画像得分与薄弱标签匹配存量资源",
            },
            {
                "key": "evaluation",
                "title": "评估定向推送",
                "desc": "评估应用后薄弱模块优先补强",
            },
            {
                "key": "ai",
                "title": "AI 协同生成",
                "desc": "星火多智能体生成讲义、案例与习题",
            },
        ],
    }
