-- 清空旧 5 模块数据，准备 12 模块 seed（执行后运行 init_db.py --refresh-all）
USE learning_agent;

DELETE FROM answer_record;
DELETE FROM student_profile;
DELETE FROM exercise;
DELETE FROM knowledge_points;
DELETE FROM subject_module;

ALTER TABLE student_profile
    ADD COLUMN IF NOT EXISTS base_score SMALLINT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS quiz_score SMALLINT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS final_score SMALLINT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS tags_json JSON DEFAULT NULL;
