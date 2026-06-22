/** 12 课程模块（与后端 knowledge_data.MODULE_NAMES 一致） */
export const MODULE_NAMES = [
  'Python环境与基础语法',
  '变量、数据类型与运算符',
  '流程控制：条件与循环',
  '组合数据结构：列表/元组/字典/集合',
  '函数、高阶函数与装饰器',
  '异常处理与调试',
  '字符串与正则表达式',
  '模块、包与虚拟环境',
  '面向对象编程',
  '文件IO与数据持久化',
  '网络请求与API调用',
  '基础算法与代码规范'
]

export const LEARNING_STAGES = [
  { stage: 1, stage_name: '阶段一·入门奠基', module_names: MODULE_NAMES.slice(0, 3) },
  { stage: 2, stage_name: '阶段二·核心语法', module_names: MODULE_NAMES.slice(3, 6) },
  { stage: 3, stage_name: '阶段三·进阶能力', module_names: MODULE_NAMES.slice(6, 9) },
  { stage: 4, stage_name: '阶段四·实战应用', module_names: MODULE_NAMES.slice(9, 12) }
]
