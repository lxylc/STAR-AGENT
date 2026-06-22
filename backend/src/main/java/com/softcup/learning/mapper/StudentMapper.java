package com.softcup.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.softcup.learning.entity.Student;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface StudentMapper extends BaseMapper<Student> {
}
