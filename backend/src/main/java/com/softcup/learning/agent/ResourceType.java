package com.softcup.learning.agent;

import lombok.Getter;

@Getter
public enum ResourceType {
    LECTURE("lecture", "知识点讲义"),
    EXAM_SUMMARY("exam_summary", "考点总结"),
    EXERCISE("exercise", "课后习题"),
    COURSEWARE("courseware", "结构化课件");

    private final String code;
    private final String label;

    ResourceType(String code, String label) {
        this.code = code;
        this.label = label;
    }
}
