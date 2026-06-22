package com.softcup.learning.dto;

import lombok.Data;

import java.util.List;

@Data
public class AdminBatchResetRequest {
    private List<Long> studentIds;
    /** 可选，默认 123456 */
    private String newPassword;
}
