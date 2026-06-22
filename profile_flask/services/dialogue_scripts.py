"""对话式学习画像 — 话术与反馈文案。"""

from config import Config

WELCOME = (
    "你好，接下来我们逐一了解 Python 各知识点的学习情况，"
    "你可以自由说说理解程度与代码练习感受。准备好了吗？"
)

MODULE_ASSESS_GLOBAL = (
    "我们现在开始第一个模块。请依次描述你对每个知识点的学习情况。"
)

def module_assess_prompt(module_name: str) -> str:
    return f"请说说你对【{module_name}】的学习情况。"

ASSESS_RECORDED = "已记录，我们继续下一个知识点。"
ASSESS_TOO_SHORT = "可以简单讲讲学习难点或是代码练习情况哦。"
ASSESS_OFF_TOPIC = "请聚焦当前 Python 知识点进行描述哈。"
ASSESS_WEAK_HINT = "该知识点基础较为薄弱，后续可以多动手练习代码哦。"

MODULE_ASSESS_DONE = "所有知识点沟通完毕，接下来完成几道小题核验，你可以慢慢作答。"
QUIZ_INTRO = "所有知识点沟通完毕，接下来完成几道小题核验，你可以慢慢作答。"
QUIZ_CORRECT = "回答正确。"
QUIZ_WRONG = "回答有误。不用着急，继续作答。"
QUIZ_NEXT = "继续下一题。"
QUIZ_DONE = (
    "所有测评已完成，专属学习画像已生成，你可以点击上方「查看我的画像」查看。"
    "现在你可以随时提问 Python 相关问题。"
)

RESUME_PROMPT = "检测到你有未完成的测评，是否继续上次进度？"
RESUME_CONTINUE = "好的，我们接着之前的内容继续。"
RESUME_RESET = "已重置进度，我们重新开始测评。"
CLEAR_CHAT_OK = "聊天记录已清空，学习进度与画像数据不会受到影响。"
PROFILE_REQUIRED = "请先完成学习测评，生成专属画像"
QA_OFF_TOPIC = "抱歉，我主要为你解答 Python 学习相关问题。"
SPARK_FALLBACK = "当前 AI 服务临时受限，我们继续完成学习流程。"

# 兼容旧流程选项（settings 页仍可用）
GRADE_OPTIONS = ["大一", "大二", "大三", "大四", "研究生", "其他"]
MAJOR_OPTIONS = [
    "计算机科学与技术", "软件工程", "人工智能", "数据科学", "电子信息", "其他",
]
LEARN_PREFERENCE_OPTIONS = [
    {"value": "理论阅读", "label": "理论阅读"},
    {"value": "代码实操", "label": "代码实操"},
    {"value": "例题演练", "label": "例题演练"},
    {"value": "视频讲解", "label": "视频讲解"},
    {"value": "图文图解", "label": "图文图解"},
]
PREFERENCE_LABELS = {opt["value"]: opt["label"] for opt in LEARN_PREFERENCE_OPTIONS}


def level_options_dto() -> list[dict]:
    return [
        {"key": k, "level": v, "label": Config.LEVEL_LABELS[v]}
        for k, v in Config.LEVEL_OPTIONS.items()
    ]


def quiz_question_prompt(index: int, content: str, module_name: str = "") -> str:
    prefix = f"第{index}题"
    if module_name:
        prefix += f"（{module_name}）"
    return f"{prefix}：{content}"


def quiz_feedback(is_correct: bool, explanation: str = "") -> str:
    base = QUIZ_CORRECT if is_correct else QUIZ_WRONG
    if explanation:
        return f"{base}{explanation}"
    return base

