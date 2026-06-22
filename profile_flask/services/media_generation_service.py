"""辅导多媒体生成：文生图 + 语音合成 → 真实图片与讲解音频/幻灯片。"""
import logging

from config import Config
from services.xfyun_tti_client import TtiClientError, XfyunTtiClient, save_image_bytes
from services.xfyun_tts_client import TtsClientError, XfyunTtsClient, save_audio_bytes

logger = logging.getLogger(__name__)


def _diagram_prompt(diagram: dict) -> str:
    title = (diagram.get("title") or "Python 概念图").strip()
    mermaid = (diagram.get("mermaid") or "").strip()
    hint = mermaid.replace("flowchart", "").replace("TD", "").replace("-->", "到")[:200]
    return (
        f"教育插画风格，简洁清晰，白底，适合大学生学习：{title}。"
        f"展示 Python 编程概念关系：{hint}"
    )


def _slide_image_prompt(section: dict, video_title: str) -> str:
    title = section.get("title") or ""
    visual = section.get("visual_hint") or section.get("narration") or ""
    return (
        f"教学幻灯片风格，16:9，简洁扁平化设计，标题「{video_title} - {title}」。"
        f"画面内容：{visual[:300]}"
    )


def generate_tutoring_media(student_id: int, answer: dict) -> dict:
    """
    为辅导回答生成真实媒体资源。
    返回 enrich 后的 answer（含 diagram_image_url、video_slides 等）。
    """
    if not isinstance(answer, dict):
        return answer

    result = dict(answer)
    tti = XfyunTtiClient()
    tts = XfyunTtsClient()

    diagram = result.get("diagram") or {}
    if diagram.get("mermaid") and Config.XFYUN_TTI_ENABLED:
        try:
            img = tti.generate_image(_diagram_prompt(diagram))
            result["diagram_image_url"] = save_image_bytes(img, student_id, "diagram")
            result["diagram"]["image_url"] = result["diagram_image_url"]
        except TtiClientError as exc:
            logger.warning("文生图失败（图解）: %s", exc)
            result["diagram_media_error"] = str(exc)

    video = result.get("video_script") or {}
    sections = video.get("sections") if isinstance(video.get("sections"), list) else []
    slides = []
    video_title = video.get("title") or "讲解"

    for idx, sec in enumerate(sections[:6]):
        if not isinstance(sec, dict):
            continue
        slide = {
            "title": sec.get("title") or f"片段{idx + 1}",
            "narration": sec.get("narration") or "",
            "visual_hint": sec.get("visual_hint") or "",
            "image_url": None,
            "audio_url": None,
        }

        if Config.XFYUN_TTI_ENABLED and (sec.get("visual_hint") or sec.get("narration")):
            try:
                img = tti.generate_image(_slide_image_prompt(sec, video_title))
                slide["image_url"] = save_image_bytes(img, student_id, f"slide{idx}")
            except TtiClientError as exc:
                logger.warning("文生图失败 slide %s: %s", idx, exc)

        narration = (sec.get("narration") or "").strip()
        if narration and Config.XFYUN_TTS_ENABLED:
            try:
                audio = tts.synthesize_mp3(narration)
                slide["audio_url"] = save_audio_bytes(audio, student_id, f"slide{idx}")
            except TtsClientError as exc:
                logger.warning("TTS 失败 slide %s: %s", idx, exc)

        slides.append(slide)

    if slides:
        result["video_slides"] = slides
        result["video_script"]["slides"] = slides

    result["media_status"] = {
        "tti_enabled": Config.XFYUN_TTI_ENABLED,
        "tts_enabled": Config.XFYUN_TTS_ENABLED,
        "slide_count": len(slides),
        "has_diagram_image": bool(result.get("diagram_image_url")),
    }
    return result
