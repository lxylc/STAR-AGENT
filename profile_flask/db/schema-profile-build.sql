-- 对话式学习画像自主构建 - 专用表（在 learning_agent 库中执行）
USE learning_agent;

-- 1. 模块表
CREATE TABLE IF NOT EXISTS subject_module (
    module_id   INT PRIMARY KEY AUTO_INCREMENT COMMENT '模块ID',
    module_name VARCHAR(64) NOT NULL UNIQUE COMMENT '模块名称'
) ENGINE=InnoDB COMMENT='Python学习模块';

-- 2. 细分知识点表
CREATE TABLE IF NOT EXISTS knowledge_points (
    kp_id       INT PRIMARY KEY AUTO_INCREMENT COMMENT '知识点ID',
    kp_name     VARCHAR(128) NOT NULL COMMENT '知识点名称',
    module_id   INT NOT NULL COMMENT '所属模块',
    INDEX idx_module (module_id),
    CONSTRAINT fk_kp_module FOREIGN KEY (module_id) REFERENCES subject_module(module_id)
) ENGINE=InnoDB COMMENT='细分知识点';

-- 3. 题库表
CREATE TABLE IF NOT EXISTS exercise (
    ex_id       INT PRIMARY KEY AUTO_INCREMENT COMMENT '题目ID',
    kp_id       INT NOT NULL COMMENT '关联知识点',
    content     TEXT NOT NULL COMMENT '题目内容',
    difficulty  TINYINT NOT NULL COMMENT '难度1-4',
    answer      VARCHAR(8) NOT NULL COMMENT '正确选项 A/B/C/D',
    question_type VARCHAR(16) NOT NULL DEFAULT 'choice' COMMENT 'choice=选择题',
    options     JSON NULL COMMENT '选项 {"A":"...","B":"..."}',
    INDEX idx_kp_diff (kp_id, difficulty),
    CONSTRAINT fk_ex_kp FOREIGN KEY (kp_id) REFERENCES knowledge_points(kp_id)
) ENGINE=InnoDB COMMENT='校验题库';

-- 4. 学生画像表（知识点掌握等级）
CREATE TABLE IF NOT EXISTS student_profile (
    profile_id    BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id    BIGINT NOT NULL COMMENT '学生ID',
    kp_id         INT NOT NULL COMMENT '知识点ID',
    master_level  TINYINT NOT NULL DEFAULT 1 COMMENT '掌握等级1-4',
    update_time   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_student_kp (student_id, kp_id),
    INDEX idx_student (student_id),
    CONSTRAINT fk_profile_kp FOREIGN KEY (kp_id) REFERENCES knowledge_points(kp_id)
) ENGINE=InnoDB COMMENT='学生知识点掌握画像';

-- 5. 答题记录表
CREATE TABLE IF NOT EXISTS answer_record (
    record_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
    student_id    BIGINT NOT NULL,
    ex_id         INT NULL,
    user_answer   TEXT NOT NULL COMMENT '学生作答',
    judge_result  TINYINT NOT NULL DEFAULT 0 COMMENT '0错误/1正确',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    module_id     INT NULL COMMENT '所属模块（习题练习直接写入）',
    source        VARCHAR(32) NOT NULL DEFAULT 'profile_quiz' COMMENT '来源：profile_quiz/exercise_center/module_practice',
    INDEX idx_student (student_id),
    INDEX idx_student_created (student_id, created_at),
    INDEX idx_ex (ex_id),
    CONSTRAINT fk_record_ex FOREIGN KEY (ex_id) REFERENCES exercise(ex_id)
) ENGINE=InnoDB COMMENT='画像构建答题记录';
