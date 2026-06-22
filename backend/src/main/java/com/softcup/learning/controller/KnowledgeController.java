package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.MasteryStatusVO;
import com.softcup.learning.entity.KnowledgeNode;
import com.softcup.learning.service.KnowledgeGraphService;
import com.softcup.learning.service.KnowledgeMasteryService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/knowledge")
@RequiredArgsConstructor
public class KnowledgeController {

    private final KnowledgeGraphService graphService;
    private final KnowledgeMasteryService masteryService;

    @GetMapping("/graph")
    public Result<Map<String, Object>> graph(@RequestParam String subject) {
        List<KnowledgeNode> nodes = graphService.listBySubject(subject);
        List<KnowledgeNode> sorted = graphService.topologicalSort(subject);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("nodes", nodes);
        data.put("topics", graphService.listTopicNodes(subject));
        data.put("chapters", graphService.listChapterNodes(subject));
        data.put("chapterGroups", graphService.buildChapterGroups(subject));
        data.put("topologicalOrder", sorted.stream().map(KnowledgeNode::getNodeName).toList());
        data.put("description", graphService.buildGraphDescription(subject));
        return Result.ok(data);
    }

    /** 获取知识点掌握状态（只读，数据来自画像构建/练习/交流同步） */
    @GetMapping("/mastery")
    public Result<MasteryStatusVO> mastery(
            @RequestParam Long studentId,
            @RequestParam String subject) {
        return Result.ok(masteryService.getStatus(studentId, subject));
    }
}
