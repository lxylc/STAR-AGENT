package com.softcup.learning.agent;

import com.softcup.learning.entity.LearningProfile;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class AgentContext {
    private Long studentId;
    private Long profileId;
    private Long taskId;
    private Long subTaskId;
    private LearningProfile profile;
    private String subject;
    private String knowledgePoint;
    /** 画像标签 JSON 快照 */
    private String profileTagsJson;
    /** 上游讲义内容，供课件/习题智能体参考 */
    private String lectureContent;
    /** 考点总结，供课件智能体参考 */
    private String summaryContent;
}
