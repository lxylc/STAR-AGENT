"""讯飞结构化抽取：由星火 AI 判断句意并输出自评结构化结果。"""
import json
import logging
import re

from config import Config
from services.spark_client import SparkClientError, SparkLiteClient

logger = logging.getLogger(__name__)

MASTERY_LEVELS = ("精通", "熟练", "一般", "薄弱")
WEAKNESS_TYPES = ("理解薄弱", "应用薄弱", "记忆薄弱", "无短板")
CODE_PRACTICE = ("实操顺畅", "实操困难")
PRACTICE_FREQ = ("经常练习", "偶尔练习", "很少练习")

ASSESS_PROMPT = """你是 Python 学习画像助手。学生正在自评对模块「{module_name}」的掌握情况。

请根据句意判断学生描述是否有效，并抽取结构化信息。输出 JSON（仅 JSON，无其他文字）：
{{
  "accepted": true 或 false,
  "reject_reason": "none|too_vague|off_topic|meaningless",
  "reject_hint": "若 accepted 为 false，用一句简短中文提示学生如何补充；accepted 为 true 时留空字符串",
  "mastery_level": "精通|熟练|一般|薄弱",
  "weakness_type": "理解薄弱|应用薄弱|记忆薄弱|无短板",
  "code_practice_feel": "实操顺畅|实操困难",
  "practice_frequency": "经常练习|偶尔练习|很少练习",
  "confidence": 0.0-1.0,
  "evidence": "一句话依据"
}}

判断标准（务必按语义理解，不要机械匹配关键词）：
- accepted=true：学生在表达对该知识点的理解程度、学习难点、做题/代码练习感受等；短句如「不太熟练」「题目大多做不出来」也算有效
- accepted=false 且 reject_reason=too_vague：与 Python 学习有关但过于空泛，无法判断掌握程度（如「还行吧」「一般般」且无具体信息）
- accepted=false 且 reject_reason=off_topic：内容与 Python 或当前知识点无关
- accepted=false 且 reject_reason=meaningless：无意义、敷衍或仅单字（如「好」「嗯」「1」）

学生描述：
{text}
"""


def _clamp_enum(value: str, allowed: tuple[str, ...], default: str) -> str:
    v = (value or "").strip()
    for a in allowed:
        if a in v or v == a:
            return a
    return default


def _parse_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def _default_assessment(module_id: int, module_name: str) -> dict:
    """星火不可用时的保守默认，避免关键词误判。"""
    return {
        "module_id": module_id,
        "module_name": module_name,
        "mastery_level": "一般",
        "weakness_type": "无短板",
        "code_practice_feel": "实操困难",
        "practice_frequency": "偶尔练习",
        "confidence": 0.5,
        "evidence": "AI 服务暂不可用，采用默认中等评估",
        "initial_level": Config.MASTERY_TO_LEVEL["一般"],
    }


def normalize_extract(data: dict, module_id: int, module_name: str) -> dict:
    return {
        "module_id": module_id,
        "module_name": module_name,
        "mastery_level": _clamp_enum(data.get("mastery_level"), MASTERY_LEVELS, "一般"),
        "weakness_type": _clamp_enum(data.get("weakness_type"), WEAKNESS_TYPES, "无短板"),
        "code_practice_feel": _clamp_enum(data.get("code_practice_feel"), CODE_PRACTICE, "实操困难"),
        "practice_frequency": _clamp_enum(data.get("practice_frequency"), PRACTICE_FREQ, "偶尔练习"),
        "confidence": float(data.get("confidence") or 0.7),
        "evidence": (data.get("evidence") or "")[:200],
    }


def _call_spark_assess(module_name: str, text: str) -> dict | None:
    prompt = ASSESS_PROMPT.format(module_name=module_name, text=text)
    client = SparkLiteClient()
    raw = client.chat(prompt, max_tokens=512)
    return _parse_json(raw)


def extract_module_assessment(module_id: int, module_name: str, text: str) -> dict:
    """
    自由文本 → 星火语义判定 + 结构化自评。
    不再使用本地关键词规则判断有效性或掌握度。
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "valid": False,
            "reason": "empty",
            "reject_hint": None,
            "data": None,
        }

    last_error = None
    for attempt in range(2):
        try:
            parsed = _call_spark_assess(module_name, cleaned)
            if not parsed:
                last_error = "parse_error"
                continue

            accepted = parsed.get("accepted")
            if accepted is False or str(accepted).lower() == "false":
                reason = (parsed.get("reject_reason") or "too_vague").strip()
                if reason not in ("too_vague", "off_topic", "meaningless"):
                    reason = "too_vague"
                return {
                    "valid": False,
                    "reason": reason,
                    "reject_hint": (parsed.get("reject_hint") or "").strip() or None,
                    "data": None,
                }

            norm = normalize_extract(parsed, module_id, module_name)
            conf = float(norm.get("confidence") or 0)
            if conf < 0.5:
                return {
                    "valid": False,
                    "reason": "too_vague",
                    "reject_hint": (parsed.get("reject_hint") or "").strip() or None,
                    "data": None,
                }

            norm["initial_level"] = Config.MASTERY_TO_LEVEL[norm["mastery_level"]]
            return {"valid": True, "reason": "ok", "reject_hint": None, "data": norm}

        except SparkClientError as exc:
            last_error = "spark_error"
            logger.warning(
                "Spark 自评抽取失败 module=%s attempt=%s: %s",
                module_id,
                attempt + 1,
                exc,
            )
        except Exception as exc:
            last_error = "spark_error"
            logger.warning(
                "自评抽取异常 module=%s attempt=%s: %s",
                module_id,
                attempt + 1,
                exc,
            )

    return {
        "valid": False,
        "reason": last_error or "spark_error",
        "reject_hint": None,
        "data": None,
    }


def default_assessment_fallback(module_id: int, module_name: str) -> dict:
    """供对话流程在多次 API 失败后使用。"""
    return _default_assessment(module_id, module_name)
