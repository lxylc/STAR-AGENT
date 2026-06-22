package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_resource")
public class LearningResource {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private Long profileId;
    private Long taskId;
    private Long subTaskId;
    private String resourceType;
    private String title;
    private String content;
    private String contentJson;
    private String subject;
    private String knowledgePoint;
    private String profileTags;
    private String resourceStatus;
    private LocalDateTime createdAt;
    @TableLogic
    private Integer deleted;
}
