package com.softcup.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.entity.LearningResource;
import com.softcup.learning.mapper.LearningResourceMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

@Service
@RequiredArgsConstructor
public class LearningResourceService {

    private final LearningResourceMapper resourceMapper;

    public LearningResource getById(Long id) {
        LearningResource r = resourceMapper.selectById(id);
        if (r == null) {
            throw new BusinessException("资源不存在");
        }
        return r;
    }

    public List<LearningResource> list(Long studentId, String subject, String resourceType, String knowledgePoint) {
        LambdaQueryWrapper<LearningResource> q = new LambdaQueryWrapper<LearningResource>()
                .eq(LearningResource::getStudentId, studentId)
                .orderByDesc(LearningResource::getCreatedAt);
        if (StringUtils.hasText(subject)) {
            q.eq(LearningResource::getSubject, subject);
        }
        if (StringUtils.hasText(resourceType)) {
            q.eq(LearningResource::getResourceType, resourceType);
        }
        if (StringUtils.hasText(knowledgePoint)) {
            q.like(LearningResource::getKnowledgePoint, knowledgePoint);
        }
        return resourceMapper.selectList(q);
    }

    public List<LearningResource> listByTaskId(Long taskId) {
        return resourceMapper.selectList(new LambdaQueryWrapper<LearningResource>()
                .eq(LearningResource::getTaskId, taskId)
                .orderByAsc(LearningResource::getId));
    }
}
