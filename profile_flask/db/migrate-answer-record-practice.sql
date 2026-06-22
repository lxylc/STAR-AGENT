-- 答题记录表扩展：支持习题中心/模块练习逐题入库
ALTER TABLE answer_record MODIFY ex_id INT NULL;
ALTER TABLE answer_record ADD COLUMN module_id INT NULL COMMENT '所属模块';
ALTER TABLE answer_record ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'profile_quiz';
ALTER TABLE answer_record ADD INDEX idx_student_created (student_id, created_at);
