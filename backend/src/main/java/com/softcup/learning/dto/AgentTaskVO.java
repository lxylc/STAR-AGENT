package com.softcup.learning.dto;

import com.softcup.learning.entity.AgentSubTask;
import com.softcup.learning.entity.AgentTask;
import com.softcup.learning.entity.LearningResource;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class AgentTaskVO {
    private AgentTask task;
    private List<AgentSubTask> subTasks;
    private List<LearningResource> resources;
}
