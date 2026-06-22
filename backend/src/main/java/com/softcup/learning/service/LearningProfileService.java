package com.softcup.learning.service;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.common.CourseConstants;
import com.softcup.learning.dto.ProfileDetailVO;
import com.softcup.learning.dto.ProfileUpdateRequest;
import com.softcup.learning.entity.LearningProfile;
import com.softcup.learning.entity.Student;
import com.softcup.learning.mapper.LearningProfileMapper;
import com.softcup.learning.mapper.StudentMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;

@Service
@RequiredArgsConstructor
public class LearningProfileService {

    private final LearningProfileMapper profileMapper;
    private final StudentMapper studentMapper;

    public LearningProfile getByStudentId(Long studentId) {
        return profileMapper.selectOne(new LambdaQueryWrapper<LearningProfile>()
                .eq(LearningProfile::getStudentId, studentId)
                .orderByDesc(LearningProfile::getVersion)
                .last("LIMIT 1"));
    }

    public ProfileDetailVO getDetailByStudentId(Long studentId) {
        Student student = studentMapper.selectById(studentId);
        if (student == null) {
            throw new BusinessException(404, "用户不存在");
        }
        LearningProfile profile = getByStudentId(studentId);
        return mergeStudentAndProfile(student, profile);
    }

    public ProfileDetailVO mergeStudentAndProfile(Student student, LearningProfile profile) {
        ProfileDetailVO vo = new ProfileDetailVO();
        vo.setStudentId(student.getId());
        vo.setRealName(student.getRealName());
        vo.setGrade(student.getGrade());
        vo.setMajor(student.getMajor());
        vo.setLearnPreferences(student.getLearnPreferences());
        if (profile != null) {
            vo.setId(profile.getId());
            vo.setMainSubject(profile.getMainSubject());
            vo.setKnowledgeBase(profile.getKnowledgeBase());
            vo.setWeakPoints(profile.getWeakPoints());
            vo.setMasteredPoints(profile.getMasteredPoints());
            vo.setDailyStudyHours(profile.getDailyStudyHours());
            vo.setLearnPreference(profile.getLearnPreference());
            vo.setLearnGoal(profile.getLearnGoal());
            vo.setBaseTags(profile.getBaseTags());
            vo.setMasteryTags(profile.getMasteryTags());
            vo.setStyleTags(profile.getStyleTags());
            vo.setGoalTags(profile.getGoalTags());
            vo.setBehaviorTags(profile.getBehaviorTags());
            vo.setProfileStatus(profile.getProfileStatus());
            vo.setVersion(profile.getVersion());
            vo.setUpdatedAt(profile.getUpdatedAt());
            if (!StringUtils.hasText(vo.getGrade())) {
                vo.setGrade(profile.getGrade());
            }
            if (!StringUtils.hasText(vo.getMajor())) {
                vo.setMajor(profile.getMajor());
            }
        } else {
            vo.setProfileStatus("draft");
            vo.setVersion(0);
        }
        return vo;
    }

    @Transactional(rollbackFor = Exception.class)
    public void syncBasicInfoFromStudent(Student student) {
        if (student == null) {
            return;
        }
        LearningProfile profile = getByStudentId(student.getId());
        if (profile == null) {
            return;
        }
        if (StringUtils.hasText(student.getGrade())) {
            profile.setGrade(student.getGrade().trim());
        }
        if (StringUtils.hasText(student.getMajor())) {
            profile.setMajor(student.getMajor().trim());
        }
        if (StringUtils.hasText(student.getLearnPreferences())) {
            profile.setLearnPreference(student.getLearnPreferences());
            profile.setStyleTags(student.getLearnPreferences());
        }
        profileMapper.updateById(profile);
    }

    public LearningProfile getOrCreateDraft(Long studentId) {
        LearningProfile existing = getByStudentId(studentId);
        if (existing != null) {
            return existing;
        }
        LearningProfile p = new LearningProfile();
        p.setStudentId(studentId);
        p.setProfileStatus("draft");
        p.setVersion(1);
        profileMapper.insert(p);
        return p;
    }

    public void markBuilding(Long profileId) {
        LearningProfile p = profileMapper.selectById(profileId);
        if (p != null && "draft".equals(p.getProfileStatus())) {
            p.setProfileStatus("building");
            profileMapper.updateById(p);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public LearningProfile applyExtractedProfile(LearningProfile profile, JSONObject obj, String rawJson) {
        ProfileExtractNormalizer.mergeExtracted(profile, obj);
        profile.setRawExtractJson(rawJson);
        profile.setProfileStatus("completed");
        profileMapper.updateById(profile);
        return profile;
    }

    @Transactional(rollbackFor = Exception.class)
    public LearningProfile update(ProfileUpdateRequest req) {
        LearningProfile p = profileMapper.selectById(req.getId());
        if (p == null) {
            throw new BusinessException("画像不存在");
        }
        if (req.getGrade() != null) p.setGrade(req.getGrade());
        if (req.getMajor() != null) p.setMajor(req.getMajor());
        if (req.getMainSubject() != null) p.setMainSubject(CourseConstants.SUBJECT);
        if (req.getKnowledgeBase() != null) p.setKnowledgeBase(req.getKnowledgeBase());
        if (req.getWeakPoints() != null) p.setWeakPoints(req.getWeakPoints());
        if (req.getDailyStudyHours() != null) p.setDailyStudyHours(req.getDailyStudyHours());
        if (req.getLearnPreference() != null) p.setLearnPreference(req.getLearnPreference());
        if (req.getLearnGoal() != null) p.setLearnGoal(req.getLearnGoal());
        if (req.getBaseTags() != null) p.setBaseTags(req.getBaseTags());
        if (req.getMasteryTags() != null) p.setMasteryTags(req.getMasteryTags());
        if (req.getStyleTags() != null) p.setStyleTags(req.getStyleTags());
        if (req.getGoalTags() != null) p.setGoalTags(req.getGoalTags());
        if (req.getBehaviorTags() != null) p.setBehaviorTags(req.getBehaviorTags());
        if (req.getMasteredPoints() != null) p.setMasteredPoints(req.getMasteredPoints());
        if (req.getProfileStatus() != null) p.setProfileStatus(req.getProfileStatus());
        p.setVersion(p.getVersion() + 1);
        profileMapper.updateById(p);
        return p;
    }

    @Transactional(rollbackFor = Exception.class)
    public LearningProfile saveProfileFields(LearningProfile profile) {
        int ver = profile.getVersion() != null ? profile.getVersion() : 1;
        profile.setVersion(ver + 1);
        profileMapper.updateById(profile);
        return profile;
    }

    @Transactional(rollbackFor = Exception.class)
    public LearningProfile updateDraftFields(LearningProfile profile) {
        profileMapper.updateById(profile);
        return profile;
    }

}
