# winterm MCP 工具 PowerShell 调用问题分析

## 概述
本文档总结了在当前环境中使用 `winterm` MCP 工具调用 PowerShell 命令时遇到的失败现象，并分析了其根本原因。

## 失败现象汇总

### 1. 直接调用 `powershell` (Shell Type: cmd)
- **命令**: `powershell -Command "Get-Date"`
- **结果**: ❌ 失败
- **错误信息**: `'powershell' 不是内部或外部命令，也不是可运行的程序或批处理文件。`
- **分析**: 系统的 `PATH` 环境变量中不包含 PowerShell 的安装路径，导致 `cmd` 无法找到 `powershell.exe`。

### 2. 指定 Shell Type 为 `powershell`
- **命令**: `Get-Date`
- **Shell Type**: `powershell`
- **结果**: ❌ 失败
- **错误信息**: `[WinError 2] 系统找不到指定的文件。`
- **分析**: `winterm` 工具在内部尝试启动 `powershell` 进程时，可能同样依赖于 `PATH` 环境变量，因此在受限环境中无法定位到可执行文件。

### 3. 指定工作目录为 PowerShell 安装路径 (Shell Type: powershell)
- **命令**: `Get-Date -Format "yyyy-MM-dd HH:mm:ss"`
- **Shell Type**: `powershell`
- **Working Directory**: `C:\Windows\System32\WindowsPowerShell\v1.0\`
- **结果**: ❌ 失败
- **错误信息**: `[WinError 2] 系统找不到指定的文件。`
- **分析**: 即使工作目录设置正确，`winterm` 的底层实现似乎并未利用该目录来查找 `powershell.exe`，而是依然依赖全局的 `PATH`。

## 成功方案

### 通过完整路径调用 (Shell Type: cmd)
- **命令**: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command "Get-Date"`
- **Shell Type**: `cmd`
- **结果**: ✅ 成功
- **分析**: 通过提供 `powershell.exe` 的绝对路径，绕过了对 `PATH` 环境变量的依赖，直接指定了要执行的程序，从而在受限环境中成功运行。

## 根本原因

所有失败现象的根本原因在于 **`winterm` MCP 工具运行在一个受限的沙箱环境中**。该环境具有以下特征：
- **受限的 `PATH` 环境变量**：关键系统工具（如 `powershell.exe`）的路径未被包含。
- **严格的进程创建策略**：可能只允许通过完整路径明确指定的可执行文件才能被启动。

这种设计是一种安全隔离措施，旨在防止潜在的滥用和对宿主系统的探测。

## 结论与建议

在当前的沙箱环境中，若需通过 `winterm` 执行 PowerShell 命令，**必须使用 `shell_type: cmd` 并在命令中显式指定 `powershell.exe` 的完整绝对路径**。

示例：
```json
{
  "command": "C:\\\\Windows\\\\System32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe -Command \\\"Your-PowerShell-Command\\\"",
  "shell_type": "cmd"
}
```
避免直接使用 `shell_type: powershell` 或仅使用 `powershell` 命令名，因为这些方式在受限环境中不可靠。