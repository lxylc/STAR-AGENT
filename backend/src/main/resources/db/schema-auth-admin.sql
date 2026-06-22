-- 鉴权与管理员扩展（在已有 learning_agent 库上执行）
USE learning_agent;

ALTER TABLE student
    ADD COLUMN password_hash VARCHAR(128) DEFAULT NULL COMMENT 'BCrypt 密码哈希' AFTER real_name,
    ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'student' COMMENT 'student/admin' AFTER password_hash,
    ADD COLUMN grade VARCHAR(32) DEFAULT NULL COMMENT '年级' AFTER role,
    ADD COLUMN major VARCHAR(64) DEFAULT NULL COMMENT '专业' AFTER grade,
    ADD COLUMN learn_preferences JSON DEFAULT NULL COMMENT '学习偏好多选' AFTER major,
    ADD COLUMN enabled TINYINT NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用' AFTER learn_preferences;

CREATE TABLE IF NOT EXISTS profile_snapshot (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id   BIGINT       NOT NULL,
    course_id    VARCHAR(32)  NOT NULL DEFAULT 'python101',
    scores_json  JSON         NOT NULL COMMENT '12模块分数',
    tags_json    JSON         NOT NULL COMMENT '四维标签',
    radar_json   JSON         DEFAULT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_student_course (student_id, course_id)
) ENGINE=InnoDB COMMENT='画像完整重测快照';

CREATE TABLE IF NOT EXISTS profile_change_log (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id   BIGINT       NOT NULL,
    course_id    VARCHAR(32)  NOT NULL DEFAULT 'python101',
    field_name   VARCHAR(64)  NOT NULL,
    old_value    VARCHAR(512) DEFAULT NULL,
    new_value    VARCHAR(512) DEFAULT NULL,
    source       VARCHAR(32)  NOT NULL COMMENT 'assessment/quiz/qa/admin',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_student_log (student_id, created_at)
) ENGINE=InnoDB COMMENT='画像变更日志';

CREATE TABLE IF NOT EXISTS admin_operation_log (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    admin_id     BIGINT       NOT NULL,
    target_student_id BIGINT  NOT NULL,
    action       VARCHAR(64)  NOT NULL,
    detail_json  JSON         DEFAULT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin_op (admin_id, created_at)
) ENGINE=InnoDB COMMENT='管理员操作审计';
