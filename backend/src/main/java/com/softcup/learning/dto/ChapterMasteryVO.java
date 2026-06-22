package com.softcup.learning.dto;

import com.softcup.learning.entity.KnowledgeNode;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class ChapterMasteryVO {
    private String chapterName;
    private Integer sortOrder;
    private List<KnowledgeNode> topics;
}
