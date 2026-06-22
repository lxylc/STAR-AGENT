package com.softcup.learning.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("knowledge_node")
public class KnowledgeNode {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String subject;
    private String nodeName;
    private Long parentId;
    private Integer nodeLevel;
    private Integer sortOrder;
    private String prerequisiteIds;
    private String description;
    private LocalDateTime createdAt;
}
