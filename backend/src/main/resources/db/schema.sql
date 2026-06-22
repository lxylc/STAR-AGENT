-- 个性化学习智能体系统 - 数据库初始化脚本
CREATE DATABASE IF NOT EXISTS learning_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE learning_agent;

-- 学生用户表
CREATE TABLE IF NOT EXISTS student (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '学生ID',
    username    VARCHAR(64)  NOT NULL UNIQUE COMMENT '登录用户名',
    real_name   VARCHAR(64)  DEFAULT NULL COMMENT '真实姓名',
    password_hash VARCHAR(128) DEFAULT NULL COMMENT 'BCrypt 密码哈希',
    role        VARCHAR(16)  NOT NULL DEFAULT 'student' COMMENT 'student/admin',
    grade       VARCHAR(32)  DEFAULT NULL COMMENT '年级',
    major       VARCHAR(64)  DEFAULT NULL COMMENT '专业',
    learn_preferences JSON DEFAULT NULL COMMENT '学习偏好多选',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted     TINYINT      NOT NULL DEFAULT 0
) ENGINE=InnoDB COMMENT='学生用户';

-- 学习画像主表（模块1核心）
CREATE TABLE IF NOT EXISTS learning_profile (
    id                BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '画像ID',
    student_id        BIGINT       NOT NULL COMMENT '学生ID',
    grade             VARCHAR(32)  DEFAULT NULL COMMENT '年级',
    major             VARCHAR(64)  DEFAULT NULL COMMENT '专业',
    main_subject      VARCHAR(64)  DEFAULT NULL COMMENT '主修学科',
    knowledge_base    TEXT         DEFAULT NULL COMMENT '知识基础描述',
    weak_points       JSON         DEFAULT NULL COMMENT '薄弱知识点标签数组',
    mastered_points   JSON         DEFAULT NULL COMMENT '已掌握知识点名称数组',
    daily_study_hours DECIMAL(4,1) DEFAULT NULL COMMENT '每日学习时长(小时)',
    learn_preference  VARCHAR(32)  DEFAULT NULL COMMENT '学习偏好: text/video/exercise/mixed',
    learn_goal        TEXT         DEFAULT NULL COMMENT '学习目标',
    base_tags         JSON         DEFAULT NULL COMMENT '学生基础标签',
    mastery_tags      JSON         DEFAULT NULL COMMENT '学科掌握度标签',
    style_tags        JSON         DEFAULT NULL COMMENT '学习风格标签',
    goal_tags         JSON         DEFAULT NULL COMMENT '学习目标标签',
    behavior_tags     JSON         DEFAULT NULL COMMENT '学习行为标签',
    profile_status    VARCHAR(16)  NOT NULL DEFAULT 'draft' COMMENT 'draft/building/completed',
    version           INT          NOT NULL DEFAULT 1 COMMENT '画像版本号',
    raw_extract_json  JSON         DEFAULT NULL COMMENT 'AI抽取原始JSON',
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted           TINYINT      NOT NULL DEFAULT 0,
    INDEX idx_student (student_id),
    INDEX idx_status (profile_status)
) ENGINE=InnoDB COMMENT='学生学习画像';

-- 画像构建对话记录
CREATE TABLE IF NOT EXISTS profile_dialogue (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id  BIGINT       NOT NULL,
    profile_id  BIGINT       DEFAULT NULL COMMENT '关联画像ID',
    role        VARCHAR(16)  NOT NULL COMMENT 'user/assistant/system',
    content     TEXT         NOT NULL,
    round_no    INT          NOT NULL DEFAULT 0 COMMENT '对话轮次',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_student_round (student_id, round_no)
) ENGINE=InnoDB COMMENT='画像构建对话记录';

-- ========== 模块2：多智能体资源生成 ==========

-- 智能体调度任务主表
CREATE TABLE IF NOT EXISTS agent_task (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务ID',
    student_id       BIGINT       NOT NULL,
    profile_id       BIGINT       DEFAULT NULL COMMENT '关联学习画像',
    subject          VARCHAR(64)  NOT NULL COMMENT '学科',
    knowledge_point  VARCHAR(128) DEFAULT NULL COMMENT '单知识点（单条生成）',
    task_type        VARCHAR(16)  NOT NULL DEFAULT 'SINGLE' COMMENT 'SINGLE/BATCH',
    agent_types      JSON         NOT NULL COMMENT '执行的智能体类型列表',
    batch_points     JSON         DEFAULT NULL COMMENT '批量知识点列表',
    task_status      VARCHAR(16)  NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/RUNNING/SUCCESS/PARTIAL/FAILED',
    error_message    TEXT         DEFAULT NULL,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at      DATETIME     DEFAULT NULL,
    deleted          TINYINT      NOT NULL DEFAULT 0,
    INDEX idx_student_task (student_id, task_status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB COMMENT='智能体调度任务';

-- 智能体子任务表
CREATE TABLE IF NOT EXISTS agent_sub_task (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id          BIGINT       NOT NULL,
    agent_type       VARCHAR(32)  NOT NULL COMMENT 'LECTURE/EXERCISE/COURSEWARE',
    knowledge_point  VARCHAR(128) NOT NULL,
    sub_status       VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    error_message    TEXT         DEFAULT NULL,
    started_at       DATETIME     DEFAULT NULL,
    finished_at      DATETIME     DEFAULT NULL,
    INDEX idx_task (task_id),
    INDEX idx_agent (agent_type)
) ENGINE=InnoDB COMMENT='智能体子任务';

-- 学习资源表
CREATE TABLE IF NOT EXISTS learning_resource (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id       BIGINT       NOT NULL,
    profile_id       BIGINT       DEFAULT NULL,
    task_id          BIGINT       DEFAULT NULL,
    sub_task_id      BIGINT       DEFAULT NULL,
    resource_type    VARCHAR(32)  NOT NULL COMMENT 'lecture/exam_summary/exercise/courseware',
    title            VARCHAR(256) NOT NULL,
    content          MEDIUMTEXT   NOT NULL COMMENT '资源正文',
    content_json     JSON         DEFAULT NULL COMMENT '习题等结构化内容',
    subject          VARCHAR(64)  NOT NULL,
    knowledge_point  VARCHAR(128) NOT NULL,
    profile_tags     JSON         DEFAULT NULL COMMENT '关联学生画像标签快照',
    resource_status  VARCHAR(16)  NOT NULL DEFAULT 'published',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted          TINYINT      NOT NULL DEFAULT 0,
    INDEX idx_student (student_id),
    INDEX idx_subject_kp (subject, knowledge_point),
    INDEX idx_type (resource_type),
    INDEX idx_task (task_id)
) ENGINE=InnoDB COMMENT='学习资源';

-- ========== 模块3：知识图谱 / 学习路径 / 进度 / 推送 ==========

-- 学科知识图谱节点（简易树 + 前置关系）
CREATE TABLE IF NOT EXISTS knowledge_node (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    subject         VARCHAR(64)  NOT NULL COMMENT '学科',
    node_name       VARCHAR(128) NOT NULL COMMENT '知识点名称',
    parent_id       BIGINT       DEFAULT 0 COMMENT '父节点，0为根',
    node_level      INT          NOT NULL DEFAULT 1 COMMENT '层级1-4',
    sort_order      INT          NOT NULL DEFAULT 0,
    prerequisite_ids JSON        DEFAULT NULL COMMENT '前置节点ID数组',
    description     VARCHAR(512) DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_subject_parent_name (subject, parent_id, node_name),
    INDEX idx_subject (subject),
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB COMMENT='知识图谱节点';

-- 学生学习路径主表
CREATE TABLE IF NOT EXISTS learning_path (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id      BIGINT       NOT NULL,
    profile_id      BIGINT       DEFAULT NULL,
    subject         VARCHAR(64)  NOT NULL,
    path_name       VARCHAR(128) NOT NULL,
    path_summary    TEXT         DEFAULT NULL COMMENT '大模型生成的路径说明',
    stages_json     JSON         NOT NULL COMMENT '阶段划分快照',
    path_status     VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT 'active/archived',
    version         INT          NOT NULL DEFAULT 1,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted         TINYINT      NOT NULL DEFAULT 0,
    INDEX idx_student_subject (student_id, subject),
    INDEX idx_status (path_status)
) ENGINE=InnoDB COMMENT='个性化学习路径';

-- 路径步骤明细
CREATE TABLE IF NOT EXISTS learning_path_item (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    path_id         BIGINT       NOT NULL,
    stage_no        INT          NOT NULL COMMENT '阶段序号',
    stage_name      VARCHAR(64)  NOT NULL,
    knowledge_point VARCHAR(128) NOT NULL,
    node_id         BIGINT       DEFAULT NULL COMMENT '关联图谱节点',
    sort_order      INT          NOT NULL DEFAULT 0,
    item_status     VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending/in_progress/completed/skipped',
    priority        INT          NOT NULL DEFAULT 5 COMMENT '1最高',
    focus_reason    VARCHAR(256) DEFAULT NULL COMMENT '推荐原因',
    estimated_hours DECIMAL(4,1) DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_path (path_id),
    INDEX idx_status (item_status)
) ENGINE=InnoDB COMMENT='学习路径步骤';

-- 学生学习进度
CREATE TABLE IF NOT EXISTS student_progress (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id      BIGINT       NOT NULL,
    subject         VARCHAR(64)  NOT NULL,
    knowledge_point VARCHAR(128) NOT NULL,
    progress_pct    INT          NOT NULL DEFAULT 0 COMMENT '0-100',
    mastery_level   VARCHAR(16)  DEFAULT 'unknown' COMMENT 'weak/normal/good/excellent',
    study_minutes   INT          NOT NULL DEFAULT 0,
    last_study_at   DATETIME     DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_student_kp (student_id, subject, knowledge_point),
    INDEX idx_student (student_id)
) ENGINE=InnoDB COMMENT='学生学习进度';

-- 资源推送记录
CREATE TABLE IF NOT EXISTS resource_push_record (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id      BIGINT       NOT NULL,
    path_id         BIGINT       DEFAULT NULL,
    path_item_id    BIGINT       DEFAULT NULL,
    resource_id     BIGINT       NOT NULL,
    push_type       VARCHAR(16)  NOT NULL DEFAULT 'auto' COMMENT 'auto/manual/refresh',
    push_reason     VARCHAR(256) DEFAULT NULL,
    read_status     VARCHAR(16)  NOT NULL DEFAULT 'unread' COMMENT 'unread/read',
    pushed_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at         DATETIME     DEFAULT NULL,
    INDEX idx_student (student_id),
    INDEX idx_path (path_id),
    INDEX idx_read (read_status)
) ENGINE=InnoDB COMMENT='资源推送记录';

-- 画像变更日志
CREATE TABLE IF NOT EXISTS profile_change_log (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    student_id   BIGINT       NOT NULL COMMENT '学生ID',
    course_id    VARCHAR(64)  NOT NULL COMMENT '课程ID',
    field_name   VARCHAR(128) NOT NULL COMMENT '变更字段',
    old_value    TEXT         DEFAULT NULL COMMENT '旧值',
    new_value    TEXT         DEFAULT NULL COMMENT '新值',
    source       VARCHAR(32)  DEFAULT NULL COMMENT '来源',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_student_course (student_id, course_id),
    INDEX idx_field (field_name),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='画像变更日志';

-- ========== 知识图谱数据（Python 127 知识点）==========
-- 首次部署必须导入: source knowledge-seed.sql  （与本文件同目录）
-- 之后所有增删改在 knowledge_node 表维护，后端不嵌入知识点文件

-- 知识图谱表结构见上方 knowledge_node

-- 演示默认学生
INSERT INTO student (username, real_name) VALUES ('demo_student', '演示学生')
ON DUPLICATE KEY UPDATE real_name = VALUES(real_name);
