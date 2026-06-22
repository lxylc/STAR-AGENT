package com.softcup.learning.controller;

import com.softcup.learning.common.Result;
import com.softcup.learning.config.XfyunProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 讯飞配置自检（不调用大模型，仅检查本地配置是否齐全、版本说明）。
 */
@RestController
@RequestMapping("/api/xfyun")
@RequiredArgsConstructor
public class XfyunConfigController {

    private final XfyunProperties properties;

    @GetMapping("/config-check")
    public Result<Map<String, Object>> configCheck() {
        Map<String, Object> info = new LinkedHashMap<>();
        boolean secretOk = StringUtils.hasText(properties.getApiSecret())
                && !"YOUR_API_SECRET_HERE".equals(properties.getApiSecret());
        info.put("appId", properties.getAppId());
        info.put("apiKeyConfigured", StringUtils.hasText(properties.getApiKey()));
        info.put("apiSecretConfigured", secretOk);
        info.put("hostUrl", properties.getSpark().getHostUrl());
        info.put("domain", properties.getSpark().getDomain());
        info.put("versionHint", versionHint(properties.getSpark().getDomain()));
        info.put("if11200", "控制台为应用开通「星火认知大模型」并领取与 domain 一致的免费套餐");
        return Result.ok(info);
    }

    private static String versionHint(String domain) {
        return switch (domain) {
            case "lite" -> "Spark Lite → wss://spark-api.xf-yun.com/v1.1/chat";
            case "generalv3" -> "Spark Pro → wss://spark-api.xf-yun.com/v3.1/chat";
            case "generalv3.5" -> "Spark Max → wss://spark-api.xf-yun.com/v3.5/chat";
            default -> "请确保 domain 与 host-url 成对，参见讯飞 Web 文档";
        };
    }
}
