"""从内置知识树与题库生成可阅读的讲义、代码案例与习题预览。"""
from __future__ import annotations

import ast
import random
import re

from knowledge_data import EXERCISE_BANK, KNOWLEDGE_TREE, MODULE_NAMES

def _module_exercises(module_name: str) -> list[tuple[str, str, dict, str]]:
    bank = EXERCISE_BANK.get(module_name) or {}
    out = []
    for diff in sorted(bank.keys()):
        for item in bank[diff]:
            kp, content, opts, ans = item
            out.append((kp, content, opts, ans))
    return out


def build_lecture_markdown(module_name: str, score: float | None, weakness: str, focus: str) -> str:
    kps = KNOWLEDGE_TREE.get(module_name) or [f"{module_name}-基础", f"{module_name}-应用"]
    exercises = _module_exercises(module_name)

    lines = [
        f"# {module_name}",
        "",
        f"**掌握度参考**：{score if score is not None else '—'} 分 · 侧重 **{focus}**",
        "",
        "## 一、学习目标",
        "",
        f"- 理解「{kps[0]}」核心概念",
        f"- 能在简单场景中应用「{kps[1] if len(kps) > 1 else module_name}」",
        "- 能识别并避免本模块常见错误",
        "",
        "## 二、核心知识点",
        "",
    ]
    for i, kp in enumerate(kps, 1):
        lines.append(f"### {i}. {kp}")
        lines.append("")
        lines.append(f"- **定义与要点**：围绕「{kp}」梳理语法规则与使用场景。")
        lines.append(f"- **易错提醒**：{weakness or '注意边界条件与类型匹配'}。")
        lines.append("")

    if exercises:
        lines.extend(["## 三、巩固例题", ""])
        for idx, (kp, q, opts, ans) in enumerate(exercises[:2], 1):
            lines.append(f"**例题 {idx}**（{kp}）")
            lines.append("")
            lines.append(q)
            lines.append("")
            for key in sorted(opts.keys()):
                lines.append(f"- **{key}**. {opts[key]}")
            lines.append("")
            lines.append(f"> 参考答案：**{ans}**")
            lines.append("")

    lines.extend(
        [
            "## 四、学习建议",
            "",
            "1. 先通读本讲义，再观看配套优秀代码案例与习题。",
            "2. 在习题中心完成本模块专项练习，错题会自动归入错题本。",
            "3. 如需更完整 AI 讲义，可点击「星火 AI 深度生成」。",
        ]
    )
    return "\n".join(lines)


def parse_test_cases_from_markdown(content: str) -> list[dict]:
    """从课件 Markdown 的「验收标准」条目中解析测试用例。"""
    cases = []
    for match in re.finditer(r"-\s*执行\s*`([^`]+)`，期望结果为\s*`([^`]+)`", content or ""):
        call_expr = match.group(1).strip()
        expected_raw = match.group(2).strip()
        try:
            expected = ast.literal_eval(expected_raw)
        except (SyntaxError, ValueError):
            expected = expected_raw.strip("'\"")
        cases.append({"call": call_expr, "expected": expected})
    return cases


def _showcase_level_hint(module_name: str, score: float | None, focus: str | None) -> str:
    focus_text = focus or "规范实现"
    if score is None:
        return f"根据当前学情，为你精选「{module_name}」模块的优秀代码写法，侧重 **{focus_text}**。"
    if score < 45:
        return (
            f"你在「{module_name}」掌握度为 **{score} 分**，推荐先阅读结构清晰、"
            f"注释完整的优秀案例，重点理解 **{focus_text}** 与常见写法。"
        )
    if score >= 85:
        return (
            f"你在「{module_name}」已有较好基础（**{score} 分**），本案例展示更规范的工程化写法"
            f"与边界处理细节，可对照 **{focus_text}** 提升代码质量。"
        )
    return (
        f"你在「{module_name}」当前 **{score} 分**，推荐通过优秀案例理解 **{focus_text}** 的标准实现方式。"
    )


def build_courseware_markdown(
    module_name: str,
    module_id: int = 0,
    score: float | None = None,
    weakness: str | None = None,
    focus: str | None = None,
) -> str:
    """生成可观看学习的优秀代码案例（非实操练习）。"""
    challenge = get_coding_challenge(module_name, module_id)
    weakness_hint = weakness or "注意边界条件与可读性"
    lines = [
        f"## {module_name} · 优秀代码案例",
        "",
        "### 推荐理由",
        "",
        _showcase_level_hint(module_name, score, focus),
        "",
        "### 应用场景",
        "",
        challenge["content"],
        "",
        "### 优秀实现",
        "",
        "以下代码为推荐学习的规范写法（含完整逻辑与注释思路），建议逐行阅读：",
        "",
        f"```python\n{challenge['answer']}\n```",
        "",
        "### 代码要点",
        "",
        f"- {challenge.get('analysis', '关注函数职责单一、命名清晰。')}",
        f"- **易错提醒**：{weakness_hint}。",
        "",
        "### 运行效果参考",
        "",
    ]
    tests = challenge.get("test_cases") or []
    if tests:
        for item in tests:
            lines.append(f"- `{item['call']}` → 输出 `{item['expected']}`")
    else:
        lines.append("- 代码可直接运行，建议点击「运行演示」查看实际输出。")
    lines.extend(
        [
            "",
            "> **观看提示**：本资源用于学习优秀写法。如需动手练习与自动判题，请前往 **习题中心** 或 **模块练习**。",
        ]
    )
    return "\n".join(lines)


def get_coding_challenge(module_name: str, module_id: int) -> dict:
    templates = {
        "Python环境与基础语法": (
            "编写函数 `greet(name)`，返回 `'Hello, {name}'` 格式的问候字符串。",
            "def greet(name):\n    # 返回问候语，例如 greet('Py') -> 'Hello, Py'\n    pass",
            "def greet(name):\n    return f'Hello, {name}'",
            [{"call": "greet('Py')", "expected": "Hello, Py"}, {"call": "greet('')", "expected": "Hello, "}],
            "可使用 f-string 拼接固定前缀与姓名参数。",
        ),
        "变量、数据类型与运算符": (
            "编写函数 `add(a, b)`，返回两数之和。",
            "def add(a, b):\n    # 返回 a 与 b 的和\n    pass",
            "def add(a, b):\n    return a + b",
            [{"call": "add(2, 3)", "expected": 5}, {"call": "add(-1, 1)", "expected": 0}],
            "注意支持负整数相加。",
        ),
        "流程控制：条件与循环": (
            "编写函数 `is_even(n)`，判断整数 `n` 是否为偶数，是则返回 `True`，否则返回 `False`。",
            "def is_even(n):\n    # 使用取模或位运算判断奇偶\n    pass",
            "def is_even(n):\n    return n % 2 == 0",
            [{"call": "is_even(4)", "expected": True}, {"call": "is_even(3)", "expected": False}],
            "可使用 `n % 2 == 0` 判断。",
        ),
        "组合数据结构：列表/元组/字典/集合": (
            "编写函数 `sum_list(nums)`，返回列表 `nums` 中所有元素之和；空列表返回 `0`。",
            "def sum_list(nums):\n    # 遍历列表并累加\n    pass",
            "def sum_list(nums):\n    return sum(nums)",
            [{"call": "sum_list([1, 2, 3])", "expected": 6}, {"call": "sum_list([])", "expected": 0}],
            "可直接使用内置 `sum`，或手写循环累加。",
        ),
        "函数、高阶函数与装饰器": (
            "编写函数 `square(x)`，返回 `x` 的平方。",
            "def square(x):\n    # 返回 x * x\n    pass",
            "def square(x):\n    return x * x",
            [{"call": "square(3)", "expected": 9}, {"call": "square(0)", "expected": 0}],
            "注意 0 的平方仍为 0。",
        ),
        "异常处理与调试": (
            "编写函数 `safe_divide(a, b)` 做两数相除：若 `b` 为 0，捕获 `ZeroDivisionError` 并返回 `None`；否则返回相除结果。",
            "def safe_divide(a, b):\n    # 使用 try/except 处理除零异常\n    pass",
            "def safe_divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return None",
            [
                {"call": "safe_divide(10, 2)", "expected": 5.0},
                {"call": "safe_divide(10, 0)", "expected": None},
            ],
            "除法前不必手动 if 判断，优先用 try/except 捕获异常。",
        ),
        "字符串与正则表达式": (
            "编写函数 `count_vowels(text)`，统计字符串中英文字母元音（a/e/i/o/u，不区分大小写）出现次数。",
            "def count_vowels(text):\n    # 遍历字符并统计元音\n    pass",
            "def count_vowels(text):\n    vowels = 'aeiouAEIOU'\n    return sum(1 for ch in text if ch in vowels)",
            [
                {"call": "count_vowels('Hello')", "expected": 2},
                {"call": "count_vowels('xyz')", "expected": 0},
            ],
            "可先统一转小写再判断，或同时匹配大小写元音。",
        ),
        "模块、包与虚拟环境": (
            "编写函数 `describe_module(mod_name)`，返回 `'module:{name}'` 格式字符串，用于模拟记录模块名。",
            "def describe_module(mod_name):\n    # 返回固定格式的描述字符串\n    pass",
            "def describe_module(mod_name):\n    return f'module:{mod_name}'",
            [
                {"call": "describe_module('math')", "expected": "module:math"},
                {"call": "describe_module('os')", "expected": "module:os"},
            ],
            "练习字符串格式化与函数封装，后续可扩展为真实 import。",
        ),
        "面向对象编程": (
            "定义类 `Student`，包含属性 `name` 与 `score`；实现方法 `passed()`，当 `score >= 60` 时返回 `True`。",
            "class Student:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n\n    def passed(self):\n        # 判断是否及格\n        pass",
            "class Student:\n    def __init__(self, name, score):\n        self.name = name\n        self.score = score\n\n    def passed(self):\n        return self.score >= 60",
            [
                {"call": "Student('Amy', 80).passed()", "expected": True},
                {"call": "Student('Bob', 55).passed()", "expected": False},
            ],
            "在 `__init__` 中保存属性，`passed` 中比较分数与 60。",
        ),
        "文件IO与数据持久化": (
            "编写函数 `line_count(text)`，统计多行字符串 `text` 的行数（按换行符 `\\n` 分割）。",
            "def line_count(text):\n    # 空字符串返回 0，否则按换行统计\n    pass",
            "def line_count(text):\n    if not text:\n        return 0\n    return len(text.splitlines())",
            [
                {"call": "line_count('a\\nb\\nc')", "expected": 3},
                {"call": "line_count('')", "expected": 0},
            ],
            "可使用 `splitlines()` 处理不同换行情况。",
        ),
        "网络请求与API调用": (
            "编写函数 `pick_status(response)`，从模拟响应字典中安全取出 `status` 字段；不存在时返回 `'unknown'`。",
            "def pick_status(response):\n    # response 为 dict，例如 {'status': 'ok'}\n    pass",
            "def pick_status(response):\n    return response.get('status', 'unknown')",
            [
                {"call": "pick_status({'status': 'ok'})", "expected": "ok"},
                {"call": "pick_status({'code': 200})", "expected": "unknown"},
            ],
            "使用 `dict.get(key, default)` 避免 KeyError。",
        ),
        "基础算法与代码规范": (
            "编写函数 `find_max(nums)`，返回列表中的最大值；要求列表非空。",
            "def find_max(nums):\n    # 遍历比较，返回最大值\n    pass",
            "def find_max(nums):\n    current = nums[0]\n    for n in nums[1:]:\n        if n > current:\n            current = n\n    return current",
            [
                {"call": "find_max([3, 9, 2])", "expected": 9},
                {"call": "find_max([-1, -5])", "expected": -1},
            ],
            "可手写遍历，也可在理解基础上使用内置 max。",
        ),
    }
    tpl = templates.get(module_name) or (
        f"编写函数 `practice()`，根据模块「{module_name}」完成一个最小可运行示例，并返回 `True` 表示完成。",
        f"def practice():\n    # 围绕「{module_name}」完成练习逻辑\n    print('模块: {module_name}')\n    return True\n\nif __name__ == '__main__':\n    practice()",
        f"def practice():\n    print('模块: {module_name}')\n    return True",
        [{"call": "practice()", "expected": True}],
        "先保证函数可运行，再逐步完善与当前模块相关的逻辑。",
    )
    content, starter_code, answer, tests, analysis = tpl
    return {
        "qid": f"code-{module_id}",
        "type": "coding",
        "content": content,
        "starter_code": starter_code,
        "options": {},
        "answer": answer,
        "analysis": analysis,
        "test_cases": tests,
        "module_id": module_id,
        "module_name": module_name,
    }


def collect_module_questions(module_id: int, module_name: str | None = None) -> list[dict]:
    """汇总模块全部可练题目，qid 稳定，供预览抽题与习题中心按 id 出题。"""
    from models import Exercise, KnowledgePoint

    mod_name = module_name
    if not mod_name:
        from models import SubjectModule

        mod = SubjectModule.query.get(module_id)
        if not mod:
            return []
        mod_name = mod.module_name

    questions: list[dict] = []
    kp_list = KnowledgePoint.query.filter_by(module_id=module_id).order_by(KnowledgePoint.kp_id).all()
    for kp in kp_list:
        for ex in Exercise.query.filter_by(kp_id=kp.kp_id).all():
            qtype = ex.question_type or "choice"
            if qtype not in ("choice", "judge", "short", "coding"):
                qtype = "choice"
            questions.append(
                {
                    "qid": str(ex.ex_id),
                    "type": qtype,
                    "content": ex.content,
                    "options": ex.options_dict(),
                    "answer": ex.answer,
                    "analysis": "",
                    "module_id": module_id,
                    "module_name": mod_name,
                    "kp_name": kp.kp_name,
                }
            )

    bank = EXERCISE_BANK.get(mod_name) or {}
    bank_idx = 0
    for diff in sorted(bank.keys()):
        for item in bank[diff]:
            kp_name, content, opts, ans = item
            questions.append(
                {
                    "qid": f"bank-{module_id}-{bank_idx}",
                    "type": "choice",
                    "content": content,
                    "options": opts,
                    "answer": ans,
                    "analysis": f"参见「{kp_name}」讲义。",
                    "module_id": module_id,
                    "module_name": mod_name,
                    "kp_name": kp_name,
                }
            )
            bank_idx += 1

    coding = get_coding_challenge(mod_name, module_id)
    if coding:
        questions.append(coding)
    return questions


def pick_preview_exercises(
    module_id: int,
    module_name: str,
    student_id: int,
    seed: int | str,
    count: int = 3,
) -> list[dict]:
    """按学情种子为本轮资源计划抽取习题（每次生成/刷新计划会换题）。"""
    pool = collect_module_questions(module_id, module_name)
    if not pool:
        return []
    count = min(count, len(pool))
    rng = random.Random(f"{student_id}:{module_id}:{seed}")
    return rng.sample(pool, count)


def build_exercise_preview_bundle(
    module_id: int,
    module_name: str,
    student_id: int,
    seed: int | str,
    count: int = 3,
    score: float | None = None,
    focus: str | None = None,
) -> dict:
    """系统预览：专项习题需通过「星火 AI 深度生成」写入，此处仅作占位说明。"""
    score_text = f"{score} 分" if score is not None else "当前学情"
    focus_text = focus or "薄弱点巩固"
    lines = [
        f"## {module_name} · 专项习题（待生成）",
        "",
        f"本模块掌握参考 **{score_text}**，侧重 **{focus_text}**。",
        "",
        "专项习题将在您点击 **「星火 AI 深度生成」** 时，由习题智能体（EXERCISE）",
        "结合当时画像薄弱点与讲义内容 **一次性生成并保存**；",
        "生成后可在本页预览题目，并在习题中心作答（**同一批题，不会每次随机换题**）。",
        "",
        "> 与「模块能力训练」不同：专项习题针对本批薄弱点精编；模块训练每次调用 AI 综合出题。",
        "",
        "**请先点击页面上方「星火 AI 深度生成」。**",
    ]
    return {
        "content": "\n".join(lines),
        "item_ids": [],
        "question_count": count,
        "ai_generated": False,
        "pending_generate": True,
    }


def build_exercise_preview(module_name: str) -> str:
    """兼容旧调用：无学情种子时仍返回静态前三题。"""
    exercises = _module_exercises(module_name)
    if not exercises:
        return f"## {module_name} 巩固练习\n\n暂无内置题目，请触发星火 AI 生成专项习题。"
    lines = [f"## {module_name} · 巩固练习", "", "以下题目可在「习题中心」在线作答并自动判分。", ""]
    for i, (kp, q, opts, ans) in enumerate(exercises[:3], 1):
        lines.append(f"### 第 {i} 题（{kp}）")
        lines.append("")
        lines.append(q)
        lines.append("")
        for key in sorted(opts.keys()):
            lines.append(f"- {key}. {opts[key]}")
        lines.append("")
    lines.append("> 点击「前往习题中心作答」提交答案。")
    return "\n".join(lines)
