package com.softcup.learning.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ProgressUpdateRequest {
    @NotNull
    private Long studentId;
    @NotBlank
    private String subject;
    @NotBlank
    private String knowledgePoint;
    @Min(0) @Max(100)
    private Integer progressPct;
    private String masteryLevel;
    private Integer studyMinutes;
}
