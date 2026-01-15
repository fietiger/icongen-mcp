# winterm-mcp

**更新日期**: 2026-01-16  
**版本**: 0.1.1

Windows Terminal MCP Service - 专门支持 Windows 终端的异步命令执行工具。

## 功能特性

- **PowerShell 支持**: 直接执行 PowerShell 命令（默认）
- **Cmd 支持**: 可选执行 cmd 命令
- **异步执行**: 后台执行命令，立即返回 token
- **状态查询**: 查询命令执行状态和结果
- **超时控制**: 可设置超时时间（1-3600秒）
- **工作目录**: 指定执行目录
- **自动编码**: 自动处理 PowerShell (UTF-8) 和 Cmd (GBK) 编码

## 安装

```bash
cd winterm_mcp_standalone
pip install -e .
```

## 使用方法

### MCP 配置

在 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "winterm-mcp": {
      "command": "winterm-mcp"
    }
  }
}
```

### 工具接口

#### run_command

异步执行 Windows 终端命令。

**参数**:
- `command` (string): 要执行的命令（必填，1-1000字符）
- `shell_type` (string, optional): Shell 类型，`powershell` 或 `cmd`，默认 `powershell`
- `timeout` (integer, optional): 超时秒数（1-3600），默认 30
- `working_directory` (string, optional): 工作目录（可选，默认当前目录）

**返回**:
```json
{
  "token": "uuid-string",
  "status": "pending",
  "message": "submitted"
}
```

#### query_command_status

查询命令执行状态和结果。

**参数**:
- `token` (string): 命令 token

**返回**:
```json
{
  "token": "uuid-string",
  "status": "completed",
  "exit_code": 0,
  "stdout": "command output",
  "stderr": "",
  "execution_time": 0.123,
  "timeout_occurred": false
}
```

## 使用示例

### PowerShell 命令

```python
# 获取当前日期
run_command("Get-Date")

# 列出进程
run_command("Get-Process | Select-Object -First 5")

# 构建项目
run_command("dotnet build", timeout=60, working_directory="d:/project")
```

### Cmd 命令

```python
# 列出目录
run_command("dir", shell_type="cmd")

# Ping 测试
run_command("ping 127.0.0.1 -n 4", shell_type="cmd")
```

### 查询命令状态

```python
# 提交命令
result = run_command("Get-Process")
token = result["token"]

# 查询状态
status = query_command_status(token)
if status["status"] == "completed":
    print(status["stdout"])
```

## 技术架构

- **框架**: FastMCP
- **并发**: 多线程异步执行
- **编码**: 自动处理 UTF-8 和 GBK
- **平台**: Windows

## 与 runcmd-mcp 的区别

| 特性 | runcmd-mcp | winterm-mcp |
|------|-----------|-------------|
| Shell 类型 | 仅 cmd | PowerShell + Cmd |
| Windows 支持 | 部分 | 完整 |
| 编码处理 | 固定 | 自动适配 |
| 平台 | 跨平台 | Windows 专用 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。
