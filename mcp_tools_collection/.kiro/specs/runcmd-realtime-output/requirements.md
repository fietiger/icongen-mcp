# Requirements Document

## Introduction

本文档定义了 runcmd-mcp 项目的实时输出流功能需求。该功能旨在解决长时间运行命令在执行过程中无法获取中间输出的问题，让用户能够在命令执行期间实时查看 stdout/stderr 输出，而不必等待命令完全结束。

## Glossary

- **RunCmdService**: runcmd-mcp 的核心服务类，负责管理命令的异步执行和状态查询
- **PTY (Pseudo Terminal)**: 伪终端，模拟真实终端环境，使程序认为自己在与真实终端交互
- **ConPTY**: Windows 10 1809+ 提供的原生伪终端 API
- **pywinpty**: Windows 平台的 Python PTY 库，封装了 ConPTY
- **Output_Buffer**: 输出缓冲区，用于存储命令执行过程中产生的实时输出
- **Streaming_Output**: 流式输出，指命令执行过程中持续产生并可被读取的输出数据
- **Token**: 命令执行任务的唯一标识符 (UUID)

## Requirements

### Requirement 1: 实时输出捕获

**User Story:** As a developer, I want to capture command output in real-time during execution, so that I can monitor long-running commands without waiting for completion.

#### Acceptance Criteria

1. WHEN a command is executed, THE RunCmdService SHALL capture stdout output incrementally as it is produced
2. WHEN a command is executed, THE RunCmdService SHALL capture stderr output incrementally as it is produced
3. WHILE a command is running, THE Output_Buffer SHALL accumulate all output data without loss
4. WHEN output is captured, THE RunCmdService SHALL preserve the chronological order of output lines

### Requirement 2: 中间状态查询

**User Story:** As a developer, I want to query partial output while a command is still running, so that I can see progress without interrupting execution.

#### Acceptance Criteria

1. WHEN query_command_status is called for a running command, THE RunCmdService SHALL return currently accumulated stdout
2. WHEN query_command_status is called for a running command, THE RunCmdService SHALL return currently accumulated stderr
3. WHEN query_command_status is called multiple times, THE RunCmdService SHALL return progressively more output as it becomes available
4. WHILE a command is running, THE query_command_status SHALL NOT block or delay command execution

### Requirement 3: PTY 模式支持

**User Story:** As a developer, I want commands to run in a PTY environment, so that programs that require terminal interaction (like progress bars) work correctly.

#### Acceptance Criteria

1. WHERE PTY mode is enabled, THE RunCmdService SHALL execute commands in a pseudo-terminal environment
2. WHEN running in PTY mode on Windows, THE RunCmdService SHALL use pywinpty for terminal emulation
3. WHEN running in PTY mode on Unix, THE RunCmdService SHALL use the standard pty module
4. IF PTY initialization fails, THEN THE RunCmdService SHALL fall back to standard subprocess execution with a warning
5. WHEN PTY mode is used, THE RunCmdService SHALL capture ANSI escape sequences and control characters

### Requirement 4: 输出缓冲管理

**User Story:** As a system administrator, I want output buffers to be managed efficiently, so that long-running commands don't consume excessive memory.

#### Acceptance Criteria

1. THE Output_Buffer SHALL have a configurable maximum size limit (default 10MB)
2. WHEN the buffer exceeds the maximum size, THE RunCmdService SHALL truncate older output while preserving recent output
3. WHEN buffer truncation occurs, THE RunCmdService SHALL indicate that truncation happened in the query response
4. WHEN a command completes, THE Output_Buffer SHALL retain the final output until explicitly cleared or the task expires

### Requirement 5: 增量输出查询

**User Story:** As a developer, I want to fetch only new output since my last query, so that I can efficiently poll for updates without re-downloading all output.

#### Acceptance Criteria

1. WHEN query_command_status is called with an offset parameter, THE RunCmdService SHALL return only output after that offset
2. THE query response SHALL include the current total output length for use as the next offset
3. WHEN offset exceeds current output length, THE RunCmdService SHALL return empty output without error
4. IF offset is not provided, THEN THE RunCmdService SHALL return all accumulated output

### Requirement 6: 向后兼容性

**User Story:** As an existing user, I want the new features to be backward compatible, so that my existing integrations continue to work.

#### Acceptance Criteria

1. THE run_command tool interface SHALL remain backward compatible with existing parameters
2. THE query_command_status tool interface SHALL remain backward compatible with existing response format
3. WHERE new parameters are added, THE RunCmdService SHALL use sensible defaults that preserve existing behavior
4. WHEN PTY mode is not explicitly enabled, THE RunCmdService SHALL use standard subprocess execution (current behavior)

### Requirement 7: 错误处理

**User Story:** As a developer, I want clear error messages when something goes wrong, so that I can diagnose and fix issues quickly.

#### Acceptance Criteria

1. IF PTY creation fails, THEN THE RunCmdService SHALL return a descriptive error message
2. IF output buffer operations fail, THEN THE RunCmdService SHALL log the error and continue execution
3. WHEN a command times out, THE RunCmdService SHALL preserve any partial output captured before timeout
4. IF an unexpected error occurs during output capture, THEN THE RunCmdService SHALL not crash the service
