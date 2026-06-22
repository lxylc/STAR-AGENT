package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("student")
public class Student {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String username;
    private String realName;
    private String passwordHash;
    private String role;
    private String grade;
    private String major;
    /** JSON 数组字符串 */
    private String learnPreferences;
    /** 1=启用 0=禁用 */
    private Integer enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    @TableLogic
    private Integer deleted;
}
