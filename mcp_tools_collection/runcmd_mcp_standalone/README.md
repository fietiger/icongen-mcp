# runcmd-mcp

**版本**: 0.2.0

runcmd-mcp 是一个Model Context Protocol (MCP) 服务，提供异步执行系统命令的功能，支持实时输出流。

## 功能特点

- **异步执行**: 命令在后台线程中执行，不会阻塞主线程
- **实时输出流**: 支持在命令执行过程中实时获取 stdout/stderr 输出
- **增量查询**: 支持通过偏移量只获取新增输出，高效轮询
- **PTY 模式**: 支持伪终端模式，正确处理进度条等终端交互程序
- **状态查询**: 可随时查询命令执行状态和结果
- **超时控制**: 支持设置命令执行超时时间
- **缓冲区管理**: 可配置最大缓冲区大小，防止内存溢出
- **资源管理**: 自动管理命令执行状态
- **MCP兼容**: 与MCP协议兼容，可与其他MCP客户端集成

## 工具说明

### run_command

异步执行系统命令，立即返回 token。命令将在后台执行，可通过 query_command_status 查询结果。

**参数:**
- `command` (string, required): 要执行的命令字符串
- `timeout` (integer, optional, default: 30): 超时秒数 (1-3600)
- `working_directory` (string, optional): 工作目录（可选，默认为当前目录）
- `use_pty` (boolean, optional, default: false): 是否使用 PTY 模式执行命令
- `max_buffer_size` (integer, optional, default: 10485760): 最大输出缓冲区大小（字节），默认 10MB

**返回:**
- `token` (string): 任务 token (GUID 字符串)
- `status` (string): 任务状态 ("pending")
- `message` (string): 提交状态消息 ("submitted")

### query_command_status

查询命令执行状态和结果。支持增量查询，只获取新增输出。

**参数:**
- `token` (string, required): 任务 token (GUID 字符串)
- `stdout_offset` (integer, optional, default: 0): stdout 输出偏移量，用于增量查询
- `stderr_offset` (integer, optional, default: 0): stderr 输出偏移量，用于增量查询

**返回:**
- `token` (string): 任务 token (GUID 字符串)
- `status` (string): 任务状态 ("pending", "running", "completed", "not_found")
- `exit_code` (integer, optional): 命令退出码
- `stdout` (string, optional): 标准输出（从偏移量开始）
- `stderr` (string, optional): 标准错误输出（从偏移量开始）
- `stdout_length` (integer): stdout 总长度，可用作下次查询的偏移量
- `stderr_length` (integer): stderr 总长度，可用作下次查询的偏移量
- `stdout_truncated` (boolean): stdout 是否发生过截断
- `stderr_truncated` (boolean): stderr 是否发生过截断
- `execution_time` (number, optional): 执行时间（秒）
- `timeout_occurred` (boolean, optional): 是否发生超时

## 安装和使用

安装:
```bash
pip install runcmd-mcp
```

或者从源码安装:
```bash
pip install -e .
```

### MCP 配置

在 MCP 客户端配置中添加：
```json
{
  "mcpServers": {
    "runcmd-mcp": {
      "command": "uvx",
      "args": [
        "runcmd-mcp"
      ]
    }
  }
}
```

启动MCP服务器:
```bash
runcmd-mcp
```

## 使用示例

### 基本用法

1. 调用 `run_command` 提交命令并获取 token
2. 使用 `query_command_status` 查询命令执行状态和结果
3. 命令在后台异步执行，不会阻塞主线程

### 实时输出流示例

对于长时间运行的命令，可以使用增量查询实时获取输出：

```python
# 1. 提交命令
result = run_command(command="ping -n 10 localhost", timeout=60)
token = result["token"]

# 2. 轮询获取实时输出
stdout_offset = 0
stderr_offset = 0

while True:
    status = query_command_status(
        token=token,
        stdout_offset=stdout_offset,
        stderr_offset=stderr_offset
    )
    
    # 打印新增输出
    if status["stdout"]:
        print(status["stdout"], end="")
    
    # 更新偏移量
    stdout_offset = status["stdout_length"]
    stderr_offset = status["stderr_length"]
    
    # 检查是否完成
    if status["status"] == "completed":
        break
    
    time.sleep(0.5)  # 轮询间隔
```

### PTY 模式示例

对于需要终端交互的程序（如进度条、颜色输出），使用 PTY 模式：

```python
# 使用 PTY 模式执行命令
result = run_command(
    command="python -c \"import tqdm; import time; [time.sleep(0.1) for _ in tqdm.tqdm(range(100))]\"",
    timeout=60,
    use_pty=True
)
token = result["token"]

# PTY 模式会保留 ANSI 转义序列，可以正确显示进度条
```

### 大输出处理

对于可能产生大量输出的命令，可以配置缓冲区大小：

```python
# 设置 5MB 缓冲区
result = run_command(
    command="cat large_file.txt",
    timeout=300,
    max_buffer_size=5 * 1024 * 1024  # 5MB
)

# 查询时检查是否发生截断
status = query_command_status(token=result["token"])
if status["stdout_truncated"]:
    print("警告：输出已被截断，只保留最新数据")
```

## 版本历史

### v0.2.0
- 新增实时输出流功能
- 新增 PTY 模式支持
- 新增增量查询（偏移量参数）
- 新增缓冲区大小配置
- 新增截断状态指示

### v0.1.4
- 初始版本
- 基本的异步命令执行功能
