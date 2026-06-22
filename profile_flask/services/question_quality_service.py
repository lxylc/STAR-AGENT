"""选择题质量校验：过滤占位选项、补全真实选项。"""
from __future__ import annotations

import logging
import re

from knowledge_data import EXERCISE_BANK
from models import Exercise, KnowledgePoint

logger = logging.getLogger(__name__)

_PLACEHOLDER_VALUES = frozenset(
    {
        "选项a",
        "选项b",
        "选项c",
        "选项d",
        "选项 a",
        "选项 b",
        "选项 c",
        "选项 d",
        "a",
        "b",
        "c",
        "d",
    }
)


def normalize_qtext(text: str) -> str:
    t = re.sub(r"\s+", "", str(text or ""))
    for old, new in (("？", "?"), ("，", ","), ("：", ":"), ("（", "("), ("）", ")")):
        t = t.replace(old, new)
    return t.lower()


def is_placeholder_options(opts: dict | None) -> bool:
    if not isinstance(opts, dict) or not opts:
        return True
    for key, val in opts.items():
        v = str(val).strip().lower()
        k = str(key).strip().upper()
        if v not in _PLACEHOLDER_VALUES and v != f"选项{k.lower()}":
            return False
    return True


def _match_answer_key(answer: str, options: dict) -> str | None:
    ans = str(answer or "").strip()
    if not ans or not isinstance(options, dict) or not options:
        return None
    opt_keys = {str(k).upper(): str(k) for k in options.keys()}
    ans_up = ans.upper()
    if ans_up in opt_keys:
        return opt_keys[ans_up]
    if ans_up and ans_up[0] in opt_keys:
        return opt_keys[ans_up[0]]
    ans_norm = normalize_qtext(ans)
    for key, val in options.items():
        if normalize_qtext(val) == ans_norm:
            return str(key)
    return None


def is_valid_choice_question(q: dict) -> bool:
    if (q.get("type") or "choice") != "choice":
        return True
    opts = q.get("options")
    if not isinstance(opts, dict) or len(opts) < 2:
        return False
    if is_placeholder_options(opts):
        return False
    unique_vals = {str(v).strip().lower() for v in opts.values() if str(v).strip()}
    if len(unique_vals) < 2:
        return False
    return _match_answer_key(q.get("answer") or "", opts) is not None


def lookup_bank_entry(module_name: str, content: str) -> dict | None:
    bank = EXERCISE_BANK.get(module_name or "")
    if not bank:
        return None
    target = normalize_qtext(content)
    if not target:
        return None
    for level_questions in bank.values():
        for entry in level_questions:
            if len(entry) < 4:
                continue
            _, q_content, options, answer = entry[0], entry[1], entry[2], entry[3]
            bank_norm = normalize_qtext(q_content)
            if bank_norm == target or bank_norm in target or target in bank_norm:
                return {
                    "content": q_content,
                    "options": options if isinstance(options, dict) else {},
                    "answer": str(answer or "").strip(),
                }
    return None


def lookup_exercise_by_content(content: str, module_id: int | None = None) -> dict | None:
    content = str(content or "").strip()
    if not content:
        return None
    query = Exercise.query.filter(Exercise.content == content)
    if module_id is not None:
        query = query.join(KnowledgePoint, Exercise.kp_id == KnowledgePoint.kp_id).filter(
            KnowledgePoint.module_id == module_id
        )
    row = query.first()
    if not row and len(content) >= 8:
        like = f"%{content[:24]}%"
        query = Exercise.query.filter(Exercise.content.like(like))
        if module_id is not None:
            query = query.join(KnowledgePoint, Exercise.kp_id == KnowledgePoint.kp_id).filter(
                KnowledgePoint.module_id == module_id
            )
        row = query.first()
    if not row:
        return None
    opts = row.options_dict()
    return {
        "content": row.content or "",
        "options": opts if isinstance(opts, dict) else {},
        "answer": str(row.answer or "").strip(),
    }


def enrich_choice_question(q: dict, module_name: str = "", module_id: int | None = None) -> dict | None:
    """尝试补全占位选项；失败则返回 None。"""
    if (q.get("type") or "choice") != "choice":
        return q
    if is_valid_choice_question(q):
        return q

    patch = lookup_bank_entry(module_name, q.get("content") or "")
    if not patch or is_placeholder_options(patch.get("options")):
        patch = lookup_exercise_by_content(q.get("content") or "", module_id)
    if not patch or is_placeholder_options(patch.get("options")):
        return None

    merged = dict(q)
    merged["options"] = patch["options"]
    if patch.get("answer"):
        merged["answer"] = patch["answer"]
    if patch.get("content"):
        merged["content"] = patch["content"]
    return merged if is_valid_choice_question(merged) else None


def filter_valid_questions(
    questions: list[dict],
    *,
    module_name: str = "",
    module_id: int | None = None,
) -> list[dict]:
    valid: list[dict] = []
    for q in questions:
        qtype = q.get("type") or "choice"
        if qtype != "choice":
            if q.get("answer"):
                valid.append(q)
            continue
        enriched = enrich_choice_question(q, module_name, module_id)
        if enriched:
            valid.append(enriched)
        else:
            logger.warning(
                "丢弃无效选择题（占位选项或答案不匹配）: %s",
                (q.get("content") or "")[:60],
            )
    return valid
