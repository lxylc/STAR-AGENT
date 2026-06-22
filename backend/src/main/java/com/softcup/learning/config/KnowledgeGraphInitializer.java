package com.softcup.learning.config;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.common.CourseConstants;
import com.softcup.learning.entity.KnowledgeNode;
import com.softcup.learning.mapper.KnowledgeNodeMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 知识图谱以数据库 knowledge_node 为唯一数据源，不在后端嵌入知识点。
 * 首次部署请执行 db/knowledge-seed.sql；启动时仅校验前置依赖链。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class KnowledgeGraphInitializer implements ApplicationRunner {

    private final KnowledgeNodeMapper nodeMapper;

    @Override
    public void run(ApplicationArguments args) {
        String subject = CourseConstants.SUBJECT;
        long count = nodeMapper.selectCount(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getSubject, subject));
        if (count == 0) {
            log.warn("knowledge_node 表暂无「{}」数据，请先导入: src/main/resources/db/knowledge-seed.sql", subject);
            return;
        }
        linkTopicPrerequisites(subject);
    }

    /** 按 sort_order 为二级知识点建立链式前置关系 */
    private void linkTopicPrerequisites(String subject) {
        List<KnowledgeNode> topics = nodeMapper.selectList(new LambdaQueryWrapper<KnowledgeNode>()
                .eq(KnowledgeNode::getSubject, subject)
                .eq(KnowledgeNode::getNodeLevel, 2)
                .orderByAsc(KnowledgeNode::getSortOrder));
        for (int i = 0; i < topics.size(); i++) {
            KnowledgeNode node = topics.get(i);
            List<Long> prereqs = i > 0 ? List.of(topics.get(i - 1).getId()) : List.of();
            String expected = JSON.toJSONString(prereqs);
            if (!expected.equals(node.getPrerequisiteIds())) {
                node.setPrerequisiteIds(expected);
                nodeMapper.updateById(node);
            }
        }
    }
}
