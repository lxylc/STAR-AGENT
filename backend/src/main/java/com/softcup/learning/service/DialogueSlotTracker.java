package com.softcup.learning.service;

import com.softcup.learning.entity.LearningProfile;
import com.softcup.learning.entity.ProfileDialogue;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 从对话中增量识别已收集的画像字段，避免 AI 重复追问。
 */
public final class DialogueSlotTracker {

    private static final Pattern GRADE_PATTERN = Pattern.compile("大[一二三四]|研[一二三]|博士|已毕业");
    private static final Pattern HOURS_PATTERN = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*(?:小时|h|H|个小时)");

    private DialogueSlotTracker() {
    }

    public record Slot(String key, String label) {
    }

    private static final List<Slot> SLOTS = List.of(
            new Slot("grade", "年级"),
            new Slot("major", "专业"),
            new Slot("knowledgeBase", "Python 知识基础"),
            new Slot("dailyStudyHours", "每日学习时长"),
            new Slot("learnPreference", "学习偏好"),
            new Slot("learnGoal", "学习目标")
    );

    public static List<Slot> slots() {
        return SLOTS;
    }

    /** 根据问答对 + 全文扫描，增量写入 profile（不覆盖已有值） */
    public static void applyFromDialogue(LearningProfile profile, List<ProfileDialogue> history) {
        if (profile == null || history == null || history.isEmpty()) {
            return;
        }
        for (int i = 0; i < history.size() - 1; i++) {
            ProfileDialogue curr = history.get(i);
            ProfileDialogue next = history.get(i + 1);
            if ("assistant".equals(curr.getRole()) && "user".equals(next.getRole())) {
                applyAnswer(profile, curr.getContent(), next.getContent());
            }
        }
        for (ProfileDialogue d : history) {
            if ("user".equals(d.getRole())) {
                scanUserMessage(profile, d.getContent());
            }
        }
    }

    public static List<Slot> missingSlots(LearningProfile profile) {
        List<Slot> missing = new ArrayList<>();
        for (Slot slot : SLOTS) {
            if (!isFilled(profile, slot.key())) {
                missing.add(slot);
            }
        }
        return missing;
    }

    public static String buildCollectedSummary(LearningProfile profile) {
        StringBuilder sb = new StringBuilder();
        for (Slot slot : SLOTS) {
            String val = displayValue(profile, slot.key());
            sb.append("- ").append(slot.label()).append("：")
                    .append(StringUtils.hasText(val) ? val + " ✓" : "未收集")
                    .append("\n");
        }
        sb.append("- 知识点掌握度：由画像构建对话、练习与日常交流自动评估，无需手动勾选 ✓\n");
        return sb.toString();
    }

    public static String buildGuideSystemPrompt(LearningProfile profile) {
        List<Slot> missing = missingSlots(profile);
        StringBuilder sb = new StringBuilder("""
                你是《Python程序设计》课程的个性化学习画像采集助手。主修学科固定为 Python程序设计。
                规则（必须严格遵守）：
                1. 【已收集信息】中标记 ✓ 的项，严禁再次提问或换说法重问。
                2. 每次只问 1 个问题，且必须来自【待收集信息】列表的第一项。
                3. 不要问具体知识点掌握情况（系统会根据对话、练习与交流自动评估）。
                4. 待收集为空时，提示发送「完成画像」或「重新生成画像」，不要再问新问题。
                5. 回复简洁友好，1-3 句话即可。

                【已收集信息】
                """);
        sb.append(buildCollectedSummary(profile));
        if (missing.isEmpty()) {
            sb.append("\n【待收集信息】\n无。请直接提示：信息已齐全，请发送「完成画像」或「重新生成画像」生成/更新学习画像。\n");
        } else {
            sb.append("\n【待收集信息】（按顺序，本次只问第一项）\n");
            for (int i = 0; i < missing.size(); i++) {
                sb.append(i + 1).append(". ").append(missing.get(i).label());
                if (i == 0) sb.append(" ← 本次只问这个");
                sb.append("\n");
            }
        }
        return sb.toString();
    }

    /** 全部收集完毕时的固定回复，不再调用大模型 */
    public static String buildAllCollectedReply() {
        return "太好了，所需信息都已收集完毕！请发送「完成画像」生成学习画像；"
                + "若之后修改了回答，可发送「重新生成画像」按最新对话更新。"
                + "（知识点掌握度将在画像构建与练习过程中自动更新）";
    }

    /** 针对下一缺失项的兜底提问（大模型仍重复时使用） */
    public static String buildFallbackQuestion(Slot slot) {
        return switch (slot.key()) {
            case "grade" -> "请告诉我你目前读大几？";
            case "major" -> "你的专业是什么？";
            case "knowledgeBase" -> "你目前的 Python 基础怎么样？例如零基础、学过语法、做过项目等。";
            case "dailyStudyHours" -> "你每天大概能投入多少小时学习 Python？";
            case "learnPreference" -> "你更倾向于哪种学习方式：图文阅读、视频教程，还是刷题练习？（可多选）";
            case "learnGoal" -> "你的 Python 学习目标是什么？";
            default -> "请继续补充你的学习情况。";
        };
    }

    private static void applyAnswer(LearningProfile profile, String question, String answer) {
        if (!StringUtils.hasText(answer)) {
            return;
        }
        String q = question == null ? "" : question;
        String a = answer.trim();

        if (containsAny(q, "偏好", "书籍", "视频", "刷题", "学习方式", "方式学习")
                && !containsAny(q, "目标", "成为", "规划")) {
            fillPreference(profile, a);
        }
        if (containsAny(q, "目标", "想达到", "规划", "成为")) {
            fillIfEmpty(profile, "learnGoal", a);
        }
        if (containsAny(q, "年级", "大几", "专业")) {
            fillGradeMajor(profile, a);
        }
        if (containsAny(q, "基础", "水平", "接触过")) {
            fillIfEmpty(profile, "knowledgeBase", a);
        }
        if (containsAny(q, "小时", "时长", "投入", "每天")) {
            fillHours(profile, a);
        }
    }

    private static void scanUserMessage(LearningProfile profile, String content) {
        if (!StringUtils.hasText(content)) {
            return;
        }
        String text = content.trim();
        fillPreference(profile, text);
        fillHours(profile, text);
        if (GRADE_PATTERN.matcher(text).find() && !isFilled(profile, "grade")) {
            fillGradeMajor(profile, text);
        }
        if (containsAny(text, "专业") && text.length() < 30) {
            fillIfEmpty(profile, "major", text.replace("专业", "").replace("是", "").trim());
        }
        if (containsAny(text, "大师", "目标", "学会", "掌握", "找到工作", "考试", "项目")
                && text.length() >= 4 && text.length() <= 80) {
            if (!isFilled(profile, "learnGoal") && containsAny(text, "成为", "想", "希望", "目标")) {
                fillIfEmpty(profile, "learnGoal", text);
            }
        }
    }

    private static void fillGradeMajor(LearningProfile profile, String answer) {
        Matcher gm = GRADE_PATTERN.matcher(answer);
        if (gm.find()) {
            fillIfEmpty(profile, "grade", gm.group());
            String major = answer.substring(gm.end()).replace("，", " ").replace(",", " ")
                    .replace("、", " ").replace("专业", "").replace("是", "").trim();
            if (StringUtils.hasText(major) && major.length() <= 32) {
                fillIfEmpty(profile, "major", major);
            }
            return;
        }
        if (answer.length() <= 32) {
            fillIfEmpty(profile, "major", answer.replace("专业", "").replace("是", "").trim());
        }
    }

    private static void fillHours(LearningProfile profile, String text) {
        if (isFilled(profile, "dailyStudyHours")) {
            return;
        }
        Matcher m = HOURS_PATTERN.matcher(text);
        if (m.find()) {
            profile.setDailyStudyHours(new BigDecimal(m.group(1)));
        }
    }

    private static void fillPreference(LearningProfile profile, String text) {
        if (isFilled(profile, "learnPreference")) {
            return;
        }
        String pref = parsePreference(text);
        if (pref != null) {
            profile.setLearnPreference(pref);
        }
    }

    /** 从自然语言解析学习偏好枚举值 */
    public static String parsePreferenceFromText(String text) {
        return parsePreference(text);
    }

    private static String parsePreference(String text) {
        if (!StringUtils.hasText(text)) {
            return null;
        }
        boolean video = containsAny(text, "视频", "录像", "教程");
        boolean exercise = containsAny(text, "刷题", "练习", "习题", "做题");
        boolean textPref = containsAny(text, "图文", "书籍", "阅读", "文字");
        int count = (video ? 1 : 0) + (exercise ? 1 : 0) + (textPref ? 1 : 0);
        if (count >= 2) {
            return "mixed";
        }
        if (video) {
            return "video";
        }
        if (exercise) {
            return "exercise";
        }
        if (textPref) {
            return "text";
        }
        return null;
    }

    private static void fillIfEmpty(LearningProfile profile, String key, String value) {
        if (!StringUtils.hasText(value) || isFilled(profile, key)) {
            return;
        }
        switch (key) {
            case "grade" -> profile.setGrade(value);
            case "major" -> profile.setMajor(value);
            case "knowledgeBase" -> profile.setKnowledgeBase(value);
            case "learnGoal" -> profile.setLearnGoal(value);
            default -> { }
        }
    }

    private static boolean isFilled(LearningProfile profile, String key) {
        return StringUtils.hasText(displayValue(profile, key));
    }

    private static String displayValue(LearningProfile profile, String key) {
        if (profile == null) {
            return null;
        }
        return switch (key) {
            case "grade" -> profile.getGrade();
            case "major" -> profile.getMajor();
            case "knowledgeBase" -> profile.getKnowledgeBase();
            case "dailyStudyHours" -> profile.getDailyStudyHours() != null
                    ? profile.getDailyStudyHours().stripTrailingZeros().toPlainString() + " 小时" : null;
            case "learnPreference" -> preferenceLabel(profile.getLearnPreference());
            case "learnGoal" -> profile.getLearnGoal();
            default -> null;
        };
    }

    private static String preferenceLabel(String pref) {
        if (!StringUtils.hasText(pref)) {
            return null;
        }
        return Map.of(
                "text", "图文",
                "video", "视频",
                "exercise", "刷题",
                "mixed", "视频+刷题/混合"
        ).getOrDefault(pref, pref);
    }

    private static boolean containsAny(String text, String... keywords) {
        if (!StringUtils.hasText(text)) {
            return false;
        }
        for (String k : keywords) {
            if (text.contains(k)) {
                return true;
            }
        }
        return false;
    }
}
