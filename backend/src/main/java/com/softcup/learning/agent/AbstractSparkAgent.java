package com.softcup.learning.agent;

import com.alibaba.fastjson2.JSON;
import com.softcup.learning.entity.LearningProfile;
import com.softcup.learning.util.xfyun.SparkMessage;
import com.softcup.learning.util.xfyun.XfSparkClient;

import java.util.ArrayList;
import java.util.List;

public abstract class AbstractSparkAgent implements LearningAgent {

    protected final XfSparkClient sparkClient;

    protected AbstractSparkAgent(XfSparkClient sparkClient) {
        this.sparkClient = sparkClient;
    }

    protected String chat(String systemPrompt, String userPrompt) {
        List<SparkMessage> messages = new ArrayList<>();
        messages.add(new SparkMessage("system", systemPrompt));
        messages.add(new SparkMessage("user", userPrompt));
        return sparkClient.chat(messages);
    }

    protected String buildProfileBrief(AgentContext ctx) {
        LearningProfile p = ctx.getProfile();
        if (p == null) {
            return "暂无学习画像，按通用高校学生水平生成。";
        }
        return """
                年级:%s，专业:%s，主修:%s，知识基础:%s，薄弱点:%s，学习偏好:%s，目标:%s，掌握度标签:%s，风格标签:%s
                """.formatted(
                nullToEmpty(p.getGrade()),
                nullToEmpty(p.getMajor()),
                nullToEmpty(p.getMainSubject()),
                nullToEmpty(p.getKnowledgeBase()),
                nullToEmpty(p.getWeakPoints()),
                nullToEmpty(p.getLearnPreference()),
                nullToEmpty(p.getLearnGoal()),
                nullToEmpty(p.getMasteryTags()),
                nullToEmpty(p.getStyleTags()));
    }

    protected String buildProfileTagsJson(AgentContext ctx) {
        LearningProfile p = ctx.getProfile();
        if (p == null) {
            return "{}";
        }
        return JSON.toJSONString(p);
    }

    private String nullToEmpty(String s) {
        return s == null ? "" : s;
    }
}
