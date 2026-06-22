package com.softcup.learning.service;



import com.alibaba.fastjson2.JSON;

import com.softcup.learning.dto.MasteryStatusVO;

import com.softcup.learning.entity.KnowledgeNode;

import com.softcup.learning.entity.LearningProfile;

import lombok.RequiredArgsConstructor;

import org.springframework.stereotype.Service;

import org.springframework.util.StringUtils;



import java.util.*;

import java.util.stream.Collectors;



/**

 * 知识点掌握度查询：数据由画像构建、练习与日常交流同步，不支持手动勾选。

 */

@Service

@RequiredArgsConstructor

public class KnowledgeMasteryService {



    private final KnowledgeGraphService graphService;

    private final LearningProfileService profileService;



    public MasteryStatusVO getStatus(Long studentId, String subject) {

        List<KnowledgeNode> sorted = graphService.topologicalSort(subject);

        Set<Long> masteredIds = parseMasteredIds(profileService.getByStudentId(studentId), sorted);

        List<String> masteredIdStr = masteredIds.stream().map(String::valueOf).sorted().toList();

        List<String> unmastered = sorted.stream()

                .filter(n -> !masteredIds.contains(n.getId()))

                .map(KnowledgeNode::getNodeName)

                .toList();

        return MasteryStatusVO.builder()

                .nodes(sorted)

                .chapterGroups(graphService.buildChapterGroups(subject))

                .topologicalOrder(sorted.stream().map(KnowledgeNode::getNodeName).toList())

                .masteredPoints(masteredIdStr)

                .unmasteredPoints(unmastered)

                .build();

    }



    public List<String> getUnmasteredPoints(Long studentId, String subject) {

        return getStatus(studentId, subject).getUnmasteredPoints();

    }



    /** 兼容同步数据：mastered_points 可为知识点名称或历史遗留的节点 ID */

    public Set<Long> parseMasteredIds(LearningProfile profile, List<KnowledgeNode> allNodes) {

        if (profile == null || !StringUtils.hasText(profile.getMasteredPoints())) {

            return Set.of();

        }

        Set<Long> validIds = allNodes.stream().map(KnowledgeNode::getId).collect(Collectors.toSet());

        Map<String, Long> nameToId = new HashMap<>();

        for (KnowledgeNode n : allNodes) {

            nameToId.putIfAbsent(n.getNodeName(), n.getId());

        }

        try {

            List<String> parsed = JSON.parseArray(profile.getMasteredPoints(), String.class);

            if (parsed == null) {

                return Set.of();

            }

            Set<Long> ids = new LinkedHashSet<>();

            for (String entry : parsed) {

                if (!StringUtils.hasText(entry)) {

                    continue;

                }

                String trimmed = entry.trim();

                if (trimmed.matches("\\d+")) {

                    long id = Long.parseLong(trimmed);

                    if (validIds.contains(id)) {

                        ids.add(id);

                    }

                } else if (nameToId.containsKey(trimmed)) {

                    ids.add(nameToId.get(trimmed));

                }

            }

            return ids;

        } catch (Exception e) {

            return Set.of();

        }

    }



    public Set<String> unmasteredSet(Long studentId, String subject) {

        return new HashSet<>(getUnmasteredPoints(studentId, subject));

    }

}

