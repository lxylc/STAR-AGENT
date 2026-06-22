"""在线代码运行：供学习资源代码案例实操使用。"""
from __future__ import annotations

import logging

from services.practice_judge_service import run_coding_tests

logger = logging.getLogger(__name__)


def execute_python_code(code: str) -> dict:
    """运行学生提交的 Python 代码，返回 stdout/stderr。"""
    code = (code or "").strip()
    if not code:
        return {"ok": False, "output": "", "error": "代码不能为空"}

    # 无断言的冒烟运行：能执行即视为通过基础检查
    passed, msg = run_coding_tests(
        code,
        [{"call": "None", "expected": None}],
    )
    if passed is True:
        return {"ok": True, "output": msg or "运行成功", "error": ""}
    return {"ok": False, "output": "", "error": msg or "运行失败"}


def execute_python_code_interactive(code: str) -> dict:
    """直接执行代码并捕获输出（用于案例编辑器）。"""
    import os
    import subprocess
    import tempfile

    code = (code or "").strip()
    if not code:
        return {"ok": False, "output": "", "error": "代码不能为空"}

    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)
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
            return {"ok": True, "output": stdout or "（无输出，运行成功）", "error": ""}
        return {
            "ok": False,
            "output": stdout,
            "error": stderr or stdout or "运行失败",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": "代码执行超时（>8秒）"}
    except Exception as exc:
        logger.warning("代码运行异常: %s", exc)
        return {"ok": False, "output": "", "error": str(exc)}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
