package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("learning_path_item")
public class LearningPathItem {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long pathId;
    private Integer stageNo;
    private String stageName;
    private String knowledgePoint;
    private Long nodeId;
    private Integer sortOrder;
    private String itemStatus;
    private Integer priority;
    private String focusReason;
    private BigDecimal estimatedHours;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
