"""学习效果评估 — 聚合画像、答题、进度、答疑等行为数据，生成多维度评估报告。"""
import json
import logging
from datetime import datetime

from sqlalchemy import text

from models import db
from knowledge_data import MODULE_NAMES
from services.behavior_event_service import collect_behavior_stats, record_event
from services.learning_profile_sync import get_mastery_view
from services.profile_snapshot_service import list_change_logs, list_snapshots
from services.spark_client import SparkClientError, SparkLiteClient

logger = logging.getLogger(__name__)

REPORT_PROMPT = """你是学习数据分析专家。根据以下 Python 程序设计课程学习数据，生成简洁评估报告。

数据摘要（JSON）：
{metrics_json}

请输出 JSON（仅 JSON）：
{{
  "summary": "200字以内的本周期综合评估（强调与上期的变化与成因）",
  "strengths": ["【进步】本期优势及进步根源1", "【进步】本期优势及进步根源2"],
  "weaknesses": ["【成因】本期待改进及问题成因1", "【成因】本期待改进及问题成因2"],
  "recommendations": ["周期性系统建议1", "周期性系统建议2", "周期性系统建议3"],
  "push_strategy": "资源推送策略调整说明（50字内）",
  "path_adjustment": "学习路径调整说明（50字内）"
}}"""


LEARNING_STAGES = [
    {"stage": 1, "stage_name": "阶段一·入门奠基", "module_names": MODULE_NAMES[0:3]},
    {"stage": 2, "stage_name": "阶段二·核心语法", "module_names": MODULE_NAMES[3:6]},
    {"stage": 3, "stage_name": "阶段三·进阶能力", "module_names": MODULE_NAMES[6:9]},
    {"stage": 4, "stage_name": "阶段四·实战应用", "module_names": MODULE_NAMES[9:12]},
]


def compute_stage_balance(modules: list[dict]) -> list[dict]:
    """按课程四阶段汇总模块得分，用于分阶段平衡图。"""
    score_map = {m.get("module_name"): float(m.get("final_score") or m.get("avg_score") or 0) for m in modules}
    stages_out = []
    min_avg = 101.0
    focus_stage = 1
    for st in LEARNING_STAGES:
        names = st["module_names"]
        scores = [score_map.get(n, 0) for n in names if n in score_map]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        if avg < min_avg:
            min_avg = avg
            focus_stage = st["stage"]
        stages_out.append(
            {
                "stage": st["stage"],
                "stage_name": st["stage_name"],
                "modules": names,
                "avg_score": avg,
                "module_count": len(scores),
                "is_focus": False,
            }
        )
    for s in stages_out:
        if s["stage"] == focus_stage:
            s["is_focus"] = True
    return stages_out


def _quiz_stats(student_id: int) -> dict:
    row = db.session.execute(
        text(
            "SELECT COUNT(*) AS total, SUM(judge_result) AS correct "
            "FROM answer_record WHERE student_id = :sid"
        ),
        {"sid": student_id},
    ).fetchone()
    total = int(row[0] or 0) if row else 0
    correct = int(row[1] or 0) if row else 0
    rate = round(correct / total * 100, 1) if total else 0.0
    return {"quiz_total": total, "quiz_correct": correct, "quiz_accuracy_pct": rate}


def _qa_activity(student_id: int, course_id: str) -> int:
    logs = list_change_logs(student_id, course_id)
    return sum(1 for log in logs if log.get("source") == "qa")


def _snapshot_trend(snapshots: list) -> dict:
    if not snapshots:
        return {"snapshot_count": 0, "score_trend": [], "improvement_pct": 0.0}
    points = []
    for snap in reversed(snapshots):
        scores = snap.get("scores_json") or snap.get("scores") or {}
        if isinstance(scores, str):
            try:
                scores = json.loads(scores)
            except json.JSONDecodeError:
                scores = {}
        avg = None
        if isinstance(scores, dict):
            avg = scores.get("avg_score")
            if avg is None and scores:
                finals = [
                    v.get("final_score")
                    for v in scores.values()
                    if isinstance(v, dict) and v.get("final_score") is not None
                ]
                if finals:
                    avg = sum(finals) / len(finals)
        if avg is not None:
            points.append(float(avg))
    improvement = 0.0
    if len(points) >= 2:
        improvement = round(points[-1] - points[0], 1)
    return {
        "snapshot_count": len(snapshots),
        "score_trend": points,
        "improvement_pct": improvement,
    }


def collect_metrics(student_id: int, course_id: str = "python101") -> dict:
    mastery = get_mastery_view(student_id)
    snapshots = list_snapshots(student_id, course_id)
    quiz = _quiz_stats(student_id)
    trend = _snapshot_trend(snapshots)
    qa_count = _qa_activity(student_id, course_id)

    modules = mastery.get("modules") or []
    weak_modules = [m["module_name"] for m in modules if (m.get("avg_score") or 0) < 60][:5]
    strong_modules = sorted(
        modules,
        key=lambda m: m.get("avg_score") or 0,
        reverse=True,
    )[:3]
    strong_names = [m["module_name"] for m in strong_modules]

    avg_score = mastery.get("summary", {}).get("avg_score")
    mastered_kp = sum(1 for m in modules for kp in (m.get("knowledge_points") or []) if (kp.get("master_level") or 0) >= 3)
    behavior = collect_behavior_stats(student_id)
    stage_balance = compute_stage_balance(modules)
    module_scores = [
        {
            "module_id": m.get("module_id"),
            "module_name": m.get("module_name"),
            "avg_score": float(m.get("avg_score") or m.get("final_score") or 0),
        }
        for m in modules
    ]

    return {
        "student_id": student_id,
        "course_id": course_id,
        "overall_avg_score": avg_score,
        "module_count": len(modules),
        "mastered_kp_count": mastered_kp,
        "weak_modules": weak_modules,
        "strong_modules": strong_names,
        "module_scores": module_scores,
        "quiz": quiz,
        "qa_sessions": qa_count,
        "tutoring_sessions": behavior.get("tutoring_sessions", 0),
        "snapshot_trend": trend,
        "has_profile": mastery.get("has_profile", False),
        "behavior": behavior,
        "stage_balance": stage_balance,
    }


def _rule_based_report(metrics: dict) -> dict:
    avg = metrics.get("overall_avg_score") or 0
    quiz_rate = metrics.get("quiz", {}).get("quiz_accuracy_pct", 0)
    improvement = metrics.get("snapshot_trend", {}).get("improvement_pct", 0)

    if avg >= 80:
        level = "优秀"
    elif avg >= 65:
        level = "良好"
    elif avg >= 50:
        level = "中等"
    else:
        level = "待提升"

    summary = (
        f"综合评级「{level}」，模块平均分 {avg or '-'}，"
        f"练习正确率 {quiz_rate}%，"
        f"测评提升 {improvement:+.1f} 分。"
    )
    strengths = [
        f"【进步】{name} 掌握较好" for name in (metrics.get("strong_modules") or [])[:2]
    ] or ["【进步】学习态度积极，保持当前节奏"]
    weaknesses = [
        f"【成因】{name} 模块得分偏低，需加强巩固" for name in (metrics.get("weak_modules") or [])[:2]
    ] or ["【成因】暂无明显薄弱模块"]
    recommendations = []
    if weaknesses:
        recommendations.append(f"优先巩固：{'、'.join(weaknesses[:3])}")
    if quiz_rate < 70:
        recommendations.append("加强针对性练习，建议每日完成 5-10 道选择题")
    if metrics.get("qa_sessions", 0) < 3:
        recommendations.append("多使用智能辅导提问，及时解决疑难点")
    behavior = metrics.get("behavior") or {}
    if behavior.get("push_read_rate_pct", 0) < 30 and behavior.get("push_records_total", 0) > 0:
        recommendations.append("建议多查看系统推送的学习资源，提高资源利用率")
    if behavior.get("tutoring_sessions", 0) < 2:
        recommendations.append("可尝试智能辅导多模态答疑，获得图解与讲解支持")
    if not recommendations:
        recommendations.append("保持当前学习节奏，定期复测更新画像")

    return {
        "summary": summary,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "recommendations": recommendations[:4],
        "push_strategy": "向薄弱模块倾斜推送讲义与习题" if weaknesses else "维持均衡资源推送",
        "path_adjustment": "缩短薄弱模块阶段时长，增加练习比重" if weaknesses else "按当前路径稳步推进",
    }


def _ai_report(metrics: dict) -> dict:
    client = SparkLiteClient()
    try:
        raw = client.chat(
            REPORT_PROMPT.format(metrics_json=json.dumps(metrics, ensure_ascii=False)),
            max_tokens=1024,
        )
        match = __import__("re").search(r"\{[\s\S]*\}", raw or "")
        if match:
            data = json.loads(match.group())
            if isinstance(data, dict) and data.get("summary"):
                return data
    except (SparkClientError, json.JSONDecodeError):
        logger.exception("星火评估报告生成失败，使用规则报告")
    return _rule_based_report(metrics)


def _overall_score(metrics: dict) -> float:
    avg = float(metrics.get("overall_avg_score") or 0)
    quiz = float(metrics.get("quiz", {}).get("quiz_accuracy_pct") or 0)
    improvement = float(metrics.get("snapshot_trend", {}).get("improvement_pct") or 0)
    imp_bonus = max(-5, min(10, improvement))
    if avg <= 0 and quiz <= 0:
        return 0.0
    return round(avg * 0.55 + quiz * 0.35 + imp_bonus * 0.1, 1)


def generate_evaluation(student_id: int, course_id: str = "python101", use_ai: bool = True) -> dict:
    metrics = collect_metrics(student_id, course_id)
    report = _ai_report(metrics) if use_ai else _rule_based_report(metrics)
    score = _overall_score(metrics)

    weak = metrics.get("weak_modules", [])
    quiz_rate = metrics.get("quiz", {}).get("quiz_accuracy_pct", 0)
    prefer_types = ["exercise"] if quiz_rate < 70 else ["lecture", "exercise"]
    if weak:
        prefer_types = ["lecture", "exercise", "courseware"]

    adjustment = {
        "push_strategy": report.get("push_strategy", ""),
        "path_adjustment": report.get("path_adjustment", ""),
        "weak_modules": weak,
        "recommended_actions": report.get("recommendations", []),
        "prefer_resource_types": prefer_types,
        "focus_weak_modules": bool(weak),
        "activity_score": (metrics.get("behavior") or {}).get("activity_score", 0),
    }

    eval_id = None
    try:
        row = db.session.execute(
            text(
                "INSERT INTO learning_evaluation "
                "(student_id, subject, overall_score, metrics_json, report_summary, "
                "ai_analysis, adjustment_json, eval_status, created_at) "
                "VALUES (:sid, :subj, :score, :metrics, :summary, :analysis, :adj, 'completed', NOW())"
            ),
            {
                "sid": student_id,
                "subj": "Python程序设计",
                "score": score,
                "metrics": json.dumps(metrics, ensure_ascii=False),
                "summary": report.get("summary", ""),
                "analysis": json.dumps(report, ensure_ascii=False),
                "adj": json.dumps(adjustment, ensure_ascii=False),
            },
        )
        db.session.commit()
        eval_id = row.lastrowid
    except Exception:
        db.session.rollback()
        logger.exception("评估报告入库失败（请先执行 schema-module5.sql）")

    record_event(student_id, "evaluation_generate", "evaluation_service", {"eval_id": eval_id, "score": score})

    prev_score = None
    score_delta = None
    prev_list = list_evaluations(student_id, limit=2)
    if len(prev_list) >= 2:
        prev_score = float(prev_list[1].get("overall_score") or 0)
        score_delta = round(score - prev_score, 1)

    return {
        "id": eval_id,
        "student_id": student_id,
        "overall_score": score,
        "metrics": metrics,
        "report": report,
        "adjustment": adjustment,
        "created_at": datetime.now().isoformat(),
        "previous_score": prev_score,
        "score_delta": score_delta,
        "report_no": f"RPT-{eval_id or 'DRAFT'}",
    }


def list_evaluations(student_id: int, limit: int = 10) -> list:
    rows = db.session.execute(
        text(
            "SELECT id, overall_score, report_summary, created_at "
            "FROM learning_evaluation WHERE student_id = :sid "
            "ORDER BY id DESC LIMIT :lim"
        ),
        {"sid": student_id, "lim": limit},
    ).fetchall()
    return [
        {
            "id": r[0],
            "overall_score": float(r[1]) if r[1] is not None else 0,
            "report_summary": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


def get_evaluation_detail(eval_id: int) -> dict | None:
    row = db.session.execute(
        text(
            "SELECT id, student_id, overall_score, metrics_json, report_summary, "
            "ai_analysis, adjustment_json, created_at "
            "FROM learning_evaluation WHERE id = :id"
        ),
        {"id": eval_id},
    ).fetchone()
    if not row:
        return None
    analysis = row[5]
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {"summary": row[4]}
    adj = row[6]
    if isinstance(adj, str):
        try:
            adj = json.loads(adj)
        except json.JSONDecodeError:
            adj = {}
    metrics = row[3]
    if isinstance(metrics, str):
        try:
            metrics = json.loads(metrics)
        except json.JSONDecodeError:
            metrics = {}
    return {
        "id": row[0],
        "student_id": row[1],
        "overall_score": float(row[2]) if row[2] is not None else 0,
        "metrics": metrics,
        "report": analysis,
        "adjustment": adj,
        "created_at": row[7].isoformat() if row[7] else None,
    }
