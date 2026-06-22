package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.dto.DialogueSendRequest;
import com.softcup.learning.dto.DialogueSendResponse;
import com.softcup.learning.entity.LearningProfile;
import com.softcup.learning.entity.ProfileDialogue;
import com.softcup.learning.service.ProfileDialogueService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 模块1：对话式学习画像构建
 */
@RestController
@RequestMapping("/api/profile/dialogue")
@RequiredArgsConstructor
public class ProfileDialogueController {

    private final ProfileDialogueService dialogueService;

    /** 初始化引导会话（首次进入对话页） */
    @PostMapping("/init/{studentId}")
    public Result<String> init(@PathVariable Long studentId) {
        return Result.ok(dialogueService.initSession(studentId));
    }

    /** 发送对话消息（引导采集 / 触发画像完成） */
    @PostMapping("/send")
    public Result<DialogueSendResponse> send(@Valid @RequestBody DialogueSendRequest request) {
        return Result.ok(dialogueService.send(request));
    }

    /** 对话历史 */
    @GetMapping("/history/{studentId}")
    public Result<List<ProfileDialogue>> history(@PathVariable Long studentId) {
        return Result.ok(dialogueService.listHistory(studentId));
    }

    /** 手动触发 AI 抽取画像 */
    @PostMapping("/extract/{studentId}")
    public Result<LearningProfile> extract(@PathVariable Long studentId) {
        return Result.ok(dialogueService.forceExtract(studentId));
    }
}
