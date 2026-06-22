package com.softcup.learning.agent;

import com.softcup.learning.util.xfyun.XfSparkClient;
import org.springframework.stereotype.Component;

/**
 * 课件编辑智能体：整合讲义与习题要点，输出结构化课件文本
 */
@Component
public class CoursewareAgent extends AbstractSparkAgent {

    public CoursewareAgent(XfSparkClient sparkClient) {
        super(sparkClient);
    }

    @Override
    public AgentType agentType() {
        return AgentType.COURSEWARE;
    }

    @Override
    public AgentResult execute(AgentContext context) {
        String profile = buildProfileBrief(context);
        String lecture = context.getLectureContent() != null ? context.getLectureContent() : "（暂无讲义，请根据知识点自行组织）";

        String content = chat(
                "你是教学课件编排专家，输出适合课堂或自学的结构化课件Markdown。",
                """
                        学科：%s，知识点：%s
                        学生画像：%s
                        已有讲义与考点：
                        %s
                        请生成课件，必须包含以下章节（按顺序）：
                        1. 学习目标（3-5条）
                        2. 知识脉络（文字描述）
                        3. 分节讲解（3-5节，用 ## / ### 标题）
                        4. **优秀代码案例**（必须包含，供学生观看学习，不是练习题）：
                           - ### 推荐理由：结合学生薄弱点说明为何推荐此案例
                           - ### 应用场景：案例解决什么问题
                           - ### 优秀实现：给出完整、规范、带注释思路的 ```python 参考代码（非 pass 模板）
                           - ### 代码要点：3-5 条写法亮点
                           - ### 运行效果参考：示例输入输出
                        5. 课堂小结
                        语言精炼，直接输出Markdown，不要用```包裹全文，不要输出空标题行。
                        """.formatted(context.getSubject(), context.getKnowledgePoint(), profile,
                        truncate(lecture, 3500)));

        return AgentResult.builder()
                .resourceType(ResourceType.COURSEWARE)
                .title(context.getSubject() + " - " + context.getKnowledgePoint() + " 教学课件")
                .content(content)
                .build();
    }

    private String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }
}
