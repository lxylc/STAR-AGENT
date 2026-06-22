package com.softcup.learning.dto;

import com.softcup.learning.entity.LearningPath;
import com.softcup.learning.entity.LearningPathItem;
import com.softcup.learning.entity.ResourcePushRecord;
import com.softcup.learning.entity.StudentProgress;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class LearningPathDetailVO {
    private LearningPath path;
    private List<LearningPathItem> items;
    private List<ResourcePushRecord> pushRecords;
    private List<StudentProgress> progressList;
    private int pushedCount;
}
