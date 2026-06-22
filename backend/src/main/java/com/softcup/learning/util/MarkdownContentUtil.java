package com.softcup.learning.util;

/**
 * 清洗 AI 生成的 Markdown 文本，去除无意义的包裹符号与空标题行。
 */
public final class MarkdownContentUtil {

    private MarkdownContentUtil() {
    }

    public static String sanitize(String raw) {
        if (raw == null || raw.isBlank()) {
            return raw;
        }
        String text = unwrapProseFences(raw.strip());

        // 仅含 # 的空标题行
        text = text.replaceAll("(?m)^#{1,6}\\s*$", "");

        // 「# # 标题」类重复井号
        text = text.replaceAll("(?m)^(#{1,6})\\s+(#\\s+)+", "$1 ");

        // 一级标题降为二级
        text = text.replaceAll("(?m)^# (?!#)", "## ");

        // 连续超过 3 个换行压缩
        text = text.replaceAll("\\n{4,}", "\n\n\n");

        return text.strip();
    }

    private static String unwrapProseFences(String text) {
        String out = text;

        if (out.matches("(?s)^```\\w*\\s*\\n.*```\\s*$")) {
            String lang = "";
            java.util.regex.Matcher m = java.util.regex.Pattern.compile("^```(\\w+)", java.util.regex.Pattern.MULTILINE)
                    .matcher(out);
            if (m.find()) {
                lang = m.group(1).toLowerCase();
            }
            String inner = out.replaceFirst("^```\\w*\\s*\\n", "").replaceFirst("\\n```\\s*$", "").strip();
            if (lang.isEmpty() || "markdown".equals(lang) || "md".equals(lang)) {
                if (looksLikeMarkdownProse(inner) && !looksLikeCode(inner) && !inner.contains("```")) {
                    out = inner;
                }
            }
        }

        out = out.replaceAll("(?is)```(?:markdown|md)\\s*\\n([\\s\\S]*?)```", "$1");

        out = out.replaceAll(
                "(?im)(^|\\R+)```[ \\t]*\\R+((?:[^`]|`(?!``))*?)\\R+```[ \\t]*(?=\\R+```(?:python|py|javascript|js|java|json)\\b)",
                "$1$2"
        );
        out = out.replaceAll(
                "(?im)(^|\\R+)```[ \\t]*\\R+((?:[^`]|`(?!``))*?)\\R+```[ \\t]*(?=\\R+## )",
                "$1$2"
        );

        out = out.replaceAll("(?m)(^|\\R{2,})```[ \\t]*\\R+(?=#{1,6}\\s)", "$1");

        if (out.startsWith("```") && out.matches("(?s).*(^|\\R)#{1,6}\\s+\\S.*")) {
            out = out.replaceFirst("^```\\w*\\s*\\R", "");
        }

        return out;
    }

    private static boolean looksLikeMarkdownProse(String text) {
        return text.matches("(?s).*(^|\\n)#{1,6}\\s+\\S.*")
                || text.contains("**")
                || text.matches("(?s).*(^|\\n)[-*]\\s+\\S.*")
                || text.matches("(?s).*(^|\\n)\\d+\\.\\s+\\S.*");
    }

    private static boolean looksLikeCode(String text) {
        return text.matches("(?s).*^\\s*(def |class |import |from |print\\(|if __name__|function |const |let |var |public |private ).*");
    }
}
