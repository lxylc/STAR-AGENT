package com.softcup.learning.dto;

import com.softcup.learning.entity.KnowledgeNode;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class MasteryStatusVO {
    private List<KnowledgeNode> nodes;
    private List<ChapterMasteryVO> chapterGroups;
    private List<String> topologicalOrder;
    private List<String> masteredPoints;
    /** 未掌握的知识点（由画像评估同步，默认全部待学） */
    private List<String> unmasteredPoints;
}
