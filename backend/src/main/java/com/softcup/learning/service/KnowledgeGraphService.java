package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.dto.ChapterMasteryVO;
import com.softcup.learning.entity.KnowledgeNode;
import com.softcup.learning.mapper.KnowledgeNodeMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class KnowledgeGraphService {

    private final KnowledgeNodeMapper nodeMapper;

    public List<KnowledgeNode> listBySubject(String subject) {
        return nodeMapper.selectList(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getSubject, subject)
                .orderByAsc(KnowledgeNode::getSortOrder));
    }

    /** 章节节点（一级） */
    public List<KnowledgeNode> listChapterNodes(String subject) {
        return listBySubject(subject).stream()
                .filter(n -> n.getNodeLevel() != null && n.getNodeLevel() == 1)
                .toList();
    }

    /** 叶子知识点（二级） */
    public List<KnowledgeNode> listTopicNodes(String subject) {
        return listBySubject(subject).stream()
                .filter(n -> n.getNodeLevel() != null && n.getNodeLevel() == 2)
                .toList();
    }

    /** 按前置依赖拓扑排序（仅知识点，不含章节） */
    public List<KnowledgeNode> topologicalSort(String subject) {
        return topologicalSortNodes(listTopicNodes(subject));
    }

    public List<ChapterMasteryVO> buildChapterGroups(String subject) {
        List<KnowledgeNode> chapters = listChapterNodes(subject);
        List<KnowledgeNode> topics = listTopicNodes(subject);
        Map<Long, List<KnowledgeNode>> byParent = new LinkedHashMap<>();
        for (KnowledgeNode t : topics) {
            byParent.computeIfAbsent(t.getParentId(), k -> new ArrayList<>()).add(t);
        }
        List<ChapterMasteryVO> groups = new ArrayList<>();
        for (KnowledgeNode ch : chapters) {
            groups.add(ChapterMasteryVO.builder()
                    .chapterName(ch.getNodeName())
                    .sortOrder(ch.getSortOrder())
                    .topics(byParent.getOrDefault(ch.getId(), List.of()))
                    .build());
        }
        return groups;
    }

    private List<KnowledgeNode> topologicalSortNodes(List<KnowledgeNode> nodes) {
        Map<Long, KnowledgeNode> byId = new HashMap<>();
        for (KnowledgeNode n : nodes) {
            byId.put(n.getId(), n);
        }
        Map<Long, Integer> indegree = new HashMap<>();
        for (KnowledgeNode n : nodes) {
            indegree.putIfAbsent(n.getId(), 0);
            List<Long> prereqs = parsePrereqIds(n.getPrerequisiteIds());
            for (Long p : prereqs) {
                if (byId.containsKey(p)) {
                    indegree.merge(n.getId(), 1, Integer::sum);
                }
            }
        }
        // rebuild indegree correctly
        indegree.clear();
        for (KnowledgeNode n : nodes) {
            indegree.put(n.getId(), 0);
        }
        Map<Long, List<Long>> dependents = new HashMap<>();
        for (KnowledgeNode n : nodes) {
            for (Long p : parsePrereqIds(n.getPrerequisiteIds())) {
                if (byId.containsKey(p)) {
                    indegree.merge(n.getId(), 1, Integer::sum);
                    dependents.computeIfAbsent(p, k -> new ArrayList<>()).add(n.getId());
                }
            }
        }
        Queue<Long> q = new LinkedList<>();
        for (KnowledgeNode n : nodes) {
            if (indegree.getOrDefault(n.getId(), 0) == 0) {
                q.add(n.getId());
            }
        }
        List<KnowledgeNode> sorted = new ArrayList<>();
        while (!q.isEmpty()) {
            Long id = q.poll();
            sorted.add(byId.get(id));
            for (Long next : dependents.getOrDefault(id, List.of())) {
                int d = indegree.merge(next, -1, Integer::sum);
                if (d == 0) {
                    q.add(next);
                }
            }
        }
        if (sorted.size() < nodes.size()) {
            sorted.clear();
            sorted.addAll(nodes);
        }
        return sorted;
    }

    public String buildGraphDescription(String subject) {
        List<KnowledgeNode> sorted = topologicalSort(subject);
        StringBuilder sb = new StringBuilder();
        for (KnowledgeNode n : sorted) {
            sb.append("- ").append(n.getNodeName());
            List<Long> prereqs = parsePrereqIds(n.getPrerequisiteIds());
            if (!prereqs.isEmpty()) {
                sb.append(" (前置:");
                prereqs.forEach(id -> {
                    KnowledgeNode p = nodeMapper.selectById(id);
                    if (p != null) sb.append(p.getNodeName()).append(",");
                });
                sb.append(")");
            }
            sb.append("\n");
        }
        return sb.toString();
    }

    public KnowledgeNode findByName(String subject, String name) {
        return nodeMapper.selectOne(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getSubject, subject)
                .eq(KnowledgeNode::getNodeName, name)
                .last("LIMIT 1"));
    }

    private List<Long> parsePrereqIds(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return JSON.parseArray(json, Long.class);
        } catch (Exception e) {
            return List.of();
        }
    }
}
