"""辅导回答 — B 站视频推荐（知识点/关键词 → 预置 BV 映射）。"""
from __future__ import annotations

import re

# 预置视频库：按模块名与关键词匹配，可在下方增删改 BV 号
_VIDEO_LIBRARY: list[dict] = [
    {
        "modules": ["Python环境与基础语法"],
        "keywords": ["环境", "安装", "pip", "解释器", "ide", "pycharm", "vscode", "hello", "print", "注释", "缩进"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 环境与基础语法入门",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["变量、数据类型与运算符"],
        "keywords": ["变量", "数据类型", "int", "float", "str", "bool", "运算符", "类型转换", "赋值"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 变量与数据类型",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["流程控制：条件与循环"],
        "keywords": ["if", "else", "elif", "条件", "循环", "for", "while", "break", "continue", "分支"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 条件判断与循环",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["组合数据结构：列表/元组/字典/集合"],
        "keywords": ["列表", "元组", "字典", "集合", "list", "tuple", "dict", "set", "索引", "切片"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 组合数据类型",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["函数、高阶函数与装饰器"],
        "keywords": ["函数", "def", "参数", "返回值", "lambda", "装饰器", "闭包", "作用域"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 函数与装饰器",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["异常处理与调试"],
        "keywords": ["异常", "try", "except", "finally", "raise", "调试", "traceback", "错误"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 异常处理与调试",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["字符串与正则表达式"],
        "keywords": ["字符串", "正则", "regex", "re模块", "split", "join", "格式化", "f-string"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 字符串与正则表达式",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["模块、包与虚拟环境"],
        "keywords": ["模块", "包", "import", "虚拟环境", "venv", "requirements", "第三方库"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 模块与虚拟环境",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["面向对象编程"],
        "keywords": ["面向对象", "类", "对象", "继承", "封装", "多态", "class", "self", "init"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 面向对象编程",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["文件IO与数据持久化"],
        "keywords": ["文件", "读写", "open", "json", "csv", "持久化", "with"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 文件读写",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["网络请求与API调用"],
        "keywords": ["网络", "请求", "api", "http", "requests", "接口", "爬虫"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 网络请求与 API",
            "author": "黑马程序员",
        },
    },
    {
        "modules": ["基础算法与代码规范"],
        "keywords": ["算法", "排序", "查找", "复杂度", "规范", "pep8", "命名"],
        "video": {
            "bvid": "BV1ex411x7Em",
            "title": "Python 基础算法与代码规范",
            "author": "黑马程序员",
        },
    },
]

_DEFAULT_VIDEO = {
    "bvid": "BV1ex411x7Em",
    "title": "Python 编程入门教程",
    "author": "黑马程序员",
}

_BVID_RE = re.compile(r"^BV[\w]+$", re.I)


def normalize_bvid(bvid: str) -> str:
    raw = (bvid or "").strip()
    if not raw:
        return ""
    if raw.lower().startswith("bv"):
        return raw.upper() if raw[2:].isdigit() else raw
    return raw


def build_embed_url(bvid: str, page: int = 1, start_sec: int = 0) -> str:
    """B 站官方 iframe 播放器地址。"""
    bvid = normalize_bvid(bvid)
    params = f"bvid={bvid}&page={max(1, page)}&high_quality=1&danmaku=0"
    if start_sec > 0:
        params += f"&t={start_sec}"
    return f"//player.bilibili.com/player.html?{params}"


def _collect_hints(question: str, context: dict | None, related_kps: list[str]) -> tuple[str, set[str]]:
    ctx = context or {}
    parts = [question or ""]
    if ctx.get("knowledge_point"):
        parts.append(str(ctx["knowledge_point"]))
    if ctx.get("resource_title"):
        parts.append(str(ctx["resource_title"]))
    parts.extend(related_kps or [])
    blob = " ".join(parts).lower()
    modules: set[str] = set()
    for kp in related_kps or []:
        modules.add(kp.split("-")[0].strip())
    if ctx.get("knowledge_point"):
        modules.add(str(ctx["knowledge_point"]).split("-")[0].strip())
    return blob, modules


def _score_entry(entry: dict, blob: str, modules: set[str]) -> int:
    score = 0
    for mod in entry.get("modules") or []:
        if mod in modules:
            score += 20
        elif any(mod in m or m in mod for m in modules):
            score += 10
        if mod.lower() in blob:
            score += 8
    for kw in entry.get("keywords") or []:
        if kw.lower() in blob:
            score += 4
    return score


def recommend_bilibili_videos(
    question: str,
    context: dict | None = None,
    related_kps: list[str] | None = None,
    limit: int = 2,
) -> list[dict]:
    """
    根据问题、上下文与相关知识点推荐 B 站视频。
    返回 [{ bvid, title, author?, page?, start_sec?, embed_url, reason? }, ...]
    """
    blob, modules = _collect_hints(question, context, related_kps or [])
    scored: list[tuple[int, dict]] = []
    for entry in _VIDEO_LIBRARY:
        s = _score_entry(entry, blob, modules)
        if s > 0:
            scored.append((s, entry["video"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    seen_bvids: set[str] = set()
    results: list[dict] = []

    for score, video in scored:
        bvid = normalize_bvid(video.get("bvid", ""))
        if not bvid or bvid in seen_bvids:
            continue
        if not _BVID_RE.match(bvid):
            continue
        seen_bvids.add(bvid)
        page = int(video.get("page") or 1)
        start_sec = int(video.get("start_sec") or 0)
        results.append({
            "bvid": bvid,
            "title": video.get("title") or "Python 视频讲解",
            "author": video.get("author") or "",
            "page": page,
            "start_sec": start_sec,
            "embed_url": build_embed_url(bvid, page, start_sec),
            "reason": f"匹配度 {score}",
        })
        if len(results) >= limit:
            break

    if not results:
        bvid = normalize_bvid(_DEFAULT_VIDEO["bvid"])
        results.append({
            "bvid": bvid,
            "title": _DEFAULT_VIDEO["title"],
            "author": _DEFAULT_VIDEO.get("author") or "",
            "page": 1,
            "start_sec": 0,
            "embed_url": build_embed_url(bvid),
            "reason": "Python 入门默认推荐",
        })

    return results
