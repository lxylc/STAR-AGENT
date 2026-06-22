package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("learning_profile")
public class LearningProfile {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private String grade;
    private String major;
    private String mainSubject;
    private String knowledgeBase;
    /** JSON 字符串存储 */
    private String weakPoints;
    /** JSON 字符串：已掌握的知识点名称（由画像构建/练习/交流同步） */
    private String masteredPoints;
    private BigDecimal dailyStudyHours;
    private String learnPreference;
    private String learnGoal;
    private String baseTags;
    private String masteryTags;
    private String styleTags;
    private String goalTags;
    private String behaviorTags;
    private String profileStatus;
    private Integer version;
    private String rawExtractJson;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    @TableLogic
    private Integer deleted;
}
