package com.softcup.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.entity.*;
import com.softcup.learning.mapper.LearningPathItemMapper;
import com.softcup.learning.mapper.LearningResourceMapper;
import com.softcup.learning.mapper.ResourcePushRecordMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 资源推送规则：薄弱点优先 + 学习偏好匹配 + 当前阶段步骤
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ResourcePushService {

    private final ResourcePushRecordMapper pushMapper;
    private final LearningResourceMapper resourceMapper;
    private final LearningPathItemMapper pathItemMapper;
    private final LearningProfileService profileService;

    /** 评估报告驱动的推送偏好（资源类型加权） */
    private final ThreadLocal<Set<String>> preferTypesHolder = new ThreadLocal<>();

    public List<ResourcePushRecord> pushForPath(LearningPath path, List<LearningPathItem> items, String pushType) {
        return pushForPath(path, items, pushType, null);
    }

    public List<ResourcePushRecord> pushForPath(LearningPath path, List<LearningPathItem> items, String pushType,
                                                List<String> preferResourceTypes) {
        if (preferResourceTypes != null && !preferResourceTypes.isEmpty()) {
            preferTypesHolder.set(new HashSet<>(preferResourceTypes));
        }
        try {
            return doPushForPath(path, items, pushType);
        } finally {
            preferTypesHolder.remove();
        }
    }

    private List<ResourcePushRecord> doPushForPath(LearningPath path, List<LearningPathItem> items, String pushType) {
        LearningProfile profile = profileService.getByStudentId(path.getStudentId());
        String preference = profile != null ? profile.getLearnPreference() : "mixed";
        Set<String> weakSet = parseWeakPoints(profile);

        Set<String> unmastered = parseWeakPoints(profile);

        List<LearningPathItem> targets = items.stream()
                .filter(i -> "in_progress".equals(i.getItemStatus())
                        || ("pending".equals(i.getItemStatus()) && isWeakPoint(i.getKnowledgePoint(), unmastered)))
                .sorted(Comparator.comparing(LearningPathItem::getPriority)
                        .thenComparing(LearningPathItem::getStageNo)
                        .thenComparing(LearningPathItem::getSortOrder))
                .limit(5)
                .toList();

        if (targets.isEmpty() && !items.isEmpty()) {
            targets = List.of(items.get(0));
        }

        List<ResourcePushRecord> pushed = new ArrayList<>();
        for (LearningPathItem item : targets) {
            List<LearningResource> candidates = findResources(path.getStudentId(), path.getSubject(), item.getKnowledgePoint());
            if (candidates.isEmpty()) {
                log.info("暂无匹配资源 student={} kp={}", path.getStudentId(), item.getKnowledgePoint());
                continue;
            }
            candidates.sort((a, b) -> scoreResource(b, preference, weakSet) - scoreResource(a, preference, weakSet));
            LearningResource best = candidates.get(0);
            if (alreadyPushed(path.getId(), item.getId(), best.getId())) {
                continue;
            }
            ResourcePushRecord record = new ResourcePushRecord();
            record.setStudentId(path.getStudentId());
            record.setPathId(path.getId());
            record.setPathItemId(item.getId());
            record.setResourceId(best.getId());
            record.setPushType(pushType);
            record.setPushReason(buildReason(item, preference, isWeakPoint(item.getKnowledgePoint(), weakSet)));
            record.setReadStatus("unread");
            record.setPushedAt(LocalDateTime.now());
            pushMapper.insert(record);
            pushed.add(record);
        }
        return pushed;
    }

    public List<ResourcePushRecord> listByStudent(Long studentId, String readStatus) {
        LambdaQueryWrapper<ResourcePushRecord> q = new LambdaQueryWrapper<ResourcePushRecord>()
                .eq(ResourcePushRecord::getStudentId, studentId)
                .orderByDesc(ResourcePushRecord::getPushedAt);
        if (StringUtils.hasText(readStatus)) {
            q.eq(ResourcePushRecord::getReadStatus, readStatus);
        }
        return pushMapper.selectList(q);
    }

    public void markRead(Long pushId) {
        ResourcePushRecord r = pushMapper.selectById(pushId);
        if (r != null) {
            r.setReadStatus("read");
            r.setReadAt(LocalDateTime.now());
            pushMapper.updateById(r);
        }
    }

    private List<LearningResource> findResources(Long studentId, String subject, String kp) {
        List<LearningResource> list = resourceMapper.selectList(new LambdaQueryWrapper<LearningResource>()
                .eq(LearningResource::getStudentId, studentId)
                .eq(LearningResource::getSubject, subject)
                .orderByDesc(LearningResource::getCreatedAt));
        return list.stream()
                .filter(r -> matchKnowledgePoint(r.getKnowledgePoint(), kp))
                .collect(Collectors.toList());
    }

    private boolean matchKnowledgePoint(String resourceKp, String pathKp) {
        if (resourceKp == null || pathKp == null) return false;
        return resourceKp.contains(pathKp) || pathKp.contains(resourceKp)
                || resourceKp.equals(pathKp);
    }

    private int scoreResource(LearningResource r, String preference, Set<String> weakSet) {
        int score = 0;
        if (isWeakPoint(r.getKnowledgePoint(), weakSet)) score += 10;
        String type = r.getResourceType();
        Set<String> preferTypes = preferTypesHolder.get();
        if (preferTypes != null && !preferTypes.isEmpty() && type != null && preferTypes.contains(type)) {
            score += 12;
        }
        if ("text".equals(preference) && "lecture".equals(type)) score += 8;
        else if ("exercise".equals(preference) && "exercise".equals(type)) score += 8;
        else if ("video".equals(preference) && "courseware".equals(type)) score += 8;
        else if ("mixed".equals(preference)) score += 4;
        else score += 2;
        return score;
    }

    private boolean alreadyPushed(Long pathId, Long itemId, Long resourceId) {
        return pushMapper.selectCount(new LambdaQueryWrapper<ResourcePushRecord>()
                .eq(ResourcePushRecord::getPathId, pathId)
                .eq(ResourcePushRecord::getPathItemId, itemId)
                .eq(ResourcePushRecord::getResourceId, resourceId)) > 0;
    }

    private String buildReason(LearningPathItem item, String preference, boolean weak) {
        StringBuilder sb = new StringBuilder("阶段").append(item.getStageNo()).append("·").append(item.getKnowledgePoint());
        if (weak) sb.append("；薄弱点强化");
        sb.append("；匹配学习偏好:").append(preference);
        if (StringUtils.hasText(item.getFocusReason())) {
            sb.append("；").append(item.getFocusReason());
        }
        return sb.toString();
    }

    private boolean isWeakPoint(String kp, Set<String> weakSet) {
        if (kp == null || weakSet.isEmpty()) return false;
        return weakSet.stream().anyMatch(w -> w != null && (w.contains(kp) || kp.contains(w) || w.equals(kp)));
    }

    private Set<String> parseWeakPoints(LearningProfile profile) {
        if (profile == null || !StringUtils.hasText(profile.getWeakPoints())) {
            return Set.of();
        }
        try {
            return new HashSet<>(com.alibaba.fastjson2.JSON.parseArray(profile.getWeakPoints(), String.class));
        } catch (Exception e) {
            return Set.of();
        }
    }
}
