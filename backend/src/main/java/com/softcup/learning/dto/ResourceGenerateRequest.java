package com.softcup.learning.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class ResourceGenerateRequest {
    @NotNull(message = "studentId不能为空")
    private Long studentId;
    @NotBlank(message = "学科不能为空")
    private String subject;
    /** 单知识点生成 */
    private String knowledgePoint;
    /** 批量知识点 */
    private List<String> knowledgePoints;
    /**
     * 智能体类型：LECTURE / EXERCISE / COURSEWARE，空则全部执行
     */
    private List<String> agentTypes;
    /** 是否批量模式 */
    private Boolean batch = false;
}
