package com.softcup.learning.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class PathPlanRequest {
    @NotNull
    private Long studentId;
    @NotBlank
    private String subject;
}
