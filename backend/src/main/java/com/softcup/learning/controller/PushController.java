package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.entity.LearningResource;
import com.softcup.learning.entity.ResourcePushRecord;
import com.softcup.learning.mapper.LearningResourceMapper;
import com.softcup.learning.service.ResourcePushService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/push")
@RequiredArgsConstructor
public class PushController {

    private final ResourcePushService pushService;
    private final LearningResourceMapper resourceMapper;

    @GetMapping("/list")
    public Result<List<Map<String, Object>>> list(
            @RequestParam Long studentId,
            @RequestParam(required = false) String readStatus) {
        List<ResourcePushRecord> records = pushService.listByStudent(studentId, readStatus);
        List<Map<String, Object>> vo = new ArrayList<>();
        for (ResourcePushRecord r : records) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("push", r);
            LearningResource res = resourceMapper.selectById(r.getResourceId());
            m.put("resource", res);
            vo.add(m);
        }
        return Result.ok(vo);
    }

    @PutMapping("/{id}/read")
    public Result<Void> markRead(@PathVariable Long id) {
        pushService.markRead(id);
        return Result.ok(null);
    }
}
