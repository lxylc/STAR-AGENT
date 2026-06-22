package com.softcup.learning.common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.BindException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(com.softcup.learning.util.xfyun.XfSparkException.class)
    public Result<Void> handleXf(com.softcup.learning.util.xfyun.XfSparkException e) {
        log.error("讯飞接口异常 code={}: {}", e.getXfCode(), e.getMessage());
        return Result.fail(502, e.getMessage());
    }

    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusiness(BusinessException e) {
        log.warn("业务异常: {}", e.getMessage());
        return Result.fail(e.getCode(), e.getMessage());
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, BindException.class})
    public Result<Void> handleValid(Exception e) {
        String msg = e instanceof MethodArgumentNotValidException m
                ? m.getBindingResult().getFieldError().getDefaultMessage()
                : "参数校验失败";
        return Result.fail(400, msg);
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleOther(Exception e) {
        log.error("系统异常", e);
        return Result.fail("系统繁忙，请稍后重试");
    }
}
