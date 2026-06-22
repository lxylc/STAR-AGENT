package com.softcup.learning.controller;

import com.softcup.learning.common.BusinessException;
import com.softcup.learning.common.Result;
import com.softcup.learning.dto.ProfileDetailVO;
import com.softcup.learning.service.LearningProfileService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 公开演示接口：仅开放固定演示学生，供报告/答辩分享链接只读查看画像。
 */
@RestController
@RequestMapping("/api/public/demo")
@RequiredArgsConstructor
public class PublicDemoController {

    private static final long DEMO_STUDENT_ID = 1L;

    private final LearningProfileService profileService;

    @GetMapping("/profile/{studentId}")
    public Result<ProfileDetailVO> getProfile(@PathVariable Long studentId) {
        assertDemoStudent(studentId);
        return Result.ok(profileService.getDetailByStudentId(studentId));
    }

    private void assertDemoStudent(Long studentId) {
        if (!Long.valueOf(DEMO_STUDENT_ID).equals(studentId)) {
            throw new BusinessException(403, "仅开放演示账号");
        }
    }
}
