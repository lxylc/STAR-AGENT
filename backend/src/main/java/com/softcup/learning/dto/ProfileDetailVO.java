package com.softcup.learning.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 画像详情页聚合：student 表基础信息 + learning_profile 学情数据。
 */
@Data
public class ProfileDetailVO {
    private Long id;
    private Long studentId;
    /** 来自 student 表，优先展示 */
    private String realName;
    private String grade;
    private String major;
    /** JSON 数组字符串，来自 student.learn_preferences */
    private String learnPreferences;

    private String mainSubject;
    private String knowledgeBase;
    private String weakPoints;
    private String masteredPoints;
    private BigDecimal dailyStudyHours;
    /** learning_profile 中单值偏好（历史字段，展示时以 learnPreferences 为准） */
    private String learnPreference;
    private String learnGoal;
    private String baseTags;
    private String masteryTags;
    private String styleTags;
    private String goalTags;
    private String behaviorTags;
    private String profileStatus;
    private Integer version;
    private LocalDateTime updatedAt;
}
