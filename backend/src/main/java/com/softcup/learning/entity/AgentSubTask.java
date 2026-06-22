package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("agent_sub_task")
public class AgentSubTask {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private String agentType;
    private String knowledgePoint;
    private String subStatus;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
}
