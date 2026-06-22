package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_path")
public class LearningPath {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private Long profileId;
    private String subject;
    private String pathName;
    private String pathSummary;
    private String stagesJson;
    private String pathStatus;
    private Integer version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    @TableLogic
    private Integer deleted;
}
