"""多模态智能辅导 — 文字解答、图解说明、B 站视频推荐 + 上下文答疑。"""
import json
import logging
import re
from uuid import uuid4

from services.bilibili_video_service import recommend_bilibili_videos
from services.behavior_event_service import record_event
from services.dialogue_service import append_message, list_messages
from services.mongo_client import dialogue_collection, ensure_indexes
from services.qa_service import _apply_mastery_updates, _load_kp_catalog, _parse_analyze_json
from services.spark_client import SparkClientError, SparkLiteClient

logger = logging.getLogger(__name__)

TUTORING_SESSION_PREFIX = "tutor-"
TUTORING_WELCOME = (
    "你好！这里是智能辅导区。你可以提问 Python 知识点，我会提供文字解答、Mermaid 图解说明，"
    "并推荐 B 站视频讲解。在学习资源页也可针对当前内容发起辅导。"
)

TUTORING_SYSTEM = """你是 Python 程序设计课程的智能辅导助手，面向大学生。
根据学生问题提供深入、易懂的学习引导。文字解答要充实具体，避免一两句话带过。
输出结构化 JSON（仅 JSON，不要 markdown 代码块）。
text_answer 内换行请用 \\n，代码示例请用单引号，不要使用未转义的双引号。"""

TUTORING_PROMPT = """{system}

学生问题：{question}
{context_block}

请输出 JSON，字段说明：
- text_answer: 详细文字解答（500-800字，分段清晰，不要包含代码块），须包含：
  1）核心概念；2）原理或适用场景；3）用文字描述示例思路（不要写代码）；
  4）常见误区；5）学习建议。语气清晰友好。
- code_snippets: ["示例1代码", "示例2代码"]（1-2 段 Python 代码字符串，代码内只用单引号，勿用双引号）
- diagram: {{ "title": "图解标题", "mermaid": "mermaid 流程图/思维导图语法，节点用中文" }}
- follow_up_actions: [
    {{ "action": "regenerate_exercise", "label": "再生成一套题" }},
    {{ "action": "change_difficulty", "label": "换难度练习" }},
    {{ "action": "view_resource", "label": "查看相关资源" }}
  ]（保留 2-4 个合适动作）
- related_kps: ["相关知识点名，最多3个"]

若问题与 Python 无关，text_answer 中礼貌说明并 related_kps 为空数组。"""

ANALYZE_PROMPT = """分析以下 Python 智能辅导对话，判断涉及哪些知识点及掌握度变化。

可选知识点（仅从此列表选择，名称需完全一致）：
{kp_list}

对话：
学生：{question}
助手：{answer}

规则：正确理解 delta=+1，明显误解 delta=-1，无法判断 delta=0。最多 3 个知识点。
仅输出 JSON：{{"updates":[{{"kp_name":"知识点名","delta":0,"reason":"简短原因"}}]}}"""


def tutoring_session_id(student_id: int) -> str:
    return f"{TUTORING_SESSION_PREFIX}{student_id}"


def new_tutoring_session_id(student_id: int) -> str:
    return f"{TUTORING_SESSION_PREFIX}{student_id}-{uuid4().hex[:8]}"


def validate_tutoring_session_id(student_id: int, session_id: str) -> str:
    sid = (session_id or "").strip()
    prefix = f"{TUTORING_SESSION_PREFIX}{student_id}"
    if not sid.startswith(prefix):
        raise ValueError("无效的辅导会话")
    return sid


def get_latest_tutoring_session_id(student_id: int) -> str | None:
    """返回该学生最近一次辅导会话 ID。"""
    try:
        ensure_indexes()
    except Exception:
        return None
    prefix = f"{TUTORING_SESSION_PREFIX}{student_id}"
    cursor = (
        dialogue_collection()
        .find({"student_id": student_id, "session_id": {"$regex": f"^{re.escape(prefix)}"}})
        .sort("created_at", -1)
        .limit(1)
    )
    for doc in cursor:
        sid = doc.get("session_id")
        if sid:
            return sid
    return None


def _append_tutoring_welcome(student_id: int, session_id: str) -> None:
    append_message(
        student_id,
        "assistant",
        "tutoring_welcome",
        TUTORING_WELCOME,
        session_id=session_id,
    )


def resolve_tutoring_session_id(student_id: int, session_id: str | None = None) -> str:
    if session_id:
        return validate_tutoring_session_id(student_id, session_id)
    return get_latest_tutoring_session_id(student_id) or tutoring_session_id(student_id)


def _build_context_block(context: dict | None) -> str:
    if not context:
        return "（无额外上下文）"
    parts = []
    if context.get("knowledge_point"):
        parts.append(f"当前知识点：{context['knowledge_point']}")
    if context.get("resource_title"):
        parts.append(f"关联资源：{context['resource_title']}")
    if context.get("resource_excerpt"):
        excerpt = str(context["resource_excerpt"])[:800]
        parts.append(f"资源摘要：{excerpt}")
    if context.get("code_snippet"):
        parts.append(f"学生代码片段：\n{context['code_snippet'][:1200]}")
    if context.get("image_description"):
        parts.append(f"学生图片描述：{context['image_description']}")
    return "\n".join(parts) if parts else "（无额外上下文）"


def _strip_json_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _unescape_json_string(value: str) -> str:
    return (
        (value or "")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def _extract_json_string_field(text: str, field_name: str) -> str:
    """从可能不合法的 JSON 文本中抽取字符串字段（支持裸换行）。"""
    pattern = rf'"{re.escape(field_name)}"\s*:\s*"'
    match = re.search(pattern, text)
    if not match:
        return ""
    i = match.end()
    chars: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == '"':
            backslashes = 0
            j = i - 1
            while j >= match.end() - 1 and text[j] == "\\":
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                break
        chars.append(ch)
        i += 1
    return _unescape_json_string("".join(chars)).strip()


def _merge_parsed_fields(base: dict, extra: dict) -> dict:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if value in (None, "", [], {}):
            continue
        if key not in merged or merged.get(key) in (None, "", [], {}):
            merged[key] = value
    return merged
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|JSON)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _repair_trailing_commas(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)


def _repair_json_multiline_strings(text: str) -> str:
    """将 JSON 字符串值内的裸换行转为 \\n，修复 LLM 常见格式错误。"""
    out: list[str] = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escape:
            out.append(ch)
            escape = False
        elif ch == "\\" and in_string:
            out.append(ch)
            escape = True
        elif ch == '"':
            out.append(ch)
            in_string = not in_string
        elif ch in "\n\r" and in_string:
            out.append("\\n")
            if ch == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
                i += 1
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _extract_tutoring_fields_fallback(raw: str) -> dict:
    """JSON 解析失败时，按字段正则兜底抽取。"""
    text = _strip_json_fence(raw)
    result: dict = {}

    text_answer = _extract_json_string_field(text, "text_answer")
    if text_answer:
        result["text_answer"] = text_answer
    else:
        ta_match = re.search(
            r'"text_answer"\s*:\s*"([\s\S]*?)"\s*,\s*"(?:diagram|follow_up_actions|related_kps)"',
            text,
        )
        if ta_match:
            result["text_answer"] = ta_match.group(1).replace("\\n", "\n").strip()

    title_match = re.search(r'"diagram"\s*:\s*\{[\s\S]*?"title"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    mermaid_match = re.search(
        r'"mermaid"\s*:\s*"([\s\S]*?)"\s*\n\s*\}',
        text,
    )
    if title_match or mermaid_match:
        result["diagram"] = {
            "title": (title_match.group(1) if title_match else "概念图解").replace("\\n", "\n"),
            "mermaid": (mermaid_match.group(1) if mermaid_match else "").replace("\\n", "\n").strip(),
        }

    kp_match = re.search(r'"related_kps"\s*:\s*(\[[\s\S]*?\])', text)
    if kp_match:
        try:
            result["related_kps"] = json.loads(_repair_json_multiline_strings(kp_match.group(1)))
        except json.JSONDecodeError:
            pass

    code_snippets = _extract_json_array_field(text, "code_snippets")
    if code_snippets:
        result["code_snippets"] = code_snippets

    return result


def _parse_tutoring_json(raw: str) -> dict:
    text = _strip_json_fence(raw)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return _extract_tutoring_fields_fallback(raw)

    blob = match.group()
    candidates = [
        blob,
        _repair_trailing_commas(blob),
        _repair_json_multiline_strings(blob),
        _repair_trailing_commas(_repair_json_multiline_strings(blob)),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    fallback = _extract_tutoring_fields_fallback(raw)
    if fallback.get("text_answer"):
        logger.warning("智能辅导 JSON 解析失败，已使用字段兜底抽取")
    return fallback


def _ensure_parsed_text_answer(raw: str, parsed: dict) -> dict:
    """补齐 text_answer / code_snippets，避免 JSON 损坏导致内容缺失。"""
    result = dict(parsed or {})
    extra = _extract_tutoring_fields_fallback(raw)
    result = _merge_parsed_fields(result, extra)
    if not (result.get("text_answer") or "").strip():
        ta = _extract_json_string_field(raw, "text_answer")
        if ta:
            result["text_answer"] = ta
    if not _normalize_code_snippets(result):
        snippets = _extract_json_array_field(raw, "code_snippets")
        if snippets:
            result["code_snippets"] = snippets
    return result


def _extract_json_array_field(text: str, field_name: str) -> list:
    match = re.search(rf'"{re.escape(field_name)}"\s*:\s*(\[[\s\S]*?\])', text)
    if not match:
        return []
    blob = _repair_trailing_commas(_repair_json_multiline_strings(match.group(1)))
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _normalize_code_snippets(parsed: dict) -> list[str]:
    raw = parsed.get("code_snippets")
    if not isinstance(raw, list):
        return []
    snippets: list[str] = []
    for item in raw[:3]:
        snip = str(item).strip().replace("\\n", "\n")
        if snip:
            snippets.append(snip)
    return snippets


def _append_code_snippets_to_text(text: str, snippets: list[str]) -> str:
    body = (text or "").strip()
    if not snippets:
        return body
    parts = [body] if body else []
    for idx, snip in enumerate(snippets, start=1):
        parts.append(f"**代码示例 {idx}：**\n\n```python\n{snip}\n```")
    return "\n\n".join(parts).strip()


def _normalize_response(parsed: dict, fallback_text: str) -> dict:
    text = (parsed.get("text_answer") or fallback_text or "").strip()
    text = _append_code_snippets_to_text(text, _normalize_code_snippets(parsed))
    diagram = parsed.get("diagram") if isinstance(parsed.get("diagram"), dict) else {}
    actions = parsed.get("follow_up_actions") if isinstance(parsed.get("follow_up_actions"), list) else []
    related = parsed.get("related_kps") if isinstance(parsed.get("related_kps"), list) else []
    return {
        "text_answer": text,
        "diagram": {
            "title": diagram.get("title") or "概念图解",
            "mermaid": diagram.get("mermaid") or "",
        },
        "follow_up_actions": [
            a for a in actions if isinstance(a, dict) and a.get("action")
        ][:4],
        "related_kps": [str(k) for k in related][:3],
    }


def _attach_bilibili_videos(
    response: dict,
    question: str,
    context: dict | None,
) -> dict:
    videos = recommend_bilibili_videos(
        question,
        context=context,
        related_kps=response.get("related_kps") or [],
    )
    if videos:
        response["bilibili_videos"] = videos
    return response


def init_tutoring(student_id: int, session_id: str | None = None) -> dict:
    sid = resolve_tutoring_session_id(student_id, session_id)
    existing = list_messages(student_id, sid)
    if not existing:
        _append_tutoring_welcome(student_id, sid)
    return {
        "student_id": student_id,
        "session_id": sid,
        "messages": list_messages(student_id, sid),
    }


def create_tutoring_session(student_id: int) -> dict:
    """开启新的辅导会话（旧会话保留在数据库，前端切换后不再显示）。"""
    sid = new_tutoring_session_id(student_id)
    _append_tutoring_welcome(student_id, sid)
    return {
        "student_id": student_id,
        "session_id": sid,
        "messages": list_messages(student_id, sid),
    }


def ask_tutoring(
    student_id: int,
    question: str,
    context: dict | None = None,
    answer_mode: str = "all",
    session_id: str | None = None,
) -> dict:
    q = (question or "").strip()
    if not q:
        raise ValueError("请输入问题")
    if len(q) > 3000:
        raise ValueError("问题过长，请精简后重试")

    sid = resolve_tutoring_session_id(student_id, session_id)
    append_message(
        student_id,
        "user",
        "text",
        q,
        payload={"context": context or {}, "answer_mode": answer_mode},
        session_id=sid,
    )

    client = SparkLiteClient()
    context_block = _build_context_block(context)
    prompt = TUTORING_PROMPT.format(
        system=TUTORING_SYSTEM,
        question=q,
        context_block=context_block,
    )

    fallback_text = ""
    parsed = {}
    try:
        raw = client.chat(prompt, max_tokens=4096)
        parsed = _ensure_parsed_text_answer(raw, _parse_tutoring_json(raw))
        if not (parsed.get("text_answer") or "").strip():
            stripped = _strip_json_fence(raw)
            if stripped and not stripped.lstrip().startswith("{"):
                fallback_text = stripped
            else:
                logger.warning("智能辅导回复无法解析 text_answer，原始长度=%s", len(raw or ""))
                fallback_text = "抱歉，AI 回复格式异常，请稍后再试或换个问法。"
    except SparkClientError as exc:
        logger.exception("智能辅导星火调用失败")
        fallback_text = f"抱歉，AI 服务暂时不可用，请稍后再试。（{exc}）"

    response = _normalize_response(parsed, fallback_text)

    if answer_mode == "text":
        response["diagram"] = {"title": "", "mermaid": ""}
    elif answer_mode == "video":
        response["diagram"] = {"title": "", "mermaid": ""}
        _attach_bilibili_videos(response, q, context)
    elif answer_mode == "all":
        _attach_bilibili_videos(response, q, context)

    append_message(
        student_id,
        "assistant",
        "tutoring_answer",
        response["text_answer"],
        payload=response,
        session_id=sid,
    )

    mastery_updates = []
    catalog = _load_kp_catalog()
    kp_names = [c["kp_name"] for c in catalog]
    if kp_names and response["text_answer"] and not response["text_answer"].startswith("抱歉"):
        try:
            analyze_prompt = ANALYZE_PROMPT.format(
                kp_list="、".join(kp_names),
                question=q,
                answer=response["text_answer"],
            )
            raw_analyze = client.chat(analyze_prompt)
            mastery_updates = _apply_mastery_updates(student_id, _parse_analyze_json(raw_analyze))
        except Exception:
            logger.exception("辅导掌握度分析失败")

    record_event(student_id, "tutoring_ask", "tutoring", {"question_len": len(q), "answer_mode": answer_mode})

    if mastery_updates:
        summary = "；".join(
            f"「{u['kp_name']}」L{u['old_level']}→L{u['new_level']}"
            for u in mastery_updates
        )
        append_message(
            student_id,
            "system",
            "mastery_update",
            f"已根据本次辅导更新掌握度：{summary}",
            payload={"updates": mastery_updates},
            session_id=sid,
        )

    return {
        "student_id": student_id,
        "session_id": sid,
        "answer": response,
        "mastery_updates": mastery_updates,
        "messages": list_messages(student_id, sid),
    }


def get_tutoring_history(student_id: int, session_id: str | None = None) -> dict:
    sid = resolve_tutoring_session_id(student_id, session_id)
    return {
        "student_id": student_id,
        "session_id": sid,
        "messages": list_messages(student_id, sid),
    }
