package com.softcup.learning.agent;

import com.softcup.learning.util.xfyun.XfSparkClient;
import org.springframework.stereotype.Component;

/**
 * 习题生成智能体：单选、多选、简答 + 答案解析
 */
@Component
public class ExerciseAgent extends AbstractSparkAgent {

    public ExerciseAgent(XfSparkClient sparkClient) {
        super(sparkClient);
    }

    @Override
    public AgentType agentType() {
        return AgentType.EXERCISE;
    }

    @Override
    public AgentResult execute(AgentContext context) {
        String profile = buildProfileBrief(context);
        String ref = context.getLectureContent() != null ? context.getLectureContent() : "无讲义参考";

        String json = chat(
                "你是高校命题专家。只输出合法JSON，不要markdown包裹。",
                """
                        为【%s】生成**专项巩固习题**（非综合模考），知识点「%s」。学生画像与薄弱点：%s
                        参考讲义摘要：%s
                        要求：题目必须针对画像中的薄弱点设计，共 4~6 题即可，不要凑数。
                        JSON格式：
                        {
                          "singleChoice":[
                            {"question":"题干","options":{"A":"具体选项A","B":"具体选项B","C":"具体选项C","D":"具体选项D"},"answer":"A","analysis":""}
                          ],
                          "multiChoice":[
                            {"question":"题干","options":{"A":"具体选项A","B":"具体选项B","C":"具体选项C","D":"具体选项D"},"answer":["A","C"],"analysis":""}
                          ],
                          "shortAnswer":[{"question":"","answer":"","analysis":""}]
                        }
                        选项必须是完整、互不相同的具体内容，禁止用 A/B/C/D 或「选项A」占位；answer 必须与题干逻辑一致且唯一正确。
                        singleChoice 2~3 题，multiChoice 0~1 题，shortAnswer 1~2 题；难度贴合薄弱点。
                        """.formatted(context.getSubject(), context.getKnowledgePoint(), profile,
                        truncate(ref, 2500)));

        String readable = chat(
                "将习题JSON整理为易读的Markdown练习册（含答案与解析）。直接输出Markdown，不要用```包裹全文。",
                json);

        return AgentResult.builder()
                .resourceType(ResourceType.EXERCISE)
                .title(context.getSubject() + " - " + context.getKnowledgePoint() + " 专项习题")
                .content(readable)
                .contentJson(cleanJson(json))
                .build();
    }

    private String cleanJson(String text) {
        if (text == null) return "{}";
        String t = text.trim();
        if (t.startsWith("```")) {
            t = t.replaceAll("^```json\\s*", "").replaceAll("^```\\s*", "").replaceAll("```\\s*$", "");
        }
        int s = t.indexOf('{');
        int e = t.lastIndexOf('}');
        return s >= 0 && e > s ? t.substring(s, e + 1) : t;
    }

    private String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }
}
