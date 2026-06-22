"""Flask 应用配置，从环境变量或 .env 加载。"""
import os
from pathlib import Path

from dotenv import load_dotenv

_BASE = Path(__file__).resolve().parent
load_dotenv(_BASE / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "profile-build-dev")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DB = os.getenv("MYSQL_DB", "learning_agent")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "learning_agent")

    XFYUN_APP_ID = os.getenv("XFYUN_APP_ID", "3d66baac")
    XFYUN_API_KEY = os.getenv("XFYUN_API_KEY", "41d971d3b6c70e15c7a174aae86d0d8a")
    XFYUN_API_SECRET = os.getenv("XFYUN_API_SECRET", "")

    SPARK_HOST_URL = os.getenv(
        "SPARK_HOST_URL", "wss://spark-api.xf-yun.com/v1.1/chat"
    )
    SPARK_DOMAIN = os.getenv("SPARK_DOMAIN", "lite")
    SPARK_TEMPERATURE = float(os.getenv("SPARK_TEMPERATURE", "0.1"))
    SPARK_MAX_TOKENS = int(os.getenv("SPARK_MAX_TOKENS", "256"))
    SPARK_TIMEOUT_SEC = int(os.getenv("SPARK_TIMEOUT_SEC", "60"))

    # 自评选项 A/B/C/D 对应等级（兼容旧流程）
    LEVEL_OPTIONS = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
    }
    LEVEL_LABELS = {
        1: "薄弱",
        2: "一般",
        3: "熟练",
        4: "精通",
    }
    MASTERY_TO_LEVEL = {
        "薄弱": 1,
        "一般": 2,
        "熟练": 3,
        "精通": 4,
    }
    COURSE_ID = os.getenv("COURSE_ID", "python101")

    # 多媒体生成（需在讯飞控制台分别开通「图片生成」「在线语音合成」）
    XFYUN_TTI_ENABLED = os.getenv("XFYUN_TTI_ENABLED", "0") == "1"
    XFYUN_TTS_ENABLED = os.getenv("XFYUN_TTS_ENABLED", "0") == "1"
    XFYUN_TTS_VCN = os.getenv("XFYUN_TTS_VCN", "xiaoyan")
    MEDIA_DIR = os.getenv("MEDIA_DIR", str(_BASE / "media"))
    AUTO_GENERATE_TUTORING_MEDIA = os.getenv("AUTO_GENERATE_TUTORING_MEDIA", "0") == "1"

    JAVA_API_BASE = os.getenv("JAVA_API_BASE", "http://127.0.0.1:8080")
