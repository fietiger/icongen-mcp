# winterm-mcp PowerShell 沙箱环境问题分析与对策

**文档日期**: 2026-01-16  
**版本**: 1.0.0

---

## 1. 问题概述

在某些 MCP 客户端环境中使用 `winterm-mcp` 工具时，PowerShell 命令执行失败。经分析，根本原因是 MCP 服务运行在一个**受限的沙箱环境**中，该环境的 `PATH` 环境变量不包含 PowerShell 的安装路径。

## 2. 问题根因分析

### 2.1 当前实现方式

`service.py` 中的 `_execute_command` 方法使用以下方式调用 PowerShell：

```python
cmd_args = [
    "powershell",  # ← 问题所在：依赖 PATH 环境变量
    "-NoProfile",
    "-NoLogo",
    "-NonInteractive",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    command,
]
```

### 2.2 失败原因

| 场景 | 失败原因 |
|------|----------|
| `shell_type: powershell` | `subprocess.run()` 无法在 PATH 中找到 `powershell` |
| `shell_type: cmd` + `powershell` 命令 | cmd 同样无法在 PATH 中找到 `powershell` |
| 设置 `working_directory` | `subprocess.run()` 的 `cwd` 参数不影响可执行文件查找 |

### 2.3 沙箱环境特征

- **受限的 PATH 环境变量**：不包含 `C:\Windows\System32\WindowsPowerShell\v1.0\`
- **安全隔离设计**：防止对宿主系统的探测和潜在滥用
- **进程创建限制**：可能只允许通过完整路径指定的可执行文件

## 3. 解决方案

### 3.1 方案一：使用绝对路径（推荐）

修改 `service.py`，使用 PowerShell 的绝对路径：

```python
import os

# PowerShell 可执行文件的标准路径
POWERSHELL_PATHS = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

# PowerShell Core (pwsh) 的常见路径
PWSH_PATHS = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
]

def _find_powershell() -> str:
    """
    查找可用的 PowerShell 可执行文件路径
    
    Returns:
        PowerShell 可执行文件的绝对路径
        
    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    # 优先使用 Windows PowerShell
    for path in POWERSHELL_PATHS:
        if os.path.isfile(path):
            return path
    
    # 尝试 PowerShell Core
    for path in PWSH_PATHS:
        if os.path.isfile(path):
            return path
    
    # 最后尝试 PATH（兼容正常环境）
    import shutil
    ps_path = shutil.which("powershell")
    if ps_path:
        return ps_path
    
    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        return pwsh_path
    
    raise FileNotFoundError(
        "PowerShell not found. Checked paths: " + 
        ", ".join(POWERSHELL_PATHS + PWSH_PATHS)
    )
```

### 3.2 方案二：环境变量注入

在启动子进程时，手动注入 PowerShell 路径到 PATH：

```python
import os

def _get_enhanced_env() -> dict:
    """
    获取增强的环境变量，确保包含 PowerShell 路径
    """
    env = os.environ.copy()
    
    ps_dir = r"C:\Windows\System32\WindowsPowerShell\v1.0"
    current_path = env.get("PATH", "")
    
    if ps_dir.lower() not in current_path.lower():
        env["PATH"] = ps_dir + os.pathsep + current_path
    
    return env

# 在 subprocess.run 中使用
result = subprocess.run(
    cmd_args,
    capture_output=True,
    text=True,
    timeout=timeout,
    cwd=working_directory,
    encoding=encoding,
    stdin=subprocess.DEVNULL,
    env=_get_enhanced_env(),  # ← 添加增强的环境变量
)
```

### 3.3 方案三：配置化路径（最灵活）

允许用户通过环境变量或配置文件指定 PowerShell 路径：

```python
import os

def _get_powershell_path() -> str:
    """
    获取 PowerShell 路径，支持环境变量配置
    
    环境变量优先级：
    1. WINTERM_POWERSHELL_PATH - 用户指定的完整路径
    2. 默认路径探测
    """
    # 检查用户配置的路径
    custom_path = os.environ.get("WINTERM_POWERSHELL_PATH")
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    
    # 使用默认路径探测
    return _find_powershell()
```

## 4. 推荐实现

综合考虑兼容性、可维护性和用户体验，推荐采用**方案一 + 方案三的组合**：

### 4.1 修改后的 `service.py`

```python
"""
winterm服务模块 - 异步执行Windows终端命令服务
"""

import subprocess
import threading
import uuid
import time
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, Any, List


# PowerShell 可执行文件的标准路径
POWERSHELL_PATHS: List[str] = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

# PowerShell Core (pwsh) 的常见路径
PWSH_PATHS: List[str] = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
]


def _find_powershell() -> str:
    """
    查找可用的 PowerShell 可执行文件路径
    
    查找顺序：
    1. 环境变量 WINTERM_POWERSHELL_PATH
    2. Windows PowerShell 标准路径
    3. PowerShell Core 标准路径
    4. PATH 环境变量中的 powershell/pwsh
    
    Returns:
        PowerShell 可执行文件的绝对路径
        
    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    # 1. 检查用户配置的路径
    custom_path = os.environ.get("WINTERM_POWERSHELL_PATH")
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    
    # 2. 检查 Windows PowerShell 标准路径
    for path in POWERSHELL_PATHS:
        if os.path.isfile(path):
            return path
    
    # 3. 检查 PowerShell Core 标准路径
    for path in PWSH_PATHS:
        if os.path.isfile(path):
            return path
    
    # 4. 尝试 PATH（兼容正常环境）
    ps_path = shutil.which("powershell")
    if ps_path:
        return ps_path
    
    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        return pwsh_path
    
    raise FileNotFoundError(
        "PowerShell not found. Please set WINTERM_POWERSHELL_PATH environment variable "
        "or ensure PowerShell is installed in a standard location."
    )


class RunCmdService:
    """
    异步命令执行服务类，管理所有异步命令的执行和状态
    """

    def __init__(self):
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._powershell_path: Optional[str] = None

    def _get_powershell_path(self) -> str:
        """
        获取 PowerShell 路径（带缓存）
        """
        if self._powershell_path is None:
            self._powershell_path = _find_powershell()
        return self._powershell_path

    def run_command(
        self,
        command: str,
        shell_type: str = "powershell",
        timeout: int = 30,
        working_directory: Optional[str] = None,
    ) -> str:
        """
        异步运行命令
        """
        token = str(uuid.uuid4())

        cmd_info = {
            "token": token,
            "command": command,
            "shell_type": shell_type,
            "status": "pending",
            "start_time": datetime.now(),
            "timeout": timeout,
            "working_directory": working_directory,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
            "timeout_occurred": False,
        }

        with self.lock:
            self.commands[token] = cmd_info

        thread = threading.Thread(
            target=self._execute_command,
            args=(token, command, shell_type, timeout, working_directory),
        )
        thread.daemon = True
        thread.start()

        return token

    def _execute_command(
        self,
        token: str,
        command: str,
        shell_type: str,
        timeout: int,
        working_directory: Optional[str],
    ):
        """
        在单独线程中执行命令
        """
        try:
            start_time = time.time()

            with self.lock:
                if token in self.commands:
                    self.commands[token]["status"] = "running"

            encoding = "gbk"

            if shell_type == "powershell":
                # 使用绝对路径调用 PowerShell
                ps_path = self._get_powershell_path()
                cmd_args = [
                    ps_path,  # ← 使用绝对路径
                    "-NoProfile",
                    "-NoLogo",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ]
            else:
                cmd_args = ["cmd", "/c", command]

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_directory,
                encoding=encoding,
                stdin=subprocess.DEVNULL,
            )

            execution_time = time.time() - start_time

            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "exit_code": result.returncode,
                            "execution_time": execution_time,
                        }
                    )

        except FileNotFoundError as e:
            # PowerShell 未找到的特殊处理
            execution_time = time.time() - start_time
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": f"PowerShell not found: {e}",
                            "exit_code": -2,
                            "execution_time": execution_time,
                            "timeout_occurred": False,
                        }
                    )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": f"Command timed out after {timeout} seconds",
                            "exit_code": -1,
                            "execution_time": execution_time,
                            "timeout_occurred": True,
                        }
                    )
        except Exception as e:
            execution_time = time.time() - start_time
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": str(e),
                            "exit_code": -1,
                            "execution_time": execution_time,
                            "timeout_occurred": False,
                        }
                    )

    def query_command_status(self, token: str) -> Dict[str, Any]:
        """
        查询命令执行状态
        """
        with self.lock:
            if token not in self.commands:
                return {
                    "token": token,
                    "status": "not_found",
                    "message": "Token not found",
                }

            cmd_info = self.commands[token].copy()

            if cmd_info["status"] == "running":
                return {"token": cmd_info["token"], "status": "running"}
            elif cmd_info["status"] in ["completed", "pending"]:
                return {
                    "token": cmd_info["token"],
                    "status": cmd_info["status"],
                    "exit_code": cmd_info["exit_code"],
                    "stdout": cmd_info["stdout"],
                    "stderr": cmd_info["stderr"],
                    "execution_time": cmd_info["execution_time"],
                    "timeout_occurred": cmd_info["timeout_occurred"],
                }
            else:
                return cmd_info
```

## 5. 用户配置指南

### 5.1 环境变量配置

如果 PowerShell 安装在非标准位置，用户可以设置环境变量：

```bash
# Windows CMD
set WINTERM_POWERSHELL_PATH=D:\CustomPath\powershell.exe

# Windows PowerShell
$env:WINTERM_POWERSHELL_PATH = "D:\CustomPath\powershell.exe"
```

### 5.2 MCP 配置中设置环境变量

```json
{
  "mcpServers": {
    "winterm": {
      "command": "uvx",
      "args": ["winterm-mcp"],
      "env": {
        "WINTERM_POWERSHELL_PATH": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
      }
    }
  }
}
```

## 6. 测试验证

修改后应验证以下场景：

| 测试场景 | 预期结果 |
|----------|----------|
| 正常环境 + `shell_type: powershell` | ✅ 成功 |
| 沙箱环境 + `shell_type: powershell` | ✅ 成功（使用绝对路径） |
| 自定义 `WINTERM_POWERSHELL_PATH` | ✅ 成功（使用配置路径） |
| PowerShell 不存在 | ❌ 返回明确错误信息 |
| `shell_type: cmd` | ✅ 成功（不受影响） |

## 7. 总结

| 项目 | 说明 |
|------|------|
| 问题根因 | 沙箱环境 PATH 不包含 PowerShell 路径 |
| 解决方案 | 使用绝对路径调用 PowerShell |
| 兼容性 | 支持 Windows PowerShell 和 PowerShell Core |
| 可配置性 | 支持 `WINTERM_POWERSHELL_PATH` 环境变量 |
| 向后兼容 | 保持原有 API 不变 |

---

## 附录：相关文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/winterm_mcp/service.py` | 修改 | 添加 PowerShell 路径探测逻辑 |
| `README.md` | 修改 | 添加环境变量配置说明 |
| `docs/powershell_sandbox_solution.md` | 新增 | 本文档 |
