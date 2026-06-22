package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.BehaviorTrackRequest;
import com.softcup.learning.service.BehaviorEventService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/behavior")
@RequiredArgsConstructor
public class BehaviorController {

    private final BehaviorEventService behaviorEventService;

    @PostMapping("/track")
    public Result<Void> track(@Valid @RequestBody BehaviorTrackRequest request) {
        behaviorEventService.track(request);
        return Result.ok(null);
    }
}
