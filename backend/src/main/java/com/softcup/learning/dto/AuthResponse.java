package com.softcup.learning.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class AuthResponse {
    private Long studentId;
    private String username;
    private String realName;
    private String role;
    private String token;
    private String grade;
    private String major;
    private String learnPreferences;
    private Boolean enabled;
}
