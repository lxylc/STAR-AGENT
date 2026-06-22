package com.softcup.learning.dto;

import com.softcup.learning.entity.LearningProfile;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class DialogueSendResponse {
    private String reply;
    private Integer roundNo;
    private Long profileId;
    private LearningProfile profile;
    private Boolean extracted;
}
