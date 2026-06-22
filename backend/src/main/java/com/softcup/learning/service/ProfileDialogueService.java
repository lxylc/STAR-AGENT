package com.softcup.learning.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.softcup.learning.common.BusinessException;
import com.softcup.learning.dto.DialogueSendRequest;
import com.softcup.learning.dto.DialogueSendResponse;
import com.softcup.learning.entity.LearningProfile;
import com.softcup.learning.entity.ProfileDialogue;
import com.softcup.learning.mapper.ProfileDialogueMapper;
import com.softcup.learning.util.xfyun.SparkMessage;
import com.softcup.learning.util.xfyun.XfSparkClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProfileDialogueService {

    private static final String EXTRACT_SYSTEM_PROMPT = """
            你是学习画像信息抽取专家。根据对话历史，抽取结构化学习画像，只输出合法JSON，不要markdown，不要其他说明。
            规则：
            1. 只填写对话中明确出现的信息，禁止编造。
            2. weakPoints 固定为 []（知识点掌握度由画像构建对话、练习与日常交流自动评估，勿从本对话猜测）。
            3. learnPreference 只能填单个值：text、video、exercise 或 mixed，禁止输出 text|video 这类模板。
            4. baseTags、styleTags、goalTags、behaviorTags 可填空数组 []，后端会根据对话自动生成。
            5. masteryTags 若有则格式为 [{"subject":"Python程序设计","level":"薄弱|一般|良好|优秀"}]，level 只选一个词。
            JSON 示例：
            {
              "grade":"大二",
              "major":"软件工程",
              "mainSubject":"Python程序设计",
              "knowledgeBase":"学过基础语法",
              "weakPoints":[],
              "dailyStudyHours":2.0,
              "learnPreference":"video",
              "learnGoal":"通过课程考试",
              "baseTags":[],
              "masteryTags":[{"subject":"Python程序设计","level":"一般"}],
              "styleTags":[],
              "goalTags":[],
              "behaviorTags":[]
            }
            缺失字段用 null；数组字段无信息时用 []。
            """;

    private final ProfileDialogueMapper dialogueMapper;
    private final LearningProfileService profileService;
    private final XfSparkClient sparkClient;

    @Transactional(rollbackFor = Exception.class)
    public DialogueSendResponse send(DialogueSendRequest req) {
        Long studentId = req.getStudentId();
        LearningProfile profile = profileService.getOrCreateDraft(studentId);

        int roundNo = nextRoundNo(studentId);
        saveDialogue(studentId, profile.getId(), "user", req.getContent(), roundNo);

        boolean finish = shouldExtractProfile(req.getContent(), req.getTryExtract());
        String reply;
        LearningProfile extractedProfile = null;
        boolean extracted = false;

        if (finish) {
            extractedProfile = extractAndSaveProfile(studentId, profile);
            extracted = true;
            boolean rebuild = StringUtils.hasText(req.getContent())
                    && !req.getContent().contains("完成画像");
            reply = rebuild
                    ? "已根据最新对话重新生成学习画像，请到「我的学习画像」查看。知识点掌握度请通过画像构建与练习自动更新。"
                    : "已根据我们的对话生成结构化学习画像，你可以在「我的学习画像」页面查看和编辑。"
                    + "之后可随时发送「重新生成画像」按最新对话更新，无需只能手动改。";
            saveDialogue(studentId, extractedProfile.getId(), "assistant", reply, roundNo);
        } else {
            DialogueSlotTracker.applyFromDialogue(profile, listHistory(studentId));
            profileService.updateDraftFields(profile);
            profile = profileService.getByStudentId(studentId);

            List<DialogueSlotTracker.Slot> missing = DialogueSlotTracker.missingSlots(profile);
            if (missing.isEmpty()) {
                reply = DialogueSlotTracker.buildAllCollectedReply();
            } else {
                reply = chatForGuide(studentId, profile);
                if (repeatsCollectedQuestion(reply, profile)) {
                    reply = DialogueSlotTracker.buildFallbackQuestion(missing.get(0));
                }
            }
            saveDialogue(studentId, profile.getId(), "assistant", reply, roundNo);
            profileService.markBuilding(profile.getId());
        }

        return DialogueSendResponse.builder()
                .reply(reply)
                .roundNo(roundNo)
                .profileId(extracted ? extractedProfile.getId() : profile.getId())
                .profile(extracted ? extractedProfile : profileService.getByStudentId(studentId))
                .extracted(extracted)
                .build();
    }

    @Transactional(rollbackFor = Exception.class)
    public String initSession(Long studentId) {
        LearningProfile profile = profileService.getOrCreateDraft(studentId);
        long count = dialogueMapper.selectCount(new LambdaQueryWrapper<ProfileDialogue>()
                .eq(ProfileDialogue::getStudentId, studentId));
        if (count > 0) {
            ProfileDialogue last = dialogueMapper.selectOne(new LambdaQueryWrapper<ProfileDialogue>()
                    .eq(ProfileDialogue::getStudentId, studentId)
                    .eq(ProfileDialogue::getRole, "assistant")
                    .orderByDesc(ProfileDialogue::getId)
                    .last("LIMIT 1"));
            return last != null ? last.getContent() : "欢迎回来，请继续补充你的学习信息。";
        }
        String welcome = "你好！我是《Python程序设计》课程的学习画像助手。我会依次了解：年级、专业、Python 基础、"
                + "每日学习时长、学习偏好与学习目标（每项只问一次）。"
                + "知识点掌握度将在画像构建与练习过程中自动评估，无需手动勾选。"
                + "请先告诉我：你目前读大几、什么专业？";
        saveDialogue(studentId, profile.getId(), "assistant", welcome, 0);
        return welcome;
    }

    public List<ProfileDialogue> listHistory(Long studentId) {
        return dialogueMapper.selectList(new LambdaQueryWrapper<ProfileDialogue>()
                .eq(ProfileDialogue::getStudentId, studentId)
                .orderByAsc(ProfileDialogue::getRoundNo, ProfileDialogue::getId));
    }

    @Transactional(rollbackFor = Exception.class)
    public LearningProfile forceExtract(Long studentId) {
        LearningProfile profile = profileService.getOrCreateDraft(studentId);
        return extractAndSaveProfile(studentId, profile);
    }

    private String chatForGuide(Long studentId, LearningProfile profile) {
        String dynamicPrompt = DialogueSlotTracker.buildGuideSystemPrompt(profile);
        List<SparkMessage> messages = buildMessages(studentId, dynamicPrompt);
        return sparkClient.chat(messages);
    }

    /** 检测 AI 是否仍在追问已收集字段 */
    private boolean repeatsCollectedQuestion(String reply, LearningProfile profile) {
        if (!StringUtils.hasText(reply)) {
            return false;
        }
        if (isFilled(profile, "learnPreference")
                && containsAny(reply, "偏好", "书籍", "视频", "刷题", "学习方式")) {
            return true;
        }
        if (isFilled(profile, "learnGoal") && containsAny(reply, "目标", "成为", "规划")) {
            return true;
        }
        if (isFilled(profile, "grade") && containsAny(reply, "大几", "年级")) {
            return true;
        }
        if (isFilled(profile, "major") && containsAny(reply, "专业")) {
            return true;
        }
        if (isFilled(profile, "dailyStudyHours") && containsAny(reply, "小时", "时长", "投入")) {
            return true;
        }
        if (isFilled(profile, "knowledgeBase") && containsAny(reply, "基础", "水平")) {
            return true;
        }
        return false;
    }

    private boolean isFilled(LearningProfile profile, String key) {
        return switch (key) {
            case "grade" -> StringUtils.hasText(profile.getGrade());
            case "major" -> StringUtils.hasText(profile.getMajor());
            case "knowledgeBase" -> StringUtils.hasText(profile.getKnowledgeBase());
            case "dailyStudyHours" -> profile.getDailyStudyHours() != null;
            case "learnPreference" -> StringUtils.hasText(profile.getLearnPreference());
            case "learnGoal" -> StringUtils.hasText(profile.getLearnGoal());
            default -> false;
        };
    }

    private boolean containsAny(String text, String... keywords) {
        for (String k : keywords) {
            if (text.contains(k)) {
                return true;
            }
        }
        return false;
    }

    private LearningProfile extractAndSaveProfile(Long studentId, LearningProfile profile) {
        DialogueSlotTracker.applyFromDialogue(profile, listHistory(studentId));
        profileService.updateDraftFields(profile);
        profile = profileService.getByStudentId(studentId);

        List<SparkMessage> messages = buildMessages(studentId, EXTRACT_SYSTEM_PROMPT);
        String summary = DialogueSlotTracker.buildCollectedSummary(profile);
        messages.add(new SparkMessage("user",
                "请根据以上全部对话，输出学习画像JSON。对话中已收集的信息如下（须保持一致，勿与对话矛盾）：\n"
                        + summary));
        String jsonText = sparkClient.chat(messages);
        String cleaned = cleanJson(jsonText);
        log.info("画像抽取结果 studentId={}: {}", studentId, cleaned);
        JSONObject obj;
        try {
            obj = JSON.parseObject(cleaned);
        } catch (Exception e) {
            throw new BusinessException("AI画像解析失败，请继续补充对话后重试");
        }
        return profileService.applyExtractedProfile(profile, obj, cleaned);
    }

    private List<SparkMessage> buildMessages(Long studentId, String systemPrompt) {
        List<SparkMessage> messages = new ArrayList<>();
        messages.add(new SparkMessage("system", systemPrompt));
        List<ProfileDialogue> history = listHistory(studentId);
        for (ProfileDialogue d : history) {
            if ("system".equals(d.getRole())) {
                continue;
            }
            messages.add(new SparkMessage(d.getRole(), d.getContent()));
        }
        return messages;
    }

    private int nextRoundNo(Long studentId) {
        ProfileDialogue last = dialogueMapper.selectOne(new LambdaQueryWrapper<ProfileDialogue>()
                .eq(ProfileDialogue::getStudentId, studentId)
                .orderByDesc(ProfileDialogue::getRoundNo)
                .last("LIMIT 1"));
        return last == null ? 1 : last.getRoundNo() + 1;
    }

    private void saveDialogue(Long studentId, Long profileId, String role, String content, int roundNo) {
        ProfileDialogue d = new ProfileDialogue();
        d.setStudentId(studentId);
        d.setProfileId(profileId);
        d.setRole(role);
        d.setContent(content);
        d.setRoundNo(roundNo);
        dialogueMapper.insert(d);
    }

    /** 触发画像抽取：完成画像、重新生成等口令，或前端 tryExtract=true */
    private static boolean shouldExtractProfile(String content, Boolean tryExtract) {
        if (Boolean.TRUE.equals(tryExtract)) {
            return true;
        }
        if (!StringUtils.hasText(content)) {
            return false;
        }
        String c = content.trim();
        return c.contains("完成画像")
                || c.contains("重新构造画像")
                || c.contains("重新生成画像")
                || c.contains("重新生成学习画像")
                || c.contains("更新画像")
                || c.contains("重新画像")
                || c.contains("再生成画像")
                || c.contains("重新抽取");
    }

    private String cleanJson(String text) {
        if (!StringUtils.hasText(text)) {
            return "{}";
        }
        String t = text.trim();
        if (t.startsWith("```")) {
            t = t.replaceAll("^```json\\s*", "").replaceAll("^```\\s*", "").replaceAll("```\\s*$", "");
        }
        int start = t.indexOf('{');
        int end = t.lastIndexOf('}');
        if (start >= 0 && end > start) {
            return t.substring(start, end + 1);
        }
        return t;
    }
}
