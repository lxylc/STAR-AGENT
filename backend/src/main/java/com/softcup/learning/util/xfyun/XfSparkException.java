package com.softcup.learning.util.xfyun;

public class XfSparkException extends RuntimeException {

    private final Integer xfCode;

    public XfSparkException(String message) {
        super(message);
        this.xfCode = null;
    }

    public XfSparkException(Integer xfCode, String message) {
        super(message);
        this.xfCode = xfCode;
    }

    public Integer getXfCode() {
        return xfCode;
    }
}
