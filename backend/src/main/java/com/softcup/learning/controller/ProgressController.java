package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.ProgressUpdateRequest;
import com.softcup.learning.entity.StudentProgress;
import com.softcup.learning.service.StudentProgressService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/progress")
@RequiredArgsConstructor
public class ProgressController {

    private final StudentProgressService progressService;

    @PutMapping("/update")
    public Result<StudentProgress> update(@Valid @RequestBody ProgressUpdateRequest request) {
        return Result.ok(progressService.updateProgress(request));
    }

    @GetMapping("/list")
    public Result<List<StudentProgress>> list(
            @RequestParam Long studentId,
            @RequestParam(required = false) String subject) {
        return Result.ok(progressService.listByStudent(studentId, subject));
    }
}
