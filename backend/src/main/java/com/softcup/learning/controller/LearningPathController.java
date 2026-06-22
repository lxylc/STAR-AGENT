package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.ApplyEvaluationRequest;
import com.softcup.learning.dto.LearningPathDetailVO;
import com.softcup.learning.dto.PathPlanRequest;
import com.softcup.learning.dto.ProfilePathSyncRequest;
import com.softcup.learning.entity.ResourcePushRecord;
import com.softcup.learning.service.LearningPathService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/path")
@RequiredArgsConstructor
public class LearningPathController {

    private final LearningPathService pathService;

    @PostMapping("/plan")
    public Result<LearningPathDetailVO> plan(@Valid @RequestBody PathPlanRequest request) {
        return Result.ok(pathService.planPath(request));
    }

    @PostMapping("/replan/{pathId}")
    public Result<LearningPathDetailVO> replan(@PathVariable Long pathId) {
        return Result.ok(pathService.replan(pathId));
    }

    @GetMapping("/active")
    public Result<LearningPathDetailVO> active(
            @RequestParam Long studentId,
            @RequestParam String subject) {
        return Result.ok(pathService.getActivePath(studentId, subject));
    }

    @GetMapping("/{pathId}")
    public Result<LearningPathDetailVO> detail(@PathVariable Long pathId) {
        return Result.ok(pathService.getPathDetail(pathId));
    }

    @PostMapping("/{pathId}/refresh-push")
    public Result<List<ResourcePushRecord>> refreshPush(@PathVariable Long pathId) {
        return Result.ok(pathService.refreshPush(pathId));
    }

    @PostMapping("/apply-evaluation")
    public Result<LearningPathDetailVO> applyEvaluation(@Valid @RequestBody ApplyEvaluationRequest request) {
        return Result.ok(pathService.applyEvaluationAdjustments(request));
    }

    @PostMapping("/sync-from-profile")
    public Result<LearningPathDetailVO> syncFromProfile(@Valid @RequestBody ProfilePathSyncRequest request) {
        return Result.ok(pathService.syncFromProfile(request));
    }
}
