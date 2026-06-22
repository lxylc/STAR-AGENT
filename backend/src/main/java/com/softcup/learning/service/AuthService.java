package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.dto.AuthResponse;
import com.softcup.learning.dto.LoginRequest;
import com.softcup.learning.dto.RegisterRequest;
import com.softcup.learning.dto.StudentSettingsRequest;
import com.softcup.learning.entity.Student;
import com.softcup.learning.mapper.StudentMapper;
import com.softcup.learning.util.JwtUtil;
import org.springframework.context.annotation.Lazy;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

@Service
public class AuthService {

    private final StudentMapper studentMapper;
    private final PasswordEncoder passwordEncoder;
    private final LearningProfileService learningProfileService;

    public AuthService(
            StudentMapper studentMapper,
            PasswordEncoder passwordEncoder,
            @Lazy LearningProfileService learningProfileService) {
        this.studentMapper = studentMapper;
        this.passwordEncoder = passwordEncoder;
        this.learningProfileService = learningProfileService;
    }

    public AuthResponse register(RegisterRequest req) {
        String username = req.getUsername().trim();
        if (studentMapper.selectCount(new LambdaQueryWrapper<Student>().eq(Student::getUsername, username)) > 0) {
            throw new BusinessException(400, "用户名已存在");
        }
        Student s = new Student();
        s.setUsername(username);
        s.setRealName(StringUtils.hasText(req.getRealName()) ? req.getRealName().trim() : username);
        s.setPasswordHash(passwordEncoder.encode(req.getPassword()));
        s.setRole("student");
        studentMapper.insert(s);
        return toAuthResponse(s, JwtUtil.createToken(s.getId(), s.getRole(), s.getUsername()));
    }

    public AuthResponse login(LoginRequest req) {
        Student s = studentMapper.selectOne(
                new LambdaQueryWrapper<Student>().eq(Student::getUsername, req.getUsername().trim()));
        if (s == null || s.getPasswordHash() == null || !passwordEncoder.matches(req.getPassword(), s.getPasswordHash())) {
            throw new BusinessException(401, "用户名或密码错误");
        }
        if (s.getEnabled() != null && s.getEnabled() == 0) {
            throw new BusinessException(403, "账号已被禁用，请联系管理员");
        }
        String expectedRole = StringUtils.hasText(req.getRole()) ? req.getRole().trim() : "student";
        if (!"student".equals(expectedRole) && !"admin".equals(expectedRole)) {
            throw new BusinessException(400, "角色无效");
        }
        if (!expectedRole.equals(s.getRole())) {
            throw new BusinessException(401, "身份选择错误，请重新选择");
        }
        return toAuthResponse(s, JwtUtil.createToken(s.getId(), s.getRole(), s.getUsername()));
    }

    public AuthResponse me(Long studentId) {
        Student s = studentMapper.selectById(studentId);
        if (s == null) {
            throw new BusinessException(404, "用户不存在");
        }
        return toAuthResponse(s, null);
    }

    public AuthResponse updateSettings(StudentSettingsRequest req) {
        Student s = applySettings(req);
        learningProfileService.syncBasicInfoFromStudent(s);
        return toAuthResponse(s, null);
    }

    public Student getStudentById(Long studentId) {
        Student s = studentMapper.selectById(studentId);
        if (s == null) {
            throw new BusinessException(404, "用户不存在");
        }
        return s;
    }

    public AuthResponse adminUpdateSettings(Long targetId, StudentSettingsRequest req) {
        req.setStudentId(targetId);
        Student s = applySettings(req);
        learningProfileService.syncBasicInfoFromStudent(s);
        return toAuthResponse(s, null);
    }

    private Student applySettings(StudentSettingsRequest req) {
        Student s = studentMapper.selectById(req.getStudentId());
        if (s == null) {
            throw new BusinessException(404, "用户不存在");
        }
        if (StringUtils.hasText(req.getRealName())) {
            s.setRealName(req.getRealName().trim());
        }
        if (StringUtils.hasText(req.getGrade())) {
            s.setGrade(req.getGrade().trim());
        }
        if (StringUtils.hasText(req.getMajor())) {
            s.setMajor(req.getMajor().trim());
        }
        if (req.getLearnPreferences() != null) {
            s.setLearnPreferences(JSON.toJSONString(req.getLearnPreferences()));
        }
        studentMapper.updateById(s);
        return s;
    }

    public List<Student> listStudents(String keyword, String grade) {
        LambdaQueryWrapper<Student> q = new LambdaQueryWrapper<Student>()
                .eq(Student::getRole, "student")
                .orderByDesc(Student::getId);
        if (StringUtils.hasText(keyword)) {
            q.and(w -> w.like(Student::getUsername, keyword).or().like(Student::getRealName, keyword));
        }
        if (StringUtils.hasText(grade)) {
            q.eq(Student::getGrade, grade.trim());
        }
        return studentMapper.selectList(q);
    }

    public void resetPassword(Long studentId, String newPassword) {
        Student s = getStudentById(studentId);
        if (!"student".equals(s.getRole())) {
            throw new BusinessException(400, "仅支持重置学生密码");
        }
        String pwd = StringUtils.hasText(newPassword) ? newPassword.trim() : "123456";
        s.setPasswordHash(passwordEncoder.encode(pwd));
        studentMapper.updateById(s);
    }

    public void batchResetPassword(List<Long> studentIds, String newPassword) {
        if (studentIds == null || studentIds.isEmpty()) {
            throw new BusinessException(400, "请选择至少一名学生");
        }
        for (Long id : studentIds) {
            resetPassword(id, newPassword);
        }
    }

    public void setStudentEnabled(Long studentId, boolean enabled) {
        Student s = getStudentById(studentId);
        if (!"student".equals(s.getRole())) {
            throw new BusinessException(400, "仅支持操作学生账号");
        }
        s.setEnabled(enabled ? 1 : 0);
        studentMapper.updateById(s);
    }

    private AuthResponse toAuthResponse(Student s, String token) {
        return AuthResponse.builder()
                .studentId(s.getId())
                .username(s.getUsername())
                .realName(s.getRealName())
                .role(s.getRole())
                .token(token)
                .grade(s.getGrade())
                .major(s.getMajor())
                .learnPreferences(s.getLearnPreferences())
                .enabled(s.getEnabled() == null || s.getEnabled() != 0)
                .build();
    }
}
