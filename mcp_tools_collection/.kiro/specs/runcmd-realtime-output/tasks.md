# Implementation Plan: runcmd-mcp 实时输出流功能

## Overview

本实现计划将 runcmd-mcp 项目升级为支持实时输出流功能。实现采用增量方式，先构建核心组件，再集成到现有服务中，最后更新 MCP 接口。

## Tasks

- [x] 1. 实现 StreamingBuffer 核心组件
  - [x] 1.1 创建 StreamingBuffer 类基础结构
    - 创建 `streaming_buffer.py` 文件
    - 实现 `__init__` 方法，初始化缓冲区、锁、最大大小配置
    - 实现 `write` 方法，支持线程安全的数据写入
    - 实现 `get_output` 方法，支持偏移量查询
    - 实现 `get_all` 和 `length` 属性
    - _Requirements: 1.3, 4.1_

  - [x] 1.2 实现缓冲区截断逻辑
    - 在 `write` 方法中添加大小检查
    - 超过最大大小时截断旧数据，保留最新数据
    - 记录截断状态和截断字节数
    - _Requirements: 4.2, 4.3_

  - [ ]* 1.3 编写 StreamingBuffer 属性测试
    - **Property 1: 增量输出捕获完整性**
    - **Property 4: 缓冲区截断正确性**
    - **Property 5: 偏移量查询正确性**
    - **Validates: Requirements 1.3, 4.2, 4.3, 5.1, 5.2, 5.4**

- [x] 2. 实现 SubprocessExecutor 流式执行器
  - [x] 2.1 创建 SubprocessExecutor 类
    - 创建 `executors.py` 文件
    - 实现 `__init__` 方法，接收 StreamingBuffer
    - 实现 `execute` 方法，使用 `subprocess.Popen` 启动进程
    - 配置 `stdout=PIPE, stderr=PIPE, bufsize=1`
    - _Requirements: 1.1, 1.2_

  - [x] 2.2 实现流式输出读取
    - 创建后台线程读取 stdout 和 stderr
    - 使用 `iter(pipe.readline, '')` 逐行读取
    - 将读取的数据写入 StreamingBuffer
    - 处理进程结束和超时情况
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ]* 2.3 编写 SubprocessExecutor 属性测试
    - **Property 2: 输出顺序保持**
    - **Property 3: 中间状态可查询**
    - **Validates: Requirements 1.4, 2.1, 2.2, 2.3**

- [x] 3. 实现 PtyExecutor PTY 执行器
  - [x] 3.1 创建 PtyExecutor 类
    - 在 `executors.py` 中添加 PtyExecutor 类
    - 实现 `__init__` 方法，接收 StreamingBuffer
    - 导入并使用 pywinpty 库
    - _Requirements: 3.1, 3.2_

  - [x] 3.2 实现 PTY 命令执行
    - 使用 `PtyProcess.spawn()` 启动命令
    - 创建后台线程持续读取 PTY 输出
    - 将输出写入 StreamingBuffer
    - 实现超时和终止逻辑
    - _Requirements: 3.1, 3.5_

  - [x] 3.3 实现 PTY 降级机制
    - 捕获 PTY 初始化异常
    - 失败时记录警告日志
    - 返回错误信息供上层处理
    - _Requirements: 3.4, 7.1_

  - [ ]* 3.4 编写 PtyExecutor 属性测试
    - **Property 7: PTY 模式 ANSI 序列保留**
    - **Validates: Requirements 3.5**

- [ ] 4. Checkpoint - 核心组件测试
  - 确保所有核心组件测试通过
  - 如有问题请询问用户

- [x] 5. 扩展 RunCmdService 服务层
  - [x] 5.1 更新 run_command 方法
    - 添加 `use_pty` 参数（默认 False）
    - 添加 `max_buffer_size` 参数（默认 10MB）
    - 创建 StreamingBuffer 实例
    - 根据 `use_pty` 选择执行器
    - _Requirements: 6.1, 6.3, 6.4_

  - [x] 5.2 更新 query_command_status 方法
    - 添加 `stdout_offset` 参数（默认 0）
    - 添加 `stderr_offset` 参数（默认 0）
    - 调用 StreamingBuffer.get_output() 获取增量输出
    - 在响应中添加 length 和 truncated 字段
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.2_

  - [x] 5.3 更新命令执行线程
    - 修改 `_execute_command` 方法
    - 使用新的执行器替代原有 subprocess.run
    - 实现 PTY 降级逻辑
    - 保留超时处理和错误处理
    - _Requirements: 7.2, 7.3, 7.4_

  - [ ]* 5.4 编写服务层属性测试
    - **Property 6: 超时输出保留**
    - **Validates: Requirements 7.3**

- [x] 6. 更新 MCP Server 接口
  - [x] 6.1 更新 run_command tool
    - 添加 `use_pty` 参数定义
    - 添加 `max_buffer_size` 参数定义
    - 更新工具描述文档
    - _Requirements: 6.1_

  - [x] 6.2 更新 query_command_status tool
    - 添加 `stdout_offset` 参数定义
    - 添加 `stderr_offset` 参数定义
    - 更新返回值文档
    - _Requirements: 6.2_

- [x] 7. 更新项目配置和文档
  - [x] 7.1 更新 pyproject.toml
    - 添加 pywinpty 依赖
    - 添加 hypothesis 开发依赖
    - 更新版本号

  - [x] 7.2 更新 README.md
    - 添加新参数说明
    - 添加实时输出使用示例
    - 更新工具文档

- [ ] 8. Final Checkpoint - 完整测试
  - 确保所有测试通过
  - 验证向后兼容性
  - 如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
