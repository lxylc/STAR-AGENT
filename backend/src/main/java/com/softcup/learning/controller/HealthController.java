package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {

    @GetMapping("/api/health")
    public Result<Map<String, String>> health() {
        return Result.ok(Map.of("status", "UP", "module", "learning-agent"));
    }
}
