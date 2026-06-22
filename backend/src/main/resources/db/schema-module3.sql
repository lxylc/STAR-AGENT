USE learning_agent;

CREATE TABLE IF NOT EXISTS knowledge_node (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    subject VARCHAR(64) NOT NULL,
    node_name VARCHAR(128) NOT NULL,
    parent_id BIGINT DEFAULT 0,
    node_level INT NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    prerequisite_ids JSON DEFAULT NULL,
    description VARCHAR(512) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_subject_name (subject, node_name),
    INDEX idx_subject (subject)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS learning_path (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id BIGINT NOT NULL,
    profile_id BIGINT DEFAULT NULL,
    subject VARCHAR(64) NOT NULL,
    path_name VARCHAR(128) NOT NULL,
    path_summary TEXT DEFAULT NULL,
    stages_json JSON NOT NULL,
    path_status VARCHAR(16) NOT NULL DEFAULT 'active',
    version INT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted TINYINT NOT NULL DEFAULT 0,
    INDEX idx_student_subject (student_id, subject)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS learning_path_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    path_id BIGINT NOT NULL,
    stage_no INT NOT NULL,
    stage_name VARCHAR(64) NOT NULL,
    knowledge_point VARCHAR(128) NOT NULL,
    node_id BIGINT DEFAULT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    item_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    priority INT NOT NULL DEFAULT 5,
    focus_reason VARCHAR(256) DEFAULT NULL,
    estimated_hours DECIMAL(4,1) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_path (path_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS student_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id BIGINT NOT NULL,
    subject VARCHAR(64) NOT NULL,
    knowledge_point VARCHAR(128) NOT NULL,
    progress_pct INT NOT NULL DEFAULT 0,
    mastery_level VARCHAR(16) DEFAULT 'unknown',
    study_minutes INT NOT NULL DEFAULT 0,
    last_study_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_student_kp (student_id, subject, knowledge_point),
    INDEX idx_student (student_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS resource_push_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id BIGINT NOT NULL,
    path_id BIGINT DEFAULT NULL,
    path_item_id BIGINT DEFAULT NULL,
    resource_id BIGINT NOT NULL,
    push_type VARCHAR(16) NOT NULL DEFAULT 'auto',
    push_reason VARCHAR(256) DEFAULT NULL,
    read_status VARCHAR(16) NOT NULL DEFAULT 'unread',
    pushed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME DEFAULT NULL,
    INDEX idx_student (student_id),
    INDEX idx_path (path_id)
) ENGINE=InnoDB;
