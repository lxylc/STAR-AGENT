package com.softcup.learning.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ProfilePathSyncRequest {
    @NotNull
    private Long studentId;
    @NotNull
    private String subject;
}
