package com.softcup.learning.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "xfyun")
public class XfyunProperties {

    private String appId;
    private String apiKey;
    private String apiSecret;
    private Spark spark = new Spark();

    @Data
    public static class Spark {
        /** WebSocket 地址，如 wss://spark-api.xf-yun.com/v3.5/chat */
        private String hostUrl = "wss://spark-api.xf-yun.com/v1.1/chat";
        /** 模型 domain，与 hostUrl 版本对应：lite / generalv3 / generalv3.5 */
        private String domain = "lite";
        private Double temperature = 0.5;
        private Integer maxTokens = 4096;
        private Integer connectTimeoutMs = 15000;
        private Integer readTimeoutMs = 120000;
        private Integer maxRetries = 2;
    }
}
