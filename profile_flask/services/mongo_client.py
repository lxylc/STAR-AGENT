"""MongoDB 连接（对话记录等非结构化数据）。"""
import logging
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from config import Config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
    return client


def get_db() -> Database:
    return get_mongo_client()[Config.MONGO_DB_NAME]


def dialogue_collection() -> Collection:
    return get_db()["profile_dialogue"]


def practice_session_collection() -> Collection:
    return get_db()["practice_session"]


def ensure_indexes():
    col = dialogue_collection()
    col.create_index([("student_id", 1), ("created_at", 1)])
    col.create_index([("student_id", 1), ("session_id", 1)])
    logger.info("MongoDB 索引已就绪: profile_dialogue")
    ps = practice_session_collection()
    ps.create_index([("session_id", 1)], unique=True)
    ps.create_index([("student_id", 1), ("created_at", -1)])
    ps.create_index([("expires_at", 1)], expireAfterSeconds=0)
