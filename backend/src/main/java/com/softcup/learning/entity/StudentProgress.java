package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("student_progress")
public class StudentProgress {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private String subject;
    private String knowledgePoint;
    private Integer progressPct;
    private String masteryLevel;
    private Integer studyMinutes;
    private LocalDateTime lastStudyAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
