package com.softcup.learning.dto;

import lombok.Data;

import java.util.List;

@Data
public class StudentSettingsRequest {
    private Long studentId;
    private String realName;
    private String grade;
    private String major;
    private List<String> learnPreferences;
}
