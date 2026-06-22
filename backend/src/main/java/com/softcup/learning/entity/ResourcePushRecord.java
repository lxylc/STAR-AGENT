package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("resource_push_record")
public class ResourcePushRecord {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private Long pathId;
    private Long pathItemId;
    private Long resourceId;
    private String pushType;
    private String pushReason;
    private String readStatus;
    private LocalDateTime pushedAt;
    private LocalDateTime readAt;
}
