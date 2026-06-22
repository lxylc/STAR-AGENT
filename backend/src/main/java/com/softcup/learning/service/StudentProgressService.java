package com.softcup.learning.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.dto.BehaviorTrackRequest;
import com.softcup.learning.dto.ProgressUpdateRequest;
import com.softcup.learning.entity.StudentProgress;
import com.softcup.learning.mapper.StudentProgressMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class StudentProgressService {

    private final StudentProgressMapper progressMapper;
    private final LearningPathService pathService;
    private final BehaviorEventService behaviorEventService;

    public StudentProgress updateProgress(ProgressUpdateRequest req) {
        StudentProgress p = progressMapper.selectOne(new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, req.getStudentId())
                .eq(StudentProgress::getSubject, req.getSubject())
                .eq(StudentProgress::getKnowledgePoint, req.getKnowledgePoint()));
        if (p == null) {
            p = new StudentProgress();
            p.setStudentId(req.getStudentId());
            p.setSubject(req.getSubject());
            p.setKnowledgePoint(req.getKnowledgePoint());
            p.setProgressPct(0);
            p.setStudyMinutes(0);
        }
        p.setProgressPct(req.getProgressPct());
        if (req.getMasteryLevel() != null) {
            p.setMasteryLevel(req.getMasteryLevel());
        } else {
            p.setMasteryLevel(calcMastery(req.getProgressPct()));
        }
        if (req.getStudyMinutes() != null) {
            p.setStudyMinutes(p.getStudyMinutes() + req.getStudyMinutes());
        }
        p.setLastStudyAt(LocalDateTime.now());
        if (p.getId() == null) {
            progressMapper.insert(p);
        } else {
            progressMapper.updateById(p);
        }
        pathService.adjustAfterProgress(req.getStudentId(), req.getSubject(), req.getKnowledgePoint(), req.getProgressPct());
        BehaviorTrackRequest track = new BehaviorTrackRequest();
        track.setStudentId(req.getStudentId());
        track.setEventType("progress_update");
        track.setEventSource("progress_api");
        track.setPayload(java.util.Map.of(
                "knowledgePoint", req.getKnowledgePoint(),
                "progressPct", req.getProgressPct()));
        behaviorEventService.track(track);
        return p;
    }

    public List<StudentProgress> listByStudent(Long studentId, String subject) {
        LambdaQueryWrapper<StudentProgress> q = new LambdaQueryWrapper<StudentProgress>()
                .eq(StudentProgress::getStudentId, studentId);
        if (subject != null && !subject.isBlank()) {
            q.eq(StudentProgress::getSubject, subject);
        }
        return progressMapper.selectList(q.orderByDesc(StudentProgress::getUpdatedAt));
    }

    private String calcMastery(int pct) {
        if (pct >= 85) return "excellent";
        if (pct >= 60) return "good";
        if (pct >= 30) return "normal";
        return "weak";
    }
}
