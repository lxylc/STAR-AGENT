package com.softcup.learning.agent;

import com.softcup.learning.util.MarkdownContentUtil;
import com.softcup.learning.util.xfyun.XfSparkClient;
import org.springframework.stereotype.Component;

/**
 * 知识点梳理智能体：生成讲义 + 考点总结（两次星火调用）
 */
@Component
public class LectureAgent extends AbstractSparkAgent {

    public LectureAgent(XfSparkClient sparkClient) {
        super(sparkClient);
    }

    @Override
    public AgentType agentType() {
        return AgentType.LECTURE;
    }

    @Override
    public AgentResult execute(AgentContext context) {
        String profile = buildProfileBrief(context);
        String kp = context.getKnowledgePoint();
        String subject = context.getSubject();

        String lecture = chat(
                "你是高校学科知识点梳理专家，输出结构清晰、适合大学生阅读的Markdown讲义。",
                """
                        请为【%s】学科的知识点「%s」生成详细讲义。
                        学生画像：%s
                        要求：含定义、核心概念、公式/定理（如适用）、典型例题思路、易错点；篇幅800-1500字。
                        格式要求：直接输出Markdown正文，不要用```代码块包裹全文；标题从二级(##)开始，不要输出空标题行。
                        """.formatted(subject, kp, profile));

        String summary = chat(
                "你是考试辅导专家，擅长提炼考点。",
                """
                        基于以下讲义内容，为「%s」提炼考点总结（条目化，8-15条，含考频提示）：
                        %s
                        """.formatted(kp, truncate(lecture, 3000)));

        String fullContent = "## 知识点讲义\n\n" + lecture + "\n\n## 考点总结\n\n" + summary;

        return AgentResult.builder()
                .resourceType(ResourceType.LECTURE)
                .title(subject + " - " + kp + " 讲义与考点")
                .content(fullContent)
                .build();
    }

    private String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }
}
