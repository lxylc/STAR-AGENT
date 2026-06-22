package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.softcup.learning.dto.BehaviorTrackRequest;
import com.softcup.learning.entity.LearningBehaviorEvent;
import com.softcup.learning.mapper.LearningBehaviorEventMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class BehaviorEventService {

    private final LearningBehaviorEventMapper eventMapper;

    public void track(BehaviorTrackRequest request) {
        String type = request.getEventType();
        if (!StringUtils.hasText(type)) {
            return;
        }
        LearningBehaviorEvent e = new LearningBehaviorEvent();
        e.setStudentId(request.getStudentId());
        e.setEventType(type);
        e.setEventSource(StringUtils.hasText(request.getEventSource()) ? request.getEventSource() : "java_api");
        if (request.getPayload() != null && !request.getPayload().isEmpty()) {
            e.setPayloadJson(JSON.toJSONString(request.getPayload()));
        }
        e.setCreatedAt(LocalDateTime.now());
        eventMapper.insert(e);
    }
}
