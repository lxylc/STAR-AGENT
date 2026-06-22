-- 题库改为选择题：增加 options 与 question_type
USE learning_agent;

ALTER TABLE exercise
    ADD COLUMN IF NOT EXISTS question_type VARCHAR(16) NOT NULL DEFAULT 'choice' COMMENT 'choice=选择题' AFTER answer,
    ADD COLUMN IF NOT EXISTS options JSON NULL COMMENT '选项 {"A":"...","B":"..."}' AFTER question_type;
