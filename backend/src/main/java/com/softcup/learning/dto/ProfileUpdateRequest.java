package com.softcup.learning.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class ProfileUpdateRequest {
    @NotNull
    private Long id;
    private String grade;
    private String major;
    private String mainSubject;
    private String knowledgeBase;
    private String weakPoints;
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
}
