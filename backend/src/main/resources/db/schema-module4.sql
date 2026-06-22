-- 模块4：已掌握知识点勾选（未勾选视为待学习）
USE learning_agent;

ALTER TABLE learning_profile
    ADD COLUMN mastered_points JSON DEFAULT NULL COMMENT '已掌握知识点名称数组' AFTER weak_points;
