package com.softcup.learning.util;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

public final class JwtUtil {

    private static final String SECRET = "learning-agent-jwt-secret-change-in-prod";
    private static final long EXPIRE_MS = 7L * 24 * 60 * 60 * 1000;

    private JwtUtil() {
    }

    public static String createToken(Long userId, String role, String username) {
        long exp = System.currentTimeMillis() + EXPIRE_MS;
        JSONObject payload = new JSONObject();
        payload.put("sub", userId);
        payload.put("role", role);
        payload.put("username", username);
        payload.put("exp", exp);
        String payloadB64 = base64Url(JSON.toJSONString(payload));
        String sig = sign(payloadB64);
        return payloadB64 + "." + sig;
    }

    public static JSONObject parseToken(String token) {
        if (token == null || token.isBlank()) {
            throw new IllegalArgumentException("未登录");
        }
        String t = token.startsWith("Bearer ") ? token.substring(7).trim() : token.trim();
        String[] parts = t.split("\\.");
        if (parts.length != 2) {
            throw new IllegalArgumentException("无效令牌");
        }
        if (!sign(parts[0]).equals(parts[1])) {
            throw new IllegalArgumentException("令牌签名校验失败");
        }
        JSONObject payload = JSON.parseObject(new String(base64UrlDecode(parts[0]), StandardCharsets.UTF_8));
        Long exp = payload.getLong("exp");
        if (exp == null || exp < System.currentTimeMillis()) {
            throw new IllegalArgumentException("登录已过期，请重新登录");
        }
        return payload;
    }

    private static String sign(String payloadB64) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            byte[] raw = mac.doFinal(payloadB64.getBytes(StandardCharsets.UTF_8));
            return base64Url(raw);
        } catch (Exception e) {
            throw new IllegalStateException("签名失败", e);
        }
    }

    private static String base64Url(String s) {
        return base64Url(s.getBytes(StandardCharsets.UTF_8));
    }

    private static String base64Url(byte[] bytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private static byte[] base64UrlDecode(String s) {
        return Base64.getUrlDecoder().decode(s);
    }
}
