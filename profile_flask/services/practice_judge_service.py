"""模块练习判题：客观题本地判定 + 编程题测试运行 + 主观题 AI 综合语义评判。"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import ast
from dataclasses import dataclass

from services.spark_client import SparkClientError, SparkLiteClient

logger = logging.getLogger(__name__)

# 简答题：AI 综合语义评判（三档）
SHORT_JUDGE_PROMPT = """你是 Python 课程阅卷老师。请通读题目、参考答案与学生作答，基于语义理解综合评判，不要机械匹配关键词。

题目：{question}
参考答案要点：{reference}
学生作答：{user_answer}

评判步骤（请在心中完成，不要输出步骤）：
1. 理解题目考查的知识点
2. 对照参考答案要点，看学生是否真正理解并表达清楚
3. 区分「学生实际写了什么」与「参考答案写了什么」，不得把参考要点当成学生已答内容
4. 给出 status 与 reason（reason 须基于学生原文，说明对/部分对/错的原因）

判定标准：
- correct：语义正确，覆盖参考答案主要要点
- partial：方向基本对但要点不完整，或有明显遗漏
- wrong：未作答、表示不会/不知道、答非所问、理解错误或要点严重缺失

仅输出一行 JSON，不要 markdown、不要其它文字：
{{"status":"correct或partial或wrong","reason":"30字内，基于学生作答说明"}}"""

SHORT_JUDGE_RETRY_PROMPT = """请将下列简答题按语义综合评判，严格输出一行 JSON（不要 markdown）：
{{"status":"correct或partial或wrong","reason":"30字内说明"}}

题目：{question}
参考答案要点：{reference}
学生作答：{user_answer}"""

# 编程题：结合本地测试结果
CODING_JUDGE_PROMPT = """你是 Python 代码阅卷老师。
题目：{question}
参考实现：
{reference}

学生代码：
{user_answer}

本地自动测试结果：{test_result}

规则：
1. 若本地测试「全部通过」，必须 correct=true
2. 若测试失败但代码逻辑明显正确（如输出格式差异），可 correct=true 并说明
3. 语法错误、逻辑错误、未实现要求 → correct=false

仅输出一行 JSON：{{"correct": true或false, "reason": "15字内理由"}}"""


@dataclass
class JudgeOutcome:
    is_correct: bool
    reason: str
    method: str  # local | ai | fallback
    is_partial: bool = False


def _outcome_from_parsed(parsed: dict, method: str) -> JudgeOutcome:
    reason = str(parsed.get("reason") or "AI 综合评判")
    status = str(parsed.get("status") or "").strip().lower()
    if status in ("correct", "right", "true", "对", "正确"):
        return JudgeOutcome(True, reason, method, False)
    if status in ("partial", "part", "部分", "部分正确"):
        return JudgeOutcome(False, reason, method, True)
    if status in ("wrong", "false", "错", "错误"):
        return JudgeOutcome(False, reason, method, False)
    if isinstance(parsed.get("correct"), bool):
        return JudgeOutcome(bool(parsed["correct"]), reason, method, False)
    return JudgeOutcome(False, reason, method, False)


def build_objective_judge_fields(
    is_correct: bool, judge_reason: str, judge_method: str = "local"
) -> dict:
    return {
        "is_correct": is_correct,
        "is_partial": False,
        "judge_label": "正确" if is_correct else "错误",
        "judge_reason": judge_reason,
        "judge_method": judge_method,
        "score_weight": 1.0 if is_correct else 0.0,
    }


def build_outcome_judge_fields(outcome: JudgeOutcome) -> dict:
    is_partial = bool(outcome.is_partial)
    is_correct = bool(outcome.is_correct) and not is_partial
    if is_correct:
        label = "正确"
    elif is_partial:
        label = "部分正确"
    else:
        label = "错误"
    score_weight = 1.0 if is_correct else (0.5 if is_partial else 0.0)
    return {
        "is_correct": is_correct,
        "is_partial": is_partial,
        "judge_label": label,
        "judge_reason": outcome.reason,
        "judge_method": outcome.method,
        "score_weight": score_weight,
    }


def _parse_judge_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        if isinstance(data, dict):
            status = str(data.get("status") or "").strip().lower()
            if status in ("correct", "partial", "wrong", "right", "true", "false", "错", "错误", "对", "正确", "部分", "部分正确"):
                return data
            if isinstance(data.get("correct"), bool):
                return data
    except json.JSONDecodeError:
        pass
    return None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def _split_answer_parts(raw: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,，、\s]+", (raw or "").strip()) if p.strip()]


def _match_option_key(part: str, options: dict | None) -> str | None:
    """将答案片段（选项字母或选项文本）映射为选项 key，如 A/B/C。"""
    part = (part or "").strip()
    if not part:
        return None
    part_up = part.upper()
    if isinstance(options, dict) and options:
        for k in options:
            if str(k).upper() == part_up:
                return str(k).upper()
        part_norm = _normalize_text(part)
        for k, v in options.items():
            v_norm = _normalize_text(str(v))
            if part_norm == v_norm or part_norm in v_norm or v_norm in part_norm:
                return str(k).upper()
    if len(part_up) == 1 and part_up.isalpha():
        return part_up
    return None


def _resolve_multi_letters(raw: str, options: dict | None = None) -> frozenset[str]:
    """将多选答案规范化为选项字母集合。"""
    parts = _split_answer_parts(raw)
    if not parts:
        return frozenset()
    letters: set[str] = set()
    for part in parts:
        key = _match_option_key(part, options)
        if key:
            letters.add(key)
        elif part:
            letters.add(part.upper()[0])
    return frozenset(letters)


def _format_option_label(key: str, options: dict | None) -> str:
    if not options:
        return key
    for k, v in options.items():
        if str(k).upper() == str(key).upper():
            return f"{str(k).upper()}（{v}）"
    return key


def _format_multi_expected(ref_set: frozenset[str], options: dict | None) -> str:
    if not ref_set:
        return ""
    if options:
        return "、".join(_format_option_label(k, options) for k in sorted(ref_set))
    return "、".join(sorted(ref_set))


def _normalize_multi_letters(raw: str) -> frozenset[str]:
    """将多选答案规范化为选项字母集合，如 'A,C' / 'AC' / 'A、C'。"""
    return _resolve_multi_letters(raw, None)


def judge_multi_choice(
    reference: str, user_answer: str, options: dict | None = None
) -> tuple[bool, str]:
    ref_set = _resolve_multi_letters(reference, options)
    user_set = _resolve_multi_letters(user_answer, options)
    if not user_set:
        return False, "未作答"
    if ref_set == user_set:
        return True, "选择正确"
    return False, f"正确答案为 {_format_multi_expected(ref_set, options)}"


def _run_single_coding_test(user_code: str, call_expr: str, expected, index: int) -> tuple[bool, object | None, str]:
    code = (user_code or "").strip()
    if not code:
        return False, None, "未提交代码"

    lines = [code, "", "if __name__ == '__main__':"]
    indent = "    "
    lines.append(f"{indent}_actual = {call_expr}")
    if expected is not None:
        exp_repr = json.dumps(expected, ensure_ascii=False)
        lines.append(
            f"{indent}assert _actual == {exp_repr} or str(_actual) == str({exp_repr}), "
            f"f'期望 {exp_repr!r}，实际 {{_actual!r}}'"
        )
    lines.append(f"{indent}print('__ACTUAL__:' + repr(_actual))")

    script = "\n".join(lines)
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        proc = subprocess.run(
            ["python", path],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if proc.returncode == 0:
            actual = None
            for line in stdout.splitlines():
                if line.startswith("__ACTUAL__:"):
                    raw = line.split(":", 1)[1]
                    try:
                        actual = ast.literal_eval(raw)
                    except (SyntaxError, ValueError):
                        actual = raw
            return True, actual, "通过"
        err = stderr or stdout or "运行失败"
        err_line = err.splitlines()[-1] if err else "断言失败"
        return False, None, err_line[:200]
    except subprocess.TimeoutExpired:
        return False, None, "代码执行超时（>8秒）"
    except Exception as exc:
        logger.warning("单项代码测试异常: %s", exc)
        return False, None, f"运行异常: {exc}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def run_coding_tests_detailed(user_code: str, test_cases: list[dict] | None) -> dict:
    """逐项运行验收用例，返回明细结果供前端展示。"""
    if not test_cases:
        return {"all_passed": None, "summary": "未配置验收用例", "cases": []}

    cases = []
    for i, tc in enumerate(test_cases):
        call_expr = tc.get("call") or tc.get("input") or ""
        if not call_expr:
            continue
        expected = tc.get("expected")
        passed, actual, message = _run_single_coding_test(user_code, call_expr, expected, i + 1)
        cases.append(
            {
                "index": len(cases) + 1,
                "call": call_expr,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "message": message,
            }
        )

    if not cases:
        return {"all_passed": None, "summary": "未配置验收用例", "cases": []}

    passed_n = sum(1 for c in cases if c["passed"])
    all_passed = passed_n == len(cases)
    if all_passed:
        summary = f"全部 {len(cases)} 项验收通过"
    else:
        summary = f"通过 {passed_n}/{len(cases)} 项，请根据未通过项修改代码"
    return {"all_passed": all_passed, "summary": summary, "cases": cases}


def run_coding_tests(user_code: str, test_cases: list[dict] | None) -> tuple[bool | None, str]:
    """
    在子进程中运行编程题测试用例。
    返回 (是否全部通过, 结果描述)；无测试用例时返回 (None, ...)。
    """
    if not test_cases:
        return None, "未配置自动测试，将使用 AI 判题"

    code = (user_code or "").strip()
    if not code:
        return False, "未提交代码"

    lines = [code, "", "if __name__ == '__main__':"]
    indent = "    "
    for i, tc in enumerate(test_cases):
        call_expr = tc.get("call") or tc.get("input") or ""
        expected = tc.get("expected")
        if not call_expr:
            continue
        lines.append(f"{indent}# test {i + 1}")
        lines.append(f"{indent}_actual = {call_expr}")
        if expected is not None:
            exp_repr = json.dumps(expected, ensure_ascii=False)
            lines.append(
                f"{indent}assert _actual == {exp_repr} or str(_actual) == str({exp_repr}), "
                f"f'test{i + 1}: got {{_actual!r}}, expected {exp_repr!r}'"
            )
        lines.append(f"{indent}print('test{i + 1}: ok')")

    script = "\n".join(lines)
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        proc = subprocess.run(
            ["python", path],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0:
            passed = len([tc for tc in test_cases if tc.get("call") or tc.get("input")])
            return True, f"全部 {passed} 项测试通过"
        err = (proc.stderr or proc.stdout or "运行失败").strip()
        err = err.splitlines()[-1] if err else "断言失败"
        return False, err[:200]
    except subprocess.TimeoutExpired:
        return False, "代码执行超时（>8秒）"
    except Exception as exc:
        logger.warning("代码测试运行异常: %s", exc)
        return False, f"运行异常: {exc}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _judge_short_with_ai(
    client: SparkLiteClient,
    question: str,
    reference: str,
    user_answer: str,
) -> JudgeOutcome | None:
    """调用星火 AI 综合评判；解析失败时重试一次。"""
    prompts = (
        SHORT_JUDGE_PROMPT.format(question=question, reference=reference, user_answer=user_answer),
        SHORT_JUDGE_RETRY_PROMPT.format(question=question, reference=reference, user_answer=user_answer),
    )
    last_raw = ""
    for i, prompt in enumerate(prompts):
        try:
            raw = client.chat(prompt, max_tokens=256)
            last_raw = raw
            parsed = _parse_judge_json(raw)
            if parsed:
                return _outcome_from_parsed(parsed, "ai")
            logger.warning("简答题 AI 返回无法解析(JSON): %s", raw[:300])
        except SparkClientError as exc:
            logger.warning("简答题 AI 判题失败(第%d次): %s", i + 1, exc)
            return None
        except Exception as exc:
            logger.warning("简答题 AI 判题异常(第%d次): %s", i + 1, exc)
            return None
    if last_raw:
        logger.warning("简答题 AI 两次均未返回可解析 JSON")
    return None


def judge_short_answer(question: str, reference: str, user_answer: str) -> JudgeOutcome:
    ans = (user_answer or "").strip()
    if not ans:
        return JudgeOutcome(False, "未作答", "local")

    try:
        client = SparkLiteClient()
        outcome = _judge_short_with_ai(client, question, reference, ans)
        if outcome:
            return outcome
    except SparkClientError as exc:
        logger.warning("简答题 AI 初始化失败: %s", exc)
    except Exception as exc:
        logger.warning("简答题 AI 判题异常: %s", exc)

    return JudgeOutcome(False, "AI 综合判题暂不可用，请稍后重新提交", "fallback")


def judge_coding_answer(
    question: str,
    reference: str,
    user_answer: str,
    test_cases: list[dict] | None = None,
) -> JudgeOutcome:
    ans = (user_answer or "").strip()
    if not ans:
        return JudgeOutcome(False, "未提交代码", "local")

    passed, test_msg = run_coding_tests(ans, test_cases)
    if passed is True:
        return JudgeOutcome(True, test_msg, "local")
    if passed is False and test_cases:
        # 测试失败时仍让 AI 综合判断（如 print 格式差异）
        try:
            client = SparkLiteClient()
            raw = client.chat(
                CODING_JUDGE_PROMPT.format(
                    question=question,
                    reference=reference,
                    user_answer=ans,
                    test_result=test_msg,
                ),
                max_tokens=256,
            )
            parsed = _parse_judge_json(raw)
            if parsed:
                return JudgeOutcome(
                    bool(parsed["correct"]),
                    str(parsed.get("reason") or test_msg),
                    "ai",
                )
        except Exception as exc:
            logger.warning("编程题 AI 判题失败: %s", exc)
        return JudgeOutcome(False, test_msg, "local")

    # 无测试用例：AI + 代码结构兜底
    try:
        client = SparkLiteClient()
        raw = client.chat(
            CODING_JUDGE_PROMPT.format(
                question=question,
                reference=reference,
                user_answer=ans,
                test_result="无自动测试",
            ),
            max_tokens=256,
        )
        parsed = _parse_judge_json(raw)
        if parsed:
            return JudgeOutcome(
                bool(parsed["correct"]),
                str(parsed.get("reason") or ""),
                "ai",
            )
    except Exception as exc:
        logger.warning("编程题 AI 判题失败: %s", exc)

    # 兜底：normalize 后比较核心 def 名或关键语句
    ref_norm = _normalize_text(reference)
    ans_norm = _normalize_text(ans)
    if ref_norm and (ref_norm in ans_norm or ans_norm in ref_norm):
        return JudgeOutcome(True, "代码结构与参考实现相近", "fallback")
    defs_ref = set(re.findall(r"def\s+(\w+)", reference))
    defs_ans = set(re.findall(r"def\s+(\w+)", ans))
    if defs_ref and defs_ref <= defs_ans and "return" in ans.lower():
        return JudgeOutcome(True, "函数定义符合要求", "fallback")
    return JudgeOutcome(False, "代码未满足题目要求", "fallback")
