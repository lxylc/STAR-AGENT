package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.dto.ProfileDetailVO;
import com.softcup.learning.dto.ProfileUpdateRequest;
import com.softcup.learning.entity.LearningProfile;
import com.softcup.learning.service.LearningProfileService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 模块1：学习画像 CRUD
 */
@RestController
@RequestMapping("/api/profile")
@RequiredArgsConstructor
public class LearningProfileController {

    private final LearningProfileService profileService;

    @GetMapping("/{studentId}")
    public Result<ProfileDetailVO> get(@PathVariable Long studentId, HttpServletRequest http) {
        assertProfileAccess(http, studentId);
        return Result.ok(profileService.getDetailByStudentId(studentId));
    }

    @PutMapping
    public Result<LearningProfile> update(
            @Valid @RequestBody ProfileUpdateRequest request,
            HttpServletRequest http) {
        String role = (String) http.getAttribute("userRole");
        if (!"admin".equals(role)) {
            throw new BusinessException(403, "学情数据仅管理员可修改");
        }
        return Result.ok(profileService.update(request));
    }

    private void assertProfileAccess(HttpServletRequest http, Long studentId) {
        Long userId = (Long) http.getAttribute("userId");
        String role = (String) http.getAttribute("userRole");
        if (!studentId.equals(userId) && !"admin".equals(role)) {
            throw new BusinessException(403, "无权查看该学生画像");
        }
    }
}
