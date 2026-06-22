package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.agent.*;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.dto.AgentTaskVO;
import com.softcup.learning.dto.ResourceGenerateRequest;
import com.softcup.learning.entity.*;
import com.softcup.learning.mapper.AgentSubTaskMapper;
import com.softcup.learning.mapper.AgentTaskMapper;
import com.softcup.learning.mapper.LearningResourceMapper;
import com.softcup.learning.util.MarkdownContentUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * 多智能体统一调度中心：任务创建 → 子任务分发 → 执行 → 资源入库 → 状态汇总
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AgentSchedulerService {

    private static final List<AgentType> DEFAULT_PIPELINE = List.of(
            AgentType.LECTURE, AgentType.EXERCISE, AgentType.COURSEWARE);

    private final AgentTaskMapper taskMapper;
    private final AgentSubTaskMapper subTaskMapper;
    private final LearningResourceMapper resourceMapper;
    private final LearningProfileService profileService;
    private final LearningResourceService resourceService;
    private final AgentRegistry agentRegistry;

    /**
     * 触发资源生成（同步执行，适合演示；生产可改异步+轮询任务状态）
     */
    public AgentTaskVO generate(ResourceGenerateRequest request) {
        LearningProfile profile = profileService.getByStudentId(request.getStudentId());
        if (profile == null) {
            profile = profileService.getOrCreateDraft(request.getStudentId());
            log.warn("学生{}暂无完整画像，将按通用水平生成资源", request.getStudentId());
        }

        List<String> knowledgePoints = resolveKnowledgePoints(request, profile);
        List<AgentType> pipeline = resolvePipeline(request.getAgentTypes());

        AgentTask task = createTask(request, profile, knowledgePoints, pipeline);
        int successCount = 0;
        int failCount = 0;

        try {
            updateTaskStatus(task.getId(), "RUNNING", null);
            for (String kp : knowledgePoints) {
                AgentContext.AgentContextBuilder ctxBuilder = AgentContext.builder()
                        .studentId(request.getStudentId())
                        .profileId(profile.getId())
                        .profile(profile)
                        .taskId(task.getId())
                        .subject(request.getSubject())
                        .knowledgePoint(kp)
                        .profileTagsJson(JSON.toJSONString(profile));

                String lectureContent = null;

                for (AgentType agentType : pipeline) {
                    AgentSubTask sub = createSubTask(task.getId(), agentType, kp);
                    try {
                        markSubRunning(sub.getId());
                        AgentContext ctx = ctxBuilder
                                .subTaskId(sub.getId())
                                .lectureContent(lectureContent)
                                .build();

                        LearningAgent agent = agentRegistry.get(agentType);
                        AgentResult result = agent.execute(ctx);

                        if (agentType == AgentType.LECTURE) {
                            lectureContent = result.getContent();
                            ctxBuilder.lectureContent(lectureContent);
                        }

                        saveResource(task, sub, profile, request.getSubject(), kp, result);
                        markSubSuccess(sub.getId());
                        successCount++;
                    } catch (Exception e) {
                        log.error("智能体执行失败 taskId={} agent={} kp={}", task.getId(), agentType, kp, e);
                        markSubFailed(sub.getId(), e.getMessage());
                        failCount++;
                    }
                }
            }

            String finalStatus = failCount == 0 ? "SUCCESS" : (successCount > 0 ? "PARTIAL" : "FAILED");
            String err = failCount > 0 ? "部分子任务失败: 成功" + successCount + ", 失败" + failCount : null;
            finishTask(task.getId(), finalStatus, err);
        } catch (Exception e) {
            log.error("调度任务失败 taskId={}", task.getId(), e);
            finishTask(task.getId(), "FAILED", e.getMessage());
            throw new BusinessException("资源生成失败: " + e.getMessage());
        }

        return getTaskDetail(task.getId());
    }

    public AgentTaskVO getTaskDetail(Long taskId) {
        AgentTask task = taskMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException("任务不存在");
        }
        List<AgentSubTask> subTasks = subTaskMapper.selectList(new LambdaQueryWrapper<AgentSubTask>()
                .eq(AgentSubTask::getTaskId, taskId)
                .orderByAsc(AgentSubTask::getId));
        List<LearningResource> resources = resourceService.listByTaskId(taskId);
        return AgentTaskVO.builder().task(task).subTasks(subTasks).resources(resources).build();
    }

    public List<AgentTask> listTasks(Long studentId) {
        return taskMapper.selectList(new LambdaQueryWrapper<AgentTask>()
                .eq(AgentTask::getStudentId, studentId)
                .orderByDesc(AgentTask::getCreatedAt)
                .last("LIMIT 50"));
    }

    private List<String> resolveKnowledgePoints(ResourceGenerateRequest req, LearningProfile profile) {
        if (Boolean.TRUE.equals(req.getBatch()) || !CollectionUtils.isEmpty(req.getKnowledgePoints())) {
            if (CollectionUtils.isEmpty(req.getKnowledgePoints())) {
                throw new BusinessException("批量模式请提供 knowledgePoints 列表");
            }
            return req.getKnowledgePoints();
        }
        if (!StringUtils.hasText(req.getKnowledgePoint())) {
            if (profile != null && StringUtils.hasText(profile.getWeakPoints())) {
                try {
                    List<String> weak = JSON.parseArray(profile.getWeakPoints(), String.class);
                    if (!CollectionUtils.isEmpty(weak)) {
                        return List.of(weak.get(0));
                    }
                } catch (Exception ignored) {
                }
            }
            throw new BusinessException("请填写 knowledgePoint 或启用批量 knowledgePoints");
        }
        return List.of(req.getKnowledgePoint());
    }

    private List<AgentType> resolvePipeline(List<String> agentTypes) {
        if (CollectionUtils.isEmpty(agentTypes)) {
            return DEFAULT_PIPELINE;
        }
        List<AgentType> list = new ArrayList<>();
        for (String code : agentTypes) {
            list.add(AgentType.fromCode(code));
        }
        if (list.contains(AgentType.EXERCISE) || list.contains(AgentType.COURSEWARE)) {
            if (!list.contains(AgentType.LECTURE)) {
                list.add(0, AgentType.LECTURE);
            }
        }
        return list.stream().distinct().toList();
    }

    private AgentTask createTask(ResourceGenerateRequest req, LearningProfile profile,
                                 List<String> kps, List<AgentType> pipeline) {
        AgentTask task = new AgentTask();
        task.setStudentId(req.getStudentId());
        task.setProfileId(profile.getId());
        task.setSubject(req.getSubject());
        task.setKnowledgePoint(kps.size() == 1 ? kps.get(0) : null);
        task.setTaskType(kps.size() > 1 ? "BATCH" : "SINGLE");
        task.setAgentTypes(JSON.toJSONString(pipeline.stream().map(AgentType::getCode).toList()));
        if (kps.size() > 1) {
            task.setBatchPoints(JSON.toJSONString(kps));
        }
        task.setTaskStatus("PENDING");
        taskMapper.insert(task);
        return task;
    }

    private AgentSubTask createSubTask(Long taskId, AgentType type, String kp) {
        AgentSubTask sub = new AgentSubTask();
        sub.setTaskId(taskId);
        sub.setAgentType(type.getCode());
        sub.setKnowledgePoint(kp);
        sub.setSubStatus("PENDING");
        subTaskMapper.insert(sub);
        return sub;
    }

    private void saveResource(AgentTask task, AgentSubTask sub, LearningProfile profile,
                              String subject, String kp, AgentResult result) {
        LearningResource r = new LearningResource();
        r.setStudentId(task.getStudentId());
        r.setProfileId(profile.getId());
        r.setTaskId(task.getId());
        r.setSubTaskId(sub.getId());
        r.setResourceType(result.getResourceType().getCode());
        r.setTitle(result.getTitle());
        r.setContent(MarkdownContentUtil.sanitize(result.getContent()));
        r.setContentJson(result.getContentJson());
        r.setSubject(subject);
        r.setKnowledgePoint(kp);
        r.setProfileTags(JSON.toJSONString(profile));
        r.setResourceStatus("published");
        resourceMapper.insert(r);
    }

    public void updateTaskStatus(Long taskId, String status, String error) {
        AgentTask t = taskMapper.selectById(taskId);
        t.setTaskStatus(status);
        t.setErrorMessage(error);
        taskMapper.updateById(t);
    }

    public void finishTask(Long taskId, String status, String error) {
        AgentTask t = taskMapper.selectById(taskId);
        t.setTaskStatus(status);
        t.setErrorMessage(error);
        t.setFinishedAt(LocalDateTime.now());
        taskMapper.updateById(t);
    }

    public void markSubRunning(Long subId) {
        AgentSubTask s = subTaskMapper.selectById(subId);
        s.setSubStatus("RUNNING");
        s.setStartedAt(LocalDateTime.now());
        subTaskMapper.updateById(s);
    }

    public void markSubSuccess(Long subId) {
        AgentSubTask s = subTaskMapper.selectById(subId);
        s.setSubStatus("SUCCESS");
        s.setFinishedAt(LocalDateTime.now());
        subTaskMapper.updateById(s);
    }

    public void markSubFailed(Long subId, String error) {
        AgentSubTask s = subTaskMapper.selectById(subId);
        s.setSubStatus("FAILED");
        s.setErrorMessage(error);
        s.setFinishedAt(LocalDateTime.now());
        subTaskMapper.updateById(s);
    }
}
