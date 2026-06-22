-- Module 5: learning effectiveness evaluation
USE learning_agent;

CREATE TABLE IF NOT EXISTS learning_evaluation (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id      BIGINT       NOT NULL,
    subject         VARCHAR(64)  NOT NULL DEFAULT 'Python',
    overall_score   DECIMAL(5,2) NOT NULL DEFAULT 0,
    metrics_json    JSON         NOT NULL,
    report_summary  TEXT         DEFAULT NULL,
    ai_analysis     JSON         DEFAULT NULL,
    adjustment_json JSON         DEFAULT NULL,
    eval_status     VARCHAR(16)  NOT NULL DEFAULT 'completed',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_eval_student (student_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS learning_behavior_event (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id   BIGINT       NOT NULL,
    event_type   VARCHAR(32)  NOT NULL,
    event_source VARCHAR(64)  DEFAULT NULL,
    payload_json JSON         DEFAULT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_behavior_student (student_id, event_type, created_at)
) ENGINE=InnoDB;
