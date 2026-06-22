package com.softcup.learning.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ApplyEvaluationRequest {
    @NotNull
    private Long studentId;
    @NotNull
    private String subject;
    private List<String> weakModules;
    private String pushStrategy;
    private String pathAdjustment;
    private List<String> recommendedActions;
    /** lecture | exercise | courseware */
    private List<String> preferResourceTypes;
    private Map<String, Object> extra;
}
