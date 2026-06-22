"""SQLAlchemy 实体映射。"""
import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON

db = SQLAlchemy()


class SubjectModule(db.Model):
    __tablename__ = "subject_module"

    module_id = db.Column(db.Integer, primary_key=True)
    module_name = db.Column(db.String(64), nullable=False, unique=True)

    knowledge_points = db.relationship("KnowledgePoint", back_populates="module")


class KnowledgePoint(db.Model):
    __tablename__ = "knowledge_points"

    kp_id = db.Column(db.Integer, primary_key=True)
    kp_name = db.Column(db.String(128), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("subject_module.module_id"), nullable=False)

    module = db.relationship("SubjectModule", back_populates="knowledge_points")
    exercises = db.relationship("Exercise", back_populates="knowledge_point")


class Exercise(db.Model):
    __tablename__ = "exercise"

    ex_id = db.Column(db.Integer, primary_key=True)
    kp_id = db.Column(db.Integer, db.ForeignKey("knowledge_points.kp_id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.SmallInteger, nullable=False)
    answer = db.Column(db.String(8), nullable=False, comment="正确选项 A/B/C/D")
    question_type = db.Column(db.String(16), nullable=False, default="choice")
    options = db.Column(JSON, nullable=True, comment='{"A":"...","B":"..."}')

    knowledge_point = db.relationship("KnowledgePoint", back_populates="exercises")

    def options_dict(self) -> dict:
        if isinstance(self.options, dict):
            return self.options
        if isinstance(self.options, str):
            return json.loads(self.options)
        return {}


class StudentProfile(db.Model):
    __tablename__ = "student_profile"

    profile_id = db.Column(db.BigInteger, primary_key=True)
    student_id = db.Column(db.BigInteger, nullable=False)
    kp_id = db.Column(db.Integer, db.ForeignKey("knowledge_points.kp_id"), nullable=False)
    master_level = db.Column(db.SmallInteger, nullable=False, default=1)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnswerRecord(db.Model):
    __tablename__ = "answer_record"

    record_id = db.Column(db.BigInteger, primary_key=True)
    student_id = db.Column(db.BigInteger, nullable=False)
    ex_id = db.Column(db.Integer, db.ForeignKey("exercise.ex_id"), nullable=True)
    module_id = db.Column(db.Integer, nullable=True)
    source = db.Column(db.String(32), nullable=False, default="profile_quiz")
    user_answer = db.Column(db.Text, nullable=False)
    judge_result = db.Column(db.SmallInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
