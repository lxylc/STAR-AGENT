package com.softcup.learning.util.xfyun;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SparkMessage {
    /** system / user / assistant */
    private String role;
    private String content;
}
