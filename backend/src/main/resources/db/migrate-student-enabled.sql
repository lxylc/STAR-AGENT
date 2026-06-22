-- 学生账号启用/禁用字段
USE learning_agent;

ALTER TABLE student
    ADD COLUMN enabled TINYINT NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用' AFTER learn_preferences;
