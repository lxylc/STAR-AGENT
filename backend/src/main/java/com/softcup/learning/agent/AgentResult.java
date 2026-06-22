package com.softcup.learning.agent;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class AgentResult {
    private ResourceType resourceType;
    private String title;
    private String content;
    /** 习题等结构化 JSON */
    private String contentJson;
}
