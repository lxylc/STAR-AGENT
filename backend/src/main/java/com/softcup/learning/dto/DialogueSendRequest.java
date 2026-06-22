package com.softcup.learning.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class DialogueSendRequest {
    @NotNull(message = "studentId不能为空")
    private Long studentId;
    @NotBlank(message = "消息内容不能为空")
    private String content;
    /** 是否在本轮后尝试抽取画像 */
    private Boolean tryExtract = false;
}
