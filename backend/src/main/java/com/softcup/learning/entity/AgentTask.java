package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("agent_task")
public class AgentTask {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private Long profileId;
    private String subject;
    private String knowledgePoint;
    private String taskType;
    private String agentTypes;
    private String batchPoints;
    private String taskStatus;
    private String errorMessage;
    private LocalDateTime createdAt;
    private LocalDateTime finishedAt;
    @TableLogic
    private Integer deleted;
}
