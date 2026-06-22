"""LLM 不可用时的关键词兜底抽取。"""

_KEYWORDS_LEVEL = [
    (("精通", "非常熟悉", "写过项目", "熟练运用"), "精通"),
    (("熟练", "比较熟", "能写", "做过"), "熟练"),
    (("一般", "了解一点", "学过", "知道"), "一般"),
    (("不会", "没学过", "不懂", "薄弱", "零基础", "不太熟练", "无法独立"), "薄弱"),
]

_KEYWORDS_WEAK = [
    (("看不懂", "概念模糊", "不理解"), "理解薄弱"),
    (("写不出", "不会写", "应用", "练习少", "无法独立", "做不出", "题目"), "应用薄弱"),
    (("记不住", "语法记", "背"), "记忆薄弱"),
]

_KEYWORDS_PRACTICE = [
    (("经常", "每天练", "刷题"), "经常练习"),
    (("很少", "几乎不", "没练"), "很少练习"),
]


def keyword_extract(text: str, module_id: int, module_name: str) -> dict:
    t = text or ""
    mastery = "一般"
    for keys, level in _KEYWORDS_LEVEL:
        if any(k in t for k in keys):
            mastery = level
            break

    weakness = "无短板"
    for keys, w in _KEYWORDS_WEAK:
        if any(k in t for k in keys):
            weakness = w
            break

    practice = "偶尔练习"
    for keys, p in _KEYWORDS_PRACTICE:
        if any(k in t for k in keys):
            practice = p
            break

    code_feel = "实操困难" if any(k in t for k in ("困难", "不会写", "报错", "卡住")) else "实操顺畅"

    return {
        "module_id": module_id,
        "module_name": module_name,
        "mastery_level": mastery,
        "weakness_type": weakness,
        "code_practice_feel": code_feel,
        "practice_frequency": practice,
        "confidence": 0.65,
        "evidence": "关键词规则推断",
    }
