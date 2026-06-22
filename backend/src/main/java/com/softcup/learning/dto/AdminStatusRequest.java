package com.softcup.learning.dto;

import lombok.Data;

@Data
public class AdminStatusRequest {
    /** true=启用 false=禁用 */
    private Boolean enabled;
}
