package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.dto.ApplyEvaluationRequest;
import com.softcup.learning.dto.LearningPathDetailVO;
import com.softcup.learning.dto.PathPlanRequest;
import com.softcup.learning.dto.ProfilePathSyncRequest;
import com.softcup.learning.entity.*;
import com.softcup.learning.mapper.LearningPathItemMapper;
import com.softcup.learning.mapper.LearningPathMapper;
import com.softcup.learning.mapper.StudentProgressMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class LearningPathService {

    private final LearningPathMapper pathMapper;
    private final LearningPathItemMapper itemMapper;
    private final LearningProfileService profileService;
    private final KnowledgeGraphService graphService;
    private final StudentProgressMapper progressMapper;
    private final ResourcePushService pushService;
    private final KnowledgeMasteryService masteryService;

    public LearningPathDetailVO planPath(PathPlanRequest request) {
        archiveActivePaths(request.getStudentId(), request.getSubject());
        LearningProfile profile = profileService.getByStudentId(request.getStudentId());
        if (profile == null) {
            profile = profileService.getOrCreateDraft(request.getStudentId());
        }

        if (graphService.listBySubject(request.getSubject()).isEmpty()) {
            throw new BusinessException("学科「" + request.getSubject() + "」暂无知识图谱，请重启后端完成初始化或联系管理员");
        }
        List<StudentProgress> progressList = progressMapper.selectList(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, request.getStudentId())
                .eq(StudentProgress::getSubject, request.getSubject()));

        List<KnowledgeNode> sortedNodes = graphService.topologicalSort(request.getSubject());
        Set<Long> masteredIds = masteryService.parseMasteredIds(profile, sortedNodes);
        List<KnowledgeNode> unmasteredNodes = sortedNodes.stream()
                .filter(n -> !masteredIds.contains(n.getId()))
                .toList();

        profile.setWeakPoints(JSON.toJSONString(unmasteredNodes.stream().map(KnowledgeNode::getNodeName).toList()));
        profileService.saveProfileFields(profile);

        JSONObject plan = unmasteredNodes.isEmpty()
                ? buildAllMasteredPlan(request.getSubject())
                : buildPlanFromUnmastered(request.getSubject(), unmasteredNodes);

        LearningPath path = new LearningPath();
        path.setStudentId(request.getStudentId());
        path.setProfileId(profile.getId());
        path.setSubject(request.getSubject());
        path.setPathName(plan.getString("pathName"));
        path.setPathSummary(plan.getString("pathSummary"));
        path.setStagesJson(plan.getJSONArray("stages").toJSONString());
        path.setPathStatus("active");
        path.setVersion(1);
        pathMapper.insert(path);

        List<LearningPathItem> items = savePathItems(path, plan.getJSONArray("stages"));
        syncItemsWithProgress(items, progressList);

        List<ResourcePushRecord> pushes = pushService.pushForPath(path, listItems(path.getId()), "auto");
        return buildDetail(path, items, pushes, progressList);
    }

    public LearningPathDetailVO replan(Long pathId) {
        LearningPath old = pathMapper.selectById(pathId);
        if (old == null) {
            throw new BusinessException("路径不存在");
        }
        PathPlanRequest req = new PathPlanRequest();
        req.setStudentId(old.getStudentId());
        req.setSubject(old.getSubject());
        return planPath(req);
    }

    public LearningPathDetailVO getActivePath(Long studentId, String subject) {
        LearningPath path = pathMapper.selectOne(new LambdaQueryWrapper<LearningPath>()
                .eq(LearningPath::getStudentId, studentId)
                .eq(LearningPath::getSubject, subject)
                .eq(LearningPath::getPathStatus, "active")
                .orderByDesc(LearningPath::getVersion)
                .last("LIMIT 1"));
        if (path == null) {
            return null;
        }
        List<LearningPathItem> items = listItems(path.getId());
        List<StudentProgress> progress = progressMapper.selectList(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, studentId)
                .eq(StudentProgress::getSubject, subject));
        List<ResourcePushRecord> pushes = pushService.listByStudent(studentId, null);
        pushes = pushes.stream().filter(p -> path.getId().equals(p.getPathId())).toList();
        return buildDetail(path, items, pushes, progress);
    }

    public LearningPathDetailVO getPathDetail(Long pathId) {
        LearningPath path = pathMapper.selectById(pathId);
        if (path == null) {
            throw new BusinessException("路径不存在");
        }
        List<LearningPathItem> items = listItems(pathId);
        List<StudentProgress> progress = progressMapper.selectList(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, path.getStudentId())
                .eq(StudentProgress::getSubject, path.getSubject()));
        List<ResourcePushRecord> pushes = pushService.listByStudent(path.getStudentId(), null).stream()
                .filter(p -> pathId.equals(p.getPathId())).toList();
        return buildDetail(path, items, pushes, progress);
    }

    public List<ResourcePushRecord> refreshPush(Long pathId) {
        return refreshPush(pathId, null);
    }

    public List<ResourcePushRecord> refreshPush(Long pathId, List<String> preferResourceTypes) {
        LearningPath path = pathMapper.selectById(pathId);
        if (path == null) {
            throw new BusinessException("路径不存在");
        }
        List<LearningPathItem> items = listItems(pathId);
        List<StudentProgress> progress = progressMapper.selectList(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, path.getStudentId())
                .eq(StudentProgress::getSubject, path.getSubject()));
        syncItemsWithProgress(items, progress);
        return pushService.pushForPath(path, listItems(pathId), "refresh", preferResourceTypes);
    }

    /**
     * 根据评估报告调整路径项优先级并刷新推送（非全量 replan）。
     */
    public LearningPathDetailVO applyEvaluationAdjustments(ApplyEvaluationRequest req) {
        LearningPath path = pathMapper.selectOne(new LambdaQueryWrapper<LearningPath>()
                .eq(LearningPath::getStudentId, req.getStudentId())
                .eq(LearningPath::getSubject, req.getSubject())
                .eq(LearningPath::getPathStatus, "active")
                .orderByDesc(LearningPath::getVersion)
                .last("LIMIT 1"));
        if (path == null) {
            return planPath(buildPlanRequest(req.getStudentId(), req.getSubject()));
        }

        List<String> weakModules = req.getWeakModules() != null ? req.getWeakModules() : List.of();
        List<LearningPathItem> items = listItems(path.getId());
        int adjusted = 0;
        for (LearningPathItem item : items) {
            if (matchesWeakModule(item.getKnowledgePoint(), weakModules)) {
                item.setPriority(1);
                item.setFocusReason(buildEvalFocusReason(req, item.getKnowledgePoint()));
                itemMapper.updateById(item);
                adjusted++;
            } else if (!"completed".equals(item.getItemStatus())) {
                item.setPriority(Math.min(5, (item.getPriority() != null ? item.getPriority() : 5) + 1));
                itemMapper.updateById(item);
            }
        }
        if (adjusted == 0 && !weakModules.isEmpty()) {
            for (LearningPathItem item : items) {
                if ("pending".equals(item.getItemStatus()) || "in_progress".equals(item.getItemStatus())) {
                    item.setPriority(2);
                    item.setFocusReason("评估建议：加强薄弱模块练习");
                    itemMapper.updateById(item);
                    break;
                }
            }
        }

        path.setVersion((path.getVersion() != null ? path.getVersion() : 1) + 1);
        String summary = path.getPathSummary() != null ? path.getPathSummary() : "";
        if (StringUtils.hasText(req.getPathAdjustment())) {
            path.setPathSummary(summary + " 【评估调整】" + req.getPathAdjustment());
        }
        pathMapper.updateById(path);

        List<String> preferTypes = inferPreferResourceTypes(req);
        List<ResourcePushRecord> pushes = pushService.pushForPath(path, listItems(path.getId()), "eval_adjust", preferTypes);
        List<StudentProgress> progress = progressMapper.selectList(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, req.getStudentId())
                .eq(StudentProgress::getSubject, req.getSubject()));
        return buildDetail(path, listItems(path.getId()), pushes, progress);
    }

    /**
     * 画像/辅导掌握度同步后：提升弱项路径优先级并刷新推送。
     */
    public LearningPathDetailVO syncFromProfile(ProfilePathSyncRequest req) {
        LearningProfile profile = profileService.getByStudentId(req.getStudentId());
        if (profile == null) {
            return null;
        }
        Set<String> weakSet = parseWeakNames(profile);
        LearningPath path = pathMapper.selectOne(new LambdaQueryWrapper<LearningPath>()
                .eq(LearningPath::getStudentId, req.getStudentId())
                .eq(LearningPath::getSubject, req.getSubject())
                .eq(LearningPath::getPathStatus, "active")
                .last("LIMIT 1"));
        if (path == null) {
            return null;
        }
        List<LearningPathItem> items = listItems(path.getId());
        for (LearningPathItem item : items) {
            if (isWeakKp(item.getKnowledgePoint(), weakSet)) {
                item.setPriority(1);
                item.setFocusReason("画像掌握度更新：该知识点为薄弱项，已提升优先级");
                itemMapper.updateById(item);
            }
        }
        List<ResourcePushRecord> pushes = pushService.pushForPath(path, listItems(path.getId()), "profile_sync");
        List<StudentProgress> progress = progressMapper.selectList(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, req.getStudentId())
                .eq(StudentProgress::getSubject, req.getSubject()));
        return buildDetail(path, listItems(path.getId()), pushes, progress);
    }

    private PathPlanRequest buildPlanRequest(Long studentId, String subject) {
        PathPlanRequest r = new PathPlanRequest();
        r.setStudentId(studentId);
        r.setSubject(subject);
        return r;
    }

    private boolean matchesWeakModule(String kp, List<String> weakModules) {
        if (kp == null || weakModules.isEmpty()) return false;
        return weakModules.stream().anyMatch(w -> w != null
                && (kp.contains(w) || w.contains(kp) || kp.equals(w)));
    }

    private String buildEvalFocusReason(ApplyEvaluationRequest req, String kp) {
        StringBuilder sb = new StringBuilder("评估驱动：薄弱强化 · ").append(kp);
        if (StringUtils.hasText(req.getPushStrategy())) {
            sb.append("；").append(req.getPushStrategy());
        }
        return sb.toString();
    }

    private List<String> inferPreferResourceTypes(ApplyEvaluationRequest req) {
        if (req.getPreferResourceTypes() != null && !req.getPreferResourceTypes().isEmpty()) {
            return req.getPreferResourceTypes();
        }
        String strategy = req.getPushStrategy() != null ? req.getPushStrategy() : "";
        if (strategy.contains("习题") || strategy.contains("练习")) {
            return List.of("exercise");
        }
        if (strategy.contains("讲义") || strategy.contains("理论")) {
            return List.of("lecture");
        }
        if (strategy.contains("课件") || strategy.contains("视频")) {
            return List.of("courseware");
        }
        return List.of("lecture", "exercise");
    }

    private Set<String> parseWeakNames(LearningProfile profile) {
        if (profile == null || !StringUtils.hasText(profile.getWeakPoints())) {
            return Set.of();
        }
        try {
            return new java.util.HashSet<>(JSON.parseArray(profile.getWeakPoints(), String.class));
        } catch (Exception e) {
            return Set.of();
        }
    }

    private boolean isWeakKp(String kp, Set<String> weakSet) {
        if (kp == null || weakSet.isEmpty()) return false;
        return weakSet.stream().anyMatch(w -> w != null && (w.contains(kp) || kp.contains(w) || w.equals(kp)));
    }

    /** 进度变化后微调路径与推送 */
    public void adjustAfterProgress(Long studentId, String subject, String knowledgePoint, int progressPct) {
        LearningPath path = pathMapper.selectOne(new LambdaQueryWrapper<LearningPath>()
                .eq(LearningPath::getStudentId, studentId)
                .eq(LearningPath::getSubject, subject)
                .eq(LearningPath::getPathStatus, "active")
                .last("LIMIT 1"));
        if (path == null) {
            return;
        }
        List<LearningPathItem> items = listItems(path.getId());
        for (LearningPathItem item : items) {
            String progressKey = item.getNodeId() != null
                    ? String.valueOf(item.getNodeId())
                    : item.getKnowledgePoint();
            if (!knowledgePoint.equals(progressKey) && !knowledgePoint.equals(item.getKnowledgePoint())) {
                continue;
            }
            if (progressPct >= 100) {
                item.setItemStatus("completed");
                itemMapper.updateById(item);
                activateNext(items, item);
            } else if (progressPct < 40) {
                item.setPriority(1);
                item.setFocusReason("进度偏低，已提升优先级并加强推送");
                itemMapper.updateById(item);
            }
            break;
        }
        pushService.pushForPath(path, listItems(path.getId()), "auto");
    }

    private void activateNext(List<LearningPathItem> items, LearningPathItem completed) {
        boolean found = false;
        for (LearningPathItem item : items) {
            if (found && "pending".equals(item.getItemStatus())) {
                item.setItemStatus("in_progress");
                itemMapper.updateById(item);
                return;
            }
            if (item.getId().equals(completed.getId())) {
                found = true;
            }
        }
    }

    /** 按已有学习进度初始化路径项状态，保证进度条与阶段步骤一致 */
    private void syncItemsWithProgress(List<LearningPathItem> items, List<StudentProgress> progressList) {
        if (CollectionUtils.isEmpty(items)) {
            return;
        }
        Map<String, Integer> progressByKp = progressList.stream()
                .collect(Collectors.toMap(
                        StudentProgress::getKnowledgePoint,
                        p -> p.getProgressPct() != null ? p.getProgressPct() : 0,
                        Math::max));
        boolean activated = false;
        for (LearningPathItem item : items) {
            String progressKey = item.getNodeId() != null
                    ? String.valueOf(item.getNodeId())
                    : item.getKnowledgePoint();
            int pct = progressByKp.getOrDefault(progressKey,
                    progressByKp.getOrDefault(item.getKnowledgePoint(), 0));
            String targetStatus;
            if (pct >= 100) {
                targetStatus = "completed";
            } else if (!activated) {
                targetStatus = "in_progress";
                activated = true;
            } else {
                targetStatus = "pending";
            }
            if (!targetStatus.equals(item.getItemStatus())) {
                item.setItemStatus(targetStatus);
                itemMapper.updateById(item);
            }
        }
    }

    private List<LearningPathItem> savePathItems(LearningPath path, JSONArray stages) {
        List<LearningPathItem> all = new ArrayList<>();
        int globalOrder = 0;
        for (int i = 0; i < stages.size(); i++) {
            JSONObject stage = stages.getJSONObject(i);
            int stageNo = stage.getIntValue("stageNo", i + 1);
            String stageName = stage.getString("stageName");
            JSONArray stageItems = stage.getJSONArray("items");
            if (stageItems == null) continue;
            for (int j = 0; j < stageItems.size(); j++) {
                JSONObject it = stageItems.getJSONObject(j);
                LearningPathItem item = new LearningPathItem();
                item.setPathId(path.getId());
                item.setStageNo(stageNo);
                item.setStageName(stageName != null ? stageName : "阶段" + stageNo);
                item.setKnowledgePoint(it.getString("knowledgePoint"));
                if (it.get("nodeId") != null) {
                    item.setNodeId(it.getLong("nodeId"));
                } else {
                    KnowledgeNode node = graphService.findByName(path.getSubject(), item.getKnowledgePoint());
                    if (node != null) {
                        item.setNodeId(node.getId());
                    }
                }
                item.setSortOrder(it.getIntValue("sortOrder", globalOrder++));
                item.setItemStatus("pending");
                item.setPriority(it.getIntValue("priority", 5));
                item.setFocusReason(it.getString("focusReason"));
                if (it.get("estimatedHours") != null) {
                    item.setEstimatedHours(it.getBigDecimal("estimatedHours"));
                }
                itemMapper.insert(item);
                all.add(item);
            }
        }
        all.sort((a, b) -> {
            int c = Integer.compare(a.getStageNo(), b.getStageNo());
            return c != 0 ? c : Integer.compare(a.getSortOrder(), b.getSortOrder());
        });
        return all;
    }

    private JSONObject buildPlanFromUnmastered(String subject, List<KnowledgeNode> unmasteredNodes) {
        JSONObject plan = new JSONObject();
        plan.put("pathName", subject + " · 待学知识点路径");
        plan.put("pathSummary", "根据画像评估，您还有 " + unmasteredNodes.size()
                + " 个知识点待学习，将按章节与前置顺序推送资源。");

        Map<Long, List<KnowledgeNode>> byChapterId = new LinkedHashMap<>();
        for (KnowledgeNode n : unmasteredNodes) {
            byChapterId.computeIfAbsent(n.getParentId(), k -> new ArrayList<>()).add(n);
        }

        JSONArray stages = new JSONArray();
        int stageNo = 1;
        for (KnowledgeNode chapter : graphService.listChapterNodes(subject)) {
            List<KnowledgeNode> chapterTopics = byChapterId.get(chapter.getId());
            if (chapterTopics == null || chapterTopics.isEmpty()) {
                continue;
            }
            JSONObject stage = new JSONObject();
            stage.put("stageNo", stageNo);
            stage.put("stageName", chapter.getNodeName());
            JSONArray items = new JSONArray();
            for (KnowledgeNode n : chapterTopics) {
                JSONObject it = new JSONObject();
                it.put("nodeId", n.getId());
                it.put("knowledgePoint", n.getNodeName());
                it.put("sortOrder", items.size() + 1);
                it.put("priority", 1);
                it.put("focusReason", "画像评估为待加强知识点，建议学习");
                it.put("estimatedHours", 2.0);
                items.add(it);
            }
            stage.put("items", items);
            stages.add(stage);
            stageNo++;
        }
        plan.put("stages", stages);
        return plan;
    }

    private JSONObject buildAllMasteredPlan(String subject) {
        JSONObject plan = new JSONObject();
        plan.put("pathName", subject + " · 已全部掌握");
        plan.put("pathSummary", "根据画像评估，您已掌握全部知识点，可前往资源中心拓展练习或通过对话与练习继续巩固。");
        JSONArray stages = new JSONArray();
        plan.put("stages", stages);
        return plan;
    }

    private void archiveActivePaths(Long studentId, String subject) {
        pathMapper.update(null, new LambdaUpdateWrapper<LearningPath>()
                .eq(LearningPath::getStudentId, studentId)
                .eq(LearningPath::getSubject, subject)
                .eq(LearningPath::getPathStatus, "active")
                .set(LearningPath::getPathStatus, "archived"));
    }

    private List<LearningPathItem> listItems(Long pathId) {
        return itemMapper.selectList(new LambdaQueryWrapper<LearningPathItem>()
                .eq(LearningPathItem::getPathId, pathId)
                .orderByAsc(LearningPathItem::getStageNo, LearningPathItem::getSortOrder));
    }

    private LearningPathDetailVO buildDetail(LearningPath path, List<LearningPathItem> items,
                                             List<ResourcePushRecord> pushes, List<StudentProgress> progress) {
        return LearningPathDetailVO.builder()
                .path(path)
                .items(items)
                .pushRecords(pushes)
                .progressList(progress)
                .pushedCount(pushes.size())
                .build();
    }
}
