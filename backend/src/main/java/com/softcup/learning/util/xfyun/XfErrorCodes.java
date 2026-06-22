package com.softcup.learning.util.xfyun;

/**
 * 讯飞星火常见错误码说明。
 * 文档: https://www.xfyun.cn/doc/spark/%E6%8E%A5%E5%8F%A3%E8%AF%B4%E6%98%8E.html
 */
public final class XfErrorCodes {

    private XfErrorCodes() {
    }

    public static String friendlyMessage(Integer code, String rawMessage, String domain) {
        if (code == null) {
            return rawMessage;
        }
        return switch (code) {
            case 11200 -> "AppIdNoAuthError：当前 AppId 未开通【" + domain + "】模型权限。"
                    + "请到讯飞开放平台控制台 → 该应用 → 添加「星火认知大模型」服务并领取对应版本免费额度；"
                    + "或将 application.yml 中 xfyun.spark 改为已开通版本（推荐先试 Lite：host-url=v1.1/chat, domain=lite）";
            case 11201 -> "日调用量超限(11201)，请明日再试或升级套餐";
            case 11202, 11203 -> "并发超限(" + code + ")，请降低并发或升级套餐";
            case 10404 -> "host-url 与 domain 不匹配(10404)，请检查配置是否成对";
            case 10013 -> "鉴权失败(10013)，请核对 APIKey、APISecret 是否与 AppId 属于同一应用";
            default -> "讯飞错误[" + code + "]: " + rawMessage;
        };
    }

    /** 授权类错误重试无效 */
    public static boolean isNonRetryable(Integer code) {
        if (code == null) {
            return false;
        }
        return code == 11200 || code == 10013 || code == 10404 || code == 10015 || code == 10016;
    }
}
