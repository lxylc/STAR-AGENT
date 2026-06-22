package com.softcup.learning.util.xfyun;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.softcup.learning.config.XfyunProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 讯飞星火大模型 WebSocket 统一客户端。
 * 接口: wss://spark-api.xf-yun.com/v3.5/chat (domain=generalv3.5)
 * 支持: 同步对话、超时重试、错误码解析
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class XfSparkClient {

    private final XfyunProperties properties;

    /**
     * 同步调用星火对话（非流式聚合返回全文）。
     *
     * @param messages 对话历史，含 system/user/assistant
     * @return 模型完整回复文本
     */
    public String chat(List<SparkMessage> messages) {
        validateConfig();
        int retries = Math.max(0, properties.getSpark().getMaxRetries());
        Exception last = null;
        for (int i = 0; i <= retries; i++) {
            try {
                return doChatOnce(messages);
            } catch (XfSparkException e) {
                if (XfErrorCodes.isNonRetryable(e.getXfCode())) {
                    throw e;
                }
                last = e;
                log.warn("星火调用失败，第{}次重试: {}", i + 1, e.getMessage());
            } catch (Exception e) {
                last = e;
                log.warn("星火调用失败，第{}次重试: {}", i + 1, e.getMessage());
                try {
                    Thread.sleep(500L * (i + 1));
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new XfSparkException("调用被中断");
                }
            }
        }
        throw new XfSparkException("星火大模型调用失败: " + (last != null ? last.getMessage() : "unknown"));
    }

    private String doChatOnce(List<SparkMessage> messages) throws Exception {
        String authUrl = XfAuthUtil.buildAuthUrl(
                properties.getSpark().getHostUrl(),
                properties.getApiKey(),
                properties.getApiSecret());

        OkHttpClient client = new OkHttpClient.Builder()
                .connectTimeout(properties.getSpark().getConnectTimeoutMs(), TimeUnit.MILLISECONDS)
                .readTimeout(properties.getSpark().getReadTimeoutMs(), TimeUnit.MILLISECONDS)
                .build();

        JSONObject requestJson = buildRequest(messages);
        StringBuilder answer = new StringBuilder();
        AtomicReference<Integer> xfCode = new AtomicReference<>();
        AtomicReference<String> xfMsg = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);

        Request request = new Request.Builder().url(authUrl).build();
        WebSocketListener listener = new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                log.debug("星火 WebSocket 已连接");
                webSocket.send(requestJson.toJSONString());
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                JSONObject resp = JSON.parseObject(text);
                JSONObject header = resp.getJSONObject("header");
                if (header != null) {
                    int code = header.getIntValue("code");
                    if (code != 0) {
                        xfCode.set(code);
                        xfMsg.set(header.getString("message"));
                        log.error("星火返回错误 code={}, message={}", code, header.getString("message"));
                        webSocket.close(1000, "error");
                        latch.countDown();
                        return;
                    }
                }
                JSONObject payload = resp.getJSONObject("payload");
                if (payload != null) {
                    JSONObject choices = payload.getJSONObject("choices");
                    if (choices != null) {
                        JSONArray textArr = choices.getJSONArray("text");
                        if (textArr != null) {
                            for (int i = 0; i < textArr.size(); i++) {
                                JSONObject item = textArr.getJSONObject(i);
                                if (item != null && item.containsKey("content")) {
                                    answer.append(item.getString("content"));
                                }
                            }
                        }
                        int status = choices.getIntValue("status");
                        if (status == 2) {
                            webSocket.close(1000, "done");
                            latch.countDown();
                        }
                    }
                }
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                log.error("星火 WebSocket 失败", t);
                xfMsg.set(t.getMessage());
                latch.countDown();
            }

            @Override
            public void onClosed(WebSocket webSocket, int code, String reason) {
                latch.countDown();
            }
        };

        client.newWebSocket(request, listener);
        boolean finished = latch.await(properties.getSpark().getReadTimeoutMs(), TimeUnit.MILLISECONDS);
        if (!finished) {
            throw new XfSparkException("星火对话超时");
        }
        if (xfCode.get() != null) {
            String friendly = XfErrorCodes.friendlyMessage(
                    xfCode.get(), xfMsg.get(), properties.getSpark().getDomain());
            throw new XfSparkException(xfCode.get(), friendly);
        }
        if (!StringUtils.hasText(answer)) {
            throw new XfSparkException("星火返回内容为空，请检查 APISecret 与套餐额度");
        }
        return answer.toString();
    }

    private JSONObject buildRequest(List<SparkMessage> messages) {
        JSONArray text = new JSONArray();
        for (SparkMessage m : messages) {
            JSONObject item = new JSONObject();
            item.put("role", m.getRole());
            item.put("content", m.getContent());
            text.add(item);
        }

        JSONObject message = new JSONObject();
        message.put("text", text);

        JSONObject chat = new JSONObject();
        chat.put("domain", properties.getSpark().getDomain());
        chat.put("temperature", properties.getSpark().getTemperature());
        chat.put("max_tokens", properties.getSpark().getMaxTokens());

        JSONObject parameter = new JSONObject();
        parameter.put("chat", chat);

        JSONObject header = new JSONObject();
        header.put("app_id", properties.getAppId());
        header.put("uid", "learning-agent");

        JSONObject payload = new JSONObject();
        payload.put("message", message);

        JSONObject root = new JSONObject();
        root.put("header", header);
        root.put("parameter", parameter);
        root.put("payload", payload);
        return root;
    }

    private void validateConfig() {
        if (!StringUtils.hasText(properties.getAppId())
                || !StringUtils.hasText(properties.getApiKey())
                || !StringUtils.hasText(properties.getApiSecret())
                || "YOUR_API_SECRET_HERE".equals(properties.getApiSecret())) {
            throw new XfSparkException("请配置讯飞 APISecret：application.yml 的 xfyun.api-secret 或环境变量 XFYUN_API_SECRET");
        }
    }
}
