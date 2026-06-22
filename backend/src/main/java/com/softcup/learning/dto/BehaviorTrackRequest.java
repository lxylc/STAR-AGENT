package com.softcup.learning.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.Map;

@Data
public class BehaviorTrackRequest {
    @NotNull
    private Long studentId;
    @NotBlank
    private String eventType;
    private String eventSource;
    private Map<String, Object> payload;
}
