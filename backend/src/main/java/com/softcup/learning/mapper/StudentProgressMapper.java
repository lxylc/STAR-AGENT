package com.softcup.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.softcup.learning.entity.StudentProgress;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface StudentProgressMapper extends BaseMapper<StudentProgress> {
}
