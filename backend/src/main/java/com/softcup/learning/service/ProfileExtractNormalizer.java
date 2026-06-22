package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.softcup.learning.common.CourseConstants;
import com.softcup.learning.entity.LearningProfile;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * 将大模型抽取结果与对话增量草稿合并，并规范化标签与偏好字段。
 */
public final class ProfileExtractNormalizer {

    private static final Set<String> VALID_PREFERENCES = Set.of("text", "video", "exercise", "mixed");

    private static final Set<String> PLACEHOLDER_TAG_WORDS = Set.of(
            "标签", "薄弱知识点", "学生基础标签", "学习风格", "学习目标标签", "学习行为标签"
    );

    private ProfileExtractNormalizer() {
    }

    public static void mergeExtracted(LearningProfile profile, JSONObject obj) {
        if (profile == null || obj == null) {
            return;
        }
        mergeScalar(profile, obj);
        profile.setMainSubject(CourseConstants.SUBJECT);
        profile.setLearnPreference(normalizePreference(
                firstNonBlank(profile.getLearnPreference(), obj.getString("learnPreference"))));
        if (!hasWeakPointsFromKnowledge(profile)) {
            String weak = sanitizeJsonArrayField(obj.get("weakPoints"));
            if (StringUtils.hasText(weak) && !"[]".equals(weak)) {
                profile.setWeakPoints(weak);
            }
        }
        profile.setBaseTags(buildBaseTags(profile));
        profile.setMasteryTags(buildMasteryTags(profile, obj));
        profile.setStyleTags(buildStyleTags(profile));
        profile.setGoalTags(buildGoalTags(profile));
        profile.setBehaviorTags(buildBehaviorTags(profile));
    }

    private static void mergeScalar(LearningProfile profile, JSONObject obj) {
        profile.setGrade(firstNonBlank(profile.getGrade(), obj.getString("grade")));
        profile.setMajor(firstNonBlank(profile.getMajor(), obj.getString("major")));
        profile.setKnowledgeBase(firstNonBlank(profile.getKnowledgeBase(), obj.getString("knowledgeBase")));
        profile.setLearnGoal(firstNonBlank(profile.getLearnGoal(), obj.getString("learnGoal")));
        if (profile.getDailyStudyHours() == null && obj.get("dailyStudyHours") != null) {
            profile.setDailyStudyHours(obj.getBigDecimal("dailyStudyHours"));
        }
    }

    private static boolean hasWeakPointsFromKnowledge(LearningProfile profile) {
        return StringUtils.hasText(profile.getMasteredPoints())
                || (StringUtils.hasText(profile.getWeakPoints())
                && !"[]".equals(profile.getWeakPoints().trim()));
    }

    public static String normalizePreference(String raw) {
        if (!StringUtils.hasText(raw)) {
            return null;
        }
        String s = raw.trim().toLowerCase();
        if (VALID_PREFERENCES.contains(s)) {
            return s;
        }
        if (s.contains("|")) {
            String parsed = DialogueSlotTracker.parsePreferenceFromText(raw);
            if (parsed != null) {
                return parsed;
            }
            return "mixed";
        }
        return DialogueSlotTracker.parsePreferenceFromText(raw);
    }

    private static String buildBaseTags(LearningProfile profile) {
        List<String> tags = new ArrayList<>();
        addTag(tags, profile.getGrade());
        addTag(tags, profile.getMajor());
        if (StringUtils.hasText(profile.getKnowledgeBase())) {
            String kb = profile.getKnowledgeBase().trim();
            if (kb.length() <= 40) {
                addTag(tags, kb);
            } else {
                addTag(tags, summarizeKnowledgeBase(kb));
            }
        }
        return JSON.toJSONString(tags);
    }

    private static String summarizeKnowledgeBase(String kb) {
        if (containsAny(kb, "零基础", "没学过", "从未")) {
            return "零基础";
        }
        if (containsAny(kb, "熟练", "精通", "项目经验")) {
            return "基础较好";
        }
        if (containsAny(kb, "语法", "入门", "学过")) {
            return "有Python基础";
        }
        return kb.length() > 20 ? kb.substring(0, 20) : kb;
    }

    private static String buildMasteryTags(LearningProfile profile, JSONObject obj) {
        JSONArray fromAi = obj.getJSONArray("masteryTags");
        if (fromAi != null && !fromAi.isEmpty()) {
            JSONObject first = fromAi.getJSONObject(0);
            if (first != null && isValidMasteryEntry(first)) {
                return JSON.toJSONString(List.of(first));
            }
        }
        String level = inferMasteryLevel(profile.getKnowledgeBase());
        JSONObject tag = new JSONObject();
        tag.put("subject", CourseConstants.SUBJECT);
        tag.put("level", level);
        return JSON.toJSONString(List.of(tag));
    }

    private static boolean isValidMasteryEntry(JSONObject entry) {
        String level = entry.getString("level");
        return StringUtils.hasText(level)
                && !PLACEHOLDER_TAG_WORDS.contains(level.trim())
                && !level.contains("|");
    }

    private static String inferMasteryLevel(String knowledgeBase) {
        if (!StringUtils.hasText(knowledgeBase)) {
            return "一般";
        }
        String kb = knowledgeBase;
        if (containsAny(kb, "零基础", "没学过", "从未", "不会")) {
            return "薄弱";
        }
        if (containsAny(kb, "熟练", "精通", "项目", "工作")) {
            return "良好";
        }
        if (containsAny(kb, "优秀", "竞赛", "深入")) {
            return "优秀";
        }
        if (containsAny(kb, "语法", "入门", "基础", "学过")) {
            return "一般";
        }
        return "一般";
    }

    private static String buildStyleTags(LearningProfile profile) {
        List<String> tags = new ArrayList<>();
        String pref = profile.getLearnPreference();
        if ("text".equals(pref)) {
            tags.add("偏好图文");
        } else if ("video".equals(pref)) {
            tags.add("偏好视频");
        } else if ("exercise".equals(pref)) {
            tags.add("偏好刷题");
        } else if ("mixed".equals(pref)) {
            tags.add("混合学习");
        }
        return JSON.toJSONString(tags);
    }

    private static String buildGoalTags(LearningProfile profile) {
        List<String> tags = new ArrayList<>();
        if (StringUtils.hasText(profile.getLearnGoal())) {
            String goal = profile.getLearnGoal().trim();
            if (goal.length() <= 24) {
                addTag(tags, goal);
            } else {
                addTag(tags, goal.substring(0, 24));
            }
        }
        return JSON.toJSONString(tags);
    }

    private static String buildBehaviorTags(LearningProfile profile) {
        List<String> tags = new ArrayList<>();
        if (profile.getDailyStudyHours() != null) {
            tags.add("每日" + profile.getDailyStudyHours().stripTrailingZeros().toPlainString() + "小时");
        }
        return JSON.toJSONString(tags);
    }

    private static String sanitizeJsonArrayField(Object val) {
        if (val == null) {
            return null;
        }
        JSONArray arr;
        if (val instanceof JSONArray) {
            arr = (JSONArray) val;
        } else if (val instanceof List) {
            arr = new JSONArray((List<?>) val);
        } else {
            return null;
        }
        LinkedHashSet<String> cleaned = new LinkedHashSet<>();
        for (int i = 0; i < arr.size(); i++) {
            Object item = arr.get(i);
            if (item == null) {
                continue;
            }
            String s = item.toString().trim();
            if (!StringUtils.hasText(s) || isPlaceholder(s)) {
                continue;
            }
            cleaned.add(s);
        }
        if (cleaned.isEmpty()) {
            return "[]";
        }
        return JSON.toJSONString(new ArrayList<>(cleaned));
    }

    private static boolean isPlaceholder(String s) {
        if (PLACEHOLDER_TAG_WORDS.contains(s)) {
            return true;
        }
        return s.contains("|") && VALID_PREFERENCES.stream().anyMatch(s::contains);
    }

    private static void addTag(List<String> tags, String value) {
        if (!StringUtils.hasText(value)) {
            return;
        }
        String v = value.trim();
        if (!isPlaceholder(v) && !tags.contains(v)) {
            tags.add(v);
        }
    }

    private static String firstNonBlank(String draft, String extracted) {
        if (StringUtils.hasText(draft)) {
            return draft.trim();
        }
        if (!StringUtils.hasText(extracted)) {
            return null;
        }
        String e = extracted.trim();
        return isPlaceholder(e) ? null : e;
    }

    private static boolean containsAny(String text, String... keywords) {
        for (String k : keywords) {
            if (text.contains(k)) {
                return true;
            }
        }
        return false;
    }
}
