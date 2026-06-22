package com.softcup.learning.agent;

import lombok.Getter;

@Getter
public enum AgentType {
    LECTURE("LECTURE", "知识点梳理智能体"),
    EXERCISE("EXERCISE", "习题生成智能体"),
    COURSEWARE("COURSEWARE", "课件编辑智能体");

    private final String code;
    private final String label;

    AgentType(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public static AgentType fromCode(String code) {
        for (AgentType t : values()) {
            if (t.code.equalsIgnoreCase(code)) {
                return t;
            }
        }
        throw new IllegalArgumentException("未知智能体类型: " + code);
    }
}
