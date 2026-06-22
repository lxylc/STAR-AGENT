package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("profile_dialogue")
public class ProfileDialogue {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long studentId;
    private Long profileId;
    private String role;
    private String content;
    private Integer roundNo;
    private LocalDateTime createdAt;
}
