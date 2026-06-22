package com.softcup.learning.util.xfyun;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Base64;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * 讯飞 WebSocket 接口鉴权工具。
 * 文档: https://www.xfyun.cn/doc/spark/Web.html 第2节 接口鉴权
 */
public final class XfAuthUtil {

    private XfAuthUtil() {
    }

    /**
     * 将 wss 地址转换为带鉴权参数的完整 WebSocket URL。
     *
     * @param hostUrl   如 wss://spark-api.xf-yun.com/v3.5/chat
     * @param apiKey    控制台 APIKey
     * @param apiSecret 控制台 APISecret
     */
    public static String buildAuthUrl(String hostUrl, String apiKey, String apiSecret) throws Exception {
        URI uri = URI.create(hostUrl);
        String host = uri.getHost();
        String path = uri.getPath();
        if (path == null || path.isEmpty()) {
            path = "/";
        }

        SimpleDateFormat sdf = new SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.US);
        sdf.setTimeZone(TimeZone.getTimeZone("GMT"));
        String date = sdf.format(new Date());

        String signatureOrigin = "host: " + host + "\n"
                + "date: " + date + "\n"
                + "GET " + path + " HTTP/1.1";

        Mac mac = Mac.getInstance("hmacsha256");
        SecretKeySpec spec = new SecretKeySpec(apiSecret.getBytes(StandardCharsets.UTF_8), "hmacsha256");
        mac.init(spec);
        byte[] signatureSha = mac.doFinal(signatureOrigin.getBytes(StandardCharsets.UTF_8));
        String signature = Base64.getEncoder().encodeToString(signatureSha);

        String authorizationOrigin = String.format(
                "api_key=\"%s\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"%s\"",
                apiKey, signature);
        String authorization = Base64.getEncoder().encodeToString(authorizationOrigin.getBytes(StandardCharsets.UTF_8));

        String query = "authorization=" + URLEncoder.encode(authorization, StandardCharsets.UTF_8)
                + "&date=" + URLEncoder.encode(date, StandardCharsets.UTF_8)
                + "&host=" + URLEncoder.encode(host, StandardCharsets.UTF_8);

        return hostUrl + "?" + query;
    }
}
