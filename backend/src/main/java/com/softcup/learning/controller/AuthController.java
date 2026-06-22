package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.AdminBatchResetRequest;
import com.softcup.learning.dto.AdminStatusRequest;
import com.softcup.learning.dto.AuthResponse;
import com.softcup.learning.dto.LoginRequest;
import com.softcup.learning.dto.RegisterRequest;
import com.softcup.learning.dto.StudentSettingsRequest;
import com.softcup.learning.entity.Student;
import com.softcup.learning.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public Result<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        return Result.ok(authService.register(request));
    }

    @PostMapping("/login")
    public Result<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        return Result.ok(authService.login(request));
    }

    @GetMapping("/me")
    public Result<AuthResponse> me(HttpServletRequest request) {
        Long id = (Long) request.getAttribute("userId");
        return Result.ok(authService.me(id));
    }

    @PutMapping("/settings")
    public Result<AuthResponse> settings(@RequestBody StudentSettingsRequest request, HttpServletRequest http) {
        if (request.getStudentId() == null) {
            request.setStudentId((Long) http.getAttribute("userId"));
        }
        return Result.ok(authService.updateSettings(request));
    }

    @GetMapping("/students")
    public Result<List<Student>> listStudents(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String grade,
            HttpServletRequest request) {
        String role = (String) request.getAttribute("userRole");
        if (!"admin".equals(role)) {
            return Result.fail(403, "无权限");
        }
        return Result.ok(authService.listStudents(keyword, grade));
    }

    @GetMapping("/students/{studentId}")
    public Result<AuthResponse> getStudent(
            @PathVariable Long studentId,
            HttpServletRequest request) {
        String role = (String) request.getAttribute("userRole");
        if (!"admin".equals(role)) {
            return Result.fail(403, "无权限");
        }
        Student s = authService.getStudentById(studentId);
        return Result.ok(AuthResponse.builder()
                .studentId(s.getId())
                .username(s.getUsername())
                .realName(s.getRealName())
                .role(s.getRole())
                .grade(s.getGrade())
                .major(s.getMajor())
                .learnPreferences(s.getLearnPreferences())
                .enabled(s.getEnabled() == null || s.getEnabled() != 0)
                .build());
    }

    @PutMapping("/students/{studentId}/settings")
    public Result<AuthResponse> adminUpdateSettings(
            @PathVariable Long studentId,
            @RequestBody StudentSettingsRequest request,
            HttpServletRequest http) {
        String role = (String) http.getAttribute("userRole");
        if (!"admin".equals(role)) {
            return Result.fail(403, "无权限");
        }
        return Result.ok(authService.adminUpdateSettings(studentId, request));
    }

    @PostMapping("/students/{studentId}/reset-password")
    public Result<Void> resetPassword(
            @PathVariable Long studentId,
            HttpServletRequest http) {
        String role = (String) http.getAttribute("userRole");
        if (!"admin".equals(role)) {
            return Result.fail(403, "无权限");
        }
        authService.resetPassword(studentId, null);
        return Result.ok(null);
    }

    @PostMapping("/students/batch-reset-password")
    public Result<Void> batchResetPassword(
            @RequestBody AdminBatchResetRequest request,
            HttpServletRequest http) {
        String role = (String) http.getAttribute("userRole");
        if (!"admin".equals(role)) {
            return Result.fail(403, "无权限");
        }
        authService.batchResetPassword(request.getStudentIds(), request.getNewPassword());
        return Result.ok(null);
    }

    @PutMapping("/students/{studentId}/status")
    public Result<AuthResponse> setStudentStatus(
            @PathVariable Long studentId,
            @RequestBody AdminStatusRequest request,
            HttpServletRequest http) {
        String role = (String) http.getAttribute("userRole");
        if (!"admin".equals(role)) {
            return Result.fail(403, "无权限");
        }
        if (request.getEnabled() == null) {
            return Result.fail(400, "缺少 enabled 参数");
        }
        authService.setStudentEnabled(studentId, request.getEnabled());
        Student s = authService.getStudentById(studentId);
        return Result.ok(AuthResponse.builder()
                .studentId(s.getId())
                .username(s.getUsername())
                .realName(s.getRealName())
                .role(s.getRole())
                .grade(s.getGrade())
                .major(s.getMajor())
                .enabled(s.getEnabled() == null || s.getEnabled() != 0)
                .build());
    }
}
