package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("learning_behavior_event")
public class LearningBehaviorEvent {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private String eventType;
    private String eventSource;
    private String payloadJson;
    private LocalDateTime createdAt;
}
