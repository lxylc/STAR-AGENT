package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.AgentTaskVO;
import com.softcup.learning.dto.ResourceGenerateRequest;
import com.softcup.learning.entity.AgentTask;
import com.softcup.learning.entity.LearningResource;
import com.softcup.learning.service.AgentSchedulerService;
import com.softcup.learning.service.LearningResourceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 模块2：学习资源生成与查询
 */
@RestController
@RequestMapping("/api/resource")
@RequiredArgsConstructor
public class ResourceController {

    private final AgentSchedulerService schedulerService;
    private final LearningResourceService resourceService;

    /** 触发多智能体生成（单个或批量） */
    @PostMapping("/generate")
    public Result<AgentTaskVO> generate(@Valid @RequestBody ResourceGenerateRequest request) {
        return Result.ok(schedulerService.generate(request));
    }

    @GetMapping("/list")
    public Result<List<LearningResource>> list(
            @RequestParam Long studentId,
            @RequestParam(required = false) String subject,
            @RequestParam(required = false) String resourceType,
            @RequestParam(required = false) String knowledgePoint) {
        return Result.ok(resourceService.list(studentId, subject, resourceType, knowledgePoint));
    }

    @GetMapping("/{id}")
    public Result<LearningResource> detail(@PathVariable Long id) {
        return Result.ok(resourceService.getById(id));
    }

    @GetMapping("/task/{taskId}")
    public Result<AgentTaskVO> taskDetail(@PathVariable Long taskId) {
        return Result.ok(schedulerService.getTaskDetail(taskId));
    }

    @GetMapping("/tasks")
    public Result<List<AgentTask>> tasks(@RequestParam Long studentId) {
        return Result.ok(schedulerService.listTasks(studentId));
    }
}
