-- 已有库增量执行（模块2表）
USE learning_agent;

CREATE TABLE IF NOT EXISTS agent_task (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id       BIGINT       NOT NULL,
    profile_id       BIGINT       DEFAULT NULL,
    subject          VARCHAR(64)  NOT NULL,
    knowledge_point  VARCHAR(128) DEFAULT NULL,
    task_type        VARCHAR(16)  NOT NULL DEFAULT 'SINGLE',
    agent_types      JSON         NOT NULL,
    batch_points     JSON         DEFAULT NULL,
    task_status      VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    error_message    TEXT         DEFAULT NULL,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at      DATETIME     DEFAULT NULL,
    deleted          TINYINT      NOT NULL DEFAULT 0,
    INDEX idx_student_task (student_id, task_status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='智能体调度任务';

CREATE TABLE IF NOT EXISTS agent_sub_task (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id          BIGINT       NOT NULL,
    agent_type       VARCHAR(32)  NOT NULL,
    knowledge_point  VARCHAR(128) NOT NULL,
    sub_status       VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    error_message    TEXT         DEFAULT NULL,
    started_at       DATETIME     DEFAULT NULL,
    finished_at      DATETIME     DEFAULT NULL,
    INDEX idx_task (task_id)
) ENGINE=InnoDB COMMENT='智能体子任务';

CREATE TABLE IF NOT EXISTS learning_resource (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id       BIGINT       NOT NULL,
    profile_id       BIGINT       DEFAULT NULL,
    task_id          BIGINT       DEFAULT NULL,
    sub_task_id      BIGINT       DEFAULT NULL,
    resource_type    VARCHAR(32)  NOT NULL,
    title            VARCHAR(256) NOT NULL,
    content          MEDIUMTEXT   NOT NULL,
    content_json     JSON         DEFAULT NULL,
    subject          VARCHAR(64)  NOT NULL,
    knowledge_point  VARCHAR(128) NOT NULL,
    profile_tags     JSON         DEFAULT NULL,
    resource_status  VARCHAR(16)  NOT NULL DEFAULT 'published',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted          TINYINT      NOT NULL DEFAULT 0,
    INDEX idx_student (student_id),
    INDEX idx_subject_kp (subject, knowledge_point),
    INDEX idx_type (resource_type),
    INDEX idx_task (task_id)
) ENGINE=InnoDB COMMENT='学习资源';
