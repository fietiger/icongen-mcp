# runcmd-mcp

**版本**: 0.1.3

runcmd-mcp 是一个Model Context Protocol (MCP) 服务，提供异步执行系统命令的功能。

## 功能特点

- **异步执行**: 命令在后台线程中执行，不会阻塞主线程
- **状态查询**: 可随时查询命令执行状态和结果
- **超时控制**: 支持设置命令执行超时时间
- **资源管理**: 自动管理命令执行状态
- **MCP兼容**: 与MCP协议兼容，可与其他MCP客户端集成

## 工具说明

### run_command

异步执行系统命令，立即返回 token。命令将在后台执行，可通过 query_command_status 查询结果。

**参数:**
- `command` (string, required): 要执行的命令字符串
- `timeout` (integer, optional, default: 30): 超时秒数 (1-3600)
- `working_directory` (string, optional): 工作目录（可选，默认为当前目录）

**返回:**
- `token` (string): 任务 token (GUID 字符串)
- `status` (string): 任务状态 ("pending")
- `message` (string): 提交状态消息 ("submitted")

### query_command_status

查询命令执行状态和结果。返回命令的当前状态、退出码、输出等信息。

**参数:**
- `token` (string, required): 任务 token (GUID 字符串)

**返回:**
- `token` (string): 任务 token (GUID 字符串)
- `status` (string): 任务状态 ("pending", "running", "completed", "not_found")
- `exit_code` (integer, optional): 命令退出码
- `stdout` (string, optional): 标准输出
- `stderr` (string, optional): 标准错误输出
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
``` json
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

1. 调用 `run_command` 提交命令并获取token
2. 使用 `query_command_status` 查询命令执行状态和结果
3. 命令在后台异步执行，不会阻塞主线程