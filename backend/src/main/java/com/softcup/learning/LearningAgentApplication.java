package com.softcup.learning;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration;

/**
 * 模块1暂可不启动 Redis；后续模块启用缓存时删除 exclude。
 */
@SpringBootApplication(exclude = {RedisAutoConfiguration.class})
@MapperScan("com.softcup.learning.mapper")
public class LearningAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(LearningAgentApplication.class, args);
    }
}
