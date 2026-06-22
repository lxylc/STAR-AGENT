package com.softcup.learning.agent;

import com.softcup.learning.common.BusinessException;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

@Component
public class AgentRegistry {

    private final Map<AgentType, LearningAgent> agents = new EnumMap<>(AgentType.class);

    public AgentRegistry(List<LearningAgent> agentList) {
        for (LearningAgent agent : agentList) {
            agents.put(agent.agentType(), agent);
        }
    }

    public LearningAgent get(AgentType type) {
        LearningAgent agent = agents.get(type);
        if (agent == null) {
            throw new BusinessException("未注册智能体: " + type);
        }
        return agent;
    }
}
