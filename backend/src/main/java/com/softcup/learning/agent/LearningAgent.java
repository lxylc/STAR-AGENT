package com.softcup.learning.agent;

/**
 * 学习资源生成智能体统一接口
 */
public interface LearningAgent {

    AgentType agentType();

    AgentResult execute(AgentContext context);
}
