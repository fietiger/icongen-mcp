# winterm-mcp PowerShell 沙箱环境适配实施方案

**文档日期**: 2026-01-16  
**版本**: 1.0.0  
**状态**: 待实施

---

## 1. 实施目标

解决 winterm-mcp 在受限沙箱环境中无法执行 PowerShell 命令的问题，通过使用绝对路径调用 PowerShell 可执行文件，绕过 PATH 环境变量的限制。

### 1.1 成功标准

| 标准 | 描述 |
|------|------|
| 功能正确性 | 在沙箱环境中 `shell_type: powershell` 能正常执行 |
| 向后兼容 | 在正常环境中行为不变，API 接口不变 |
| 可配置性 | 支持用户自定义 PowerShell 路径 |
| 错误处理 | PowerShell 未找到时返回明确错误信息 |

---

## 2. 变更范围

### 2.1 文件变更清单

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `src/winterm_mcp/service.py` | 修改 | 核心逻辑变更 |
| `README.md` | 修改 | 添加配置说明 |
| `pyproject.toml` | 修改 | 版本号更新 |

### 2.2 不变更的文件

| 文件路径 | 说明 |
|----------|------|
| `src/winterm_mcp/server.py` | API 接口不变 |
| `src/winterm_mcp/__init__.py` | 无需变更 |
| `src/winterm_mcp/__main__.py` | 无需变更 |

---

## 3. 详细实施步骤

### 3.1 步骤一：修改 service.py

#### 3.1.1 添加导入语句

**位置**: 文件顶部，现有 import 语句之后

**当前代码**:
```python
import subprocess
import threading
import uuid
import time
from datetime import datetime
from typing import Dict, Optional, Any
```

**修改为**:
```python
import subprocess
import threading
import uuid
import time
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, Any, List
```

#### 3.1.2 添加 PowerShell 路径常量和探测函数

**位置**: import 语句之后，`RunCmdService` 类定义之前

**新增代码**:
```python
# PowerShell 可执行文件的标准路径（按优先级排序）
POWERSHELL_PATHS: List[str] = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

# PowerShell Core (pwsh) 的常见路径
PWSH_PATHS: List[str] = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
]

# 环境变量名称
ENV_POWERSHELL_PATH = "WINTERM_POWERSHELL_PATH"


def _find_powershell() -> str:
    """
    查找可用的 PowerShell 可执行文件路径
    
    查找顺序：
    1. 环境变量 WINTERM_POWERSHELL_PATH（用户自定义）
    2. Windows PowerShell 标准路径
    3. PowerShell Core 标准路径
    4. PATH 环境变量中的 powershell/pwsh（兼容正常环境）
    
    Returns:
        PowerShell 可执行文件的绝对路径
        
    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    # 1. 检查用户配置的环境变量
    custom_path = os.environ.get(ENV_POWERSHELL_PATH)
    if custom_path:
        if os.path.isfile(custom_path):
            return custom_path
        # 用户配置了但路径无效，记录警告但继续查找
    
    # 2. 检查 Windows PowerShell 标准路径
    for path in POWERSHELL_PATHS:
        if os.path.isfile(path):
            return path
    
    # 3. 检查 PowerShell Core 标准路径
    for path in PWSH_PATHS:
        if os.path.isfile(path):
            return path
    
    # 4. 尝试 PATH 环境变量（兼容正常环境）
    ps_path = shutil.which("powershell")
    if ps_path:
        return ps_path
    
    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        return pwsh_path
    
    # 所有方法都失败
    checked_paths = POWERSHELL_PATHS + PWSH_PATHS
    raise FileNotFoundError(
        f"PowerShell not found. "
        f"Set {ENV_POWERSHELL_PATH} environment variable or ensure PowerShell is installed. "
        f"Checked paths: {', '.join(checked_paths)}"
    )
```

#### 3.1.3 修改 RunCmdService 类

**变更 1**: 添加 `_powershell_path` 属性到 `__init__` 方法

**当前代码**:
```python
def __init__(self):
    self.commands: Dict[str, Dict[str, Any]] = {}
    self.lock = threading.Lock()
```

**修改为**:
```python
def __init__(self):
    self.commands: Dict[str, Dict[str, Any]] = {}
    self.lock = threading.Lock()
    self._powershell_path: Optional[str] = None  # 缓存 PowerShell 路径
```

**变更 2**: 添加 `_get_powershell_path` 方法

**位置**: `__init__` 方法之后，`run_command` 方法之前

**新增代码**:
```python
def _get_powershell_path(self) -> str:
    """
    获取 PowerShell 可执行文件路径（带缓存）
    
    首次调用时查找并缓存路径，后续调用直接返回缓存值。
    
    Returns:
        PowerShell 可执行文件的绝对路径
        
    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    if self._powershell_path is None:
        self._powershell_path = _find_powershell()
    return self._powershell_path
```

**变更 3**: 修改 `_execute_command` 方法中的 PowerShell 调用

**当前代码** (第 79-90 行附近):
```python
if shell_type == "powershell":
    # 添加 -ExecutionPolicy Bypass 避免执行策略阻塞
    # 添加 -NoLogo 减少启动输出
    cmd_args = [
        "powershell",
        "-NoProfile",
        "-NoLogo",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]
```

**修改为**:
```python
if shell_type == "powershell":
    # 使用绝对路径调用 PowerShell，避免 PATH 环境变量限制
    ps_path = self._get_powershell_path()
    cmd_args = [
        ps_path,  # 使用绝对路径
        "-NoProfile",
        "-NoLogo",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]
```

**变更 4**: 添加 FileNotFoundError 异常处理

**当前代码** (异常处理部分):
```python
except subprocess.TimeoutExpired:
    execution_time = time.time() - start_time
    # ... 超时处理代码 ...
except Exception as e:
    execution_time = time.time() - start_time
    # ... 通用异常处理代码 ...
```

**修改为**:
```python
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
                    "exit_code": -2,  # 使用 -2 区分于超时的 -1
                    "execution_time": execution_time,
                    "timeout_occurred": False,
                }
            )
except subprocess.TimeoutExpired:
    execution_time = time.time() - start_time
    # ... 超时处理代码保持不变 ...
except Exception as e:
    execution_time = time.time() - start_time
    # ... 通用异常处理代码保持不变 ...
```

---

### 3.2 步骤二：更新 README.md

**位置**: 在 "使用方法" 或 "MCP 配置" 章节之后添加新章节

**新增内容**:
```markdown
## 环境配置

### PowerShell 路径配置

在某些受限环境（如沙箱环境）中，系统 PATH 可能不包含 PowerShell 路径。winterm-mcp 会自动探测以下位置：

1. `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
2. `C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`
3. `C:\Program Files\PowerShell\7\pwsh.exe`（PowerShell Core）
4. `C:\Program Files (x86)\PowerShell\7\pwsh.exe`

如果 PowerShell 安装在非标准位置，可通过环境变量指定：

#### 方式一：系统环境变量

```bash
# Windows CMD
set WINTERM_POWERSHELL_PATH=D:\CustomPath\powershell.exe

# Windows PowerShell
$env:WINTERM_POWERSHELL_PATH = "D:\CustomPath\powershell.exe"
```

#### 方式二：MCP 配置

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
```

---

### 3.3 步骤三：更新版本号

**文件**: `pyproject.toml`

**当前版本**: `0.1.3`

**新版本**: `0.1.4`

**变更说明**: 在 CHANGELOG 或提交信息中记录：
- 修复：沙箱环境中 PowerShell 命令执行失败的问题
- 新增：支持 `WINTERM_POWERSHELL_PATH` 环境变量配置

---

## 4. 完整修改后的 service.py

以下是完整的修改后文件内容，可直接替换现有文件：


```python
"""
winterm服务模块 - 异步执行Windows终端命令服务

变更历史:
- v0.1.4: 添加 PowerShell 绝对路径支持，解决沙箱环境兼容性问题
"""

import subprocess
import threading
import uuid
import time
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, Any, List


# PowerShell 可执行文件的标准路径（按优先级排序）
POWERSHELL_PATHS: List[str] = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

# PowerShell Core (pwsh) 的常见路径
PWSH_PATHS: List[str] = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
]

# 环境变量名称
ENV_POWERSHELL_PATH = "WINTERM_POWERSHELL_PATH"


def _find_powershell() -> str:
    """
    查找可用的 PowerShell 可执行文件路径
    
    查找顺序：
    1. 环境变量 WINTERM_POWERSHELL_PATH（用户自定义）
    2. Windows PowerShell 标准路径
    3. PowerShell Core 标准路径
    4. PATH 环境变量中的 powershell/pwsh（兼容正常环境）
    
    Returns:
        PowerShell 可执行文件的绝对路径
        
    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    # 1. 检查用户配置的环境变量
    custom_path = os.environ.get(ENV_POWERSHELL_PATH)
    if custom_path:
        if os.path.isfile(custom_path):
            return custom_path
        # 用户配置了但路径无效，记录警告但继续查找
    
    # 2. 检查 Windows PowerShell 标准路径
    for path in POWERSHELL_PATHS:
        if os.path.isfile(path):
            return path
    
    # 3. 检查 PowerShell Core 标准路径
    for path in PWSH_PATHS:
        if os.path.isfile(path):
            return path
    
    # 4. 尝试 PATH 环境变量（兼容正常环境）
    ps_path = shutil.which("powershell")
    if ps_path:
        return ps_path
    
    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        return pwsh_path
    
    # 所有方法都失败
    checked_paths = POWERSHELL_PATHS + PWSH_PATHS
    raise FileNotFoundError(
        f"PowerShell not found. "
        f"Set {ENV_POWERSHELL_PATH} environment variable or ensure PowerShell is installed. "
        f"Checked paths: {', '.join(checked_paths)}"
    )


class RunCmdService:
    """
    异步命令执行服务类，管理所有异步命令的执行和状态
    """

    def __init__(self):
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._powershell_path: Optional[str] = None  # 缓存 PowerShell 路径

    def _get_powershell_path(self) -> str:
        """
        获取 PowerShell 可执行文件路径（带缓存）
        
        首次调用时查找并缓存路径，后续调用直接返回缓存值。
        
        Returns:
            PowerShell 可执行文件的绝对路径
            
        Raises:
            FileNotFoundError: 如果找不到 PowerShell
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

        Args:
            command: 要执行的命令
            shell_type: Shell 类型 (powershell 或 cmd)
            timeout: 超时时间（秒）
            working_directory: 工作目录

        Returns:
            命令执行的token
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
                # 使用绝对路径调用 PowerShell，避免 PATH 环境变量限制
                ps_path = self._get_powershell_path()
                cmd_args = [
                    ps_path,  # 使用绝对路径
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
                stdin=subprocess.DEVNULL,  # 防止等待输入导致挂起
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
                            "exit_code": -2,  # 使用 -2 区分于超时的 -1
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
                            "stderr": (f"Command timed out after {timeout} seconds"),
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

        Args:
            token: 命令的token

        Returns:
            包含命令状态的字典
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

---

## 5. 测试计划

### 5.1 单元测试用例

| 测试ID | 测试场景 | 输入 | 预期结果 |
|--------|----------|------|----------|
| T01 | 正常环境 PowerShell | `Get-Date`, `shell_type=powershell` | 成功返回日期 |
| T02 | 正常环境 Cmd | `dir`, `shell_type=cmd` | 成功返回目录列表 |
| T03 | 自定义环境变量 | 设置 `WINTERM_POWERSHELL_PATH` | 使用指定路径 |
| T04 | 无效环境变量路径 | 设置无效路径 | 回退到标准路径 |
| T05 | PowerShell 不存在 | 所有路径都无效 | 返回 `exit_code=-2` |
| T06 | 中文输出 | `echo 你好` | 正确显示中文 |
| T07 | 超时处理 | 长时间命令 | 返回 `timeout_occurred=true` |

### 5.2 集成测试场景

| 场景 | 测试方法 | 验证点 |
|------|----------|--------|
| 沙箱环境模拟 | 清空 PATH 后测试 | PowerShell 仍可执行 |
| MCP 客户端集成 | 通过 MCP 协议调用 | 完整流程正常 |
| 并发执行 | 同时提交多个命令 | 线程安全，无数据竞争 |

### 5.3 手动测试命令

```python
# 测试 1: 基本 PowerShell 命令
run_command("Get-Date")

# 测试 2: 带参数的 PowerShell 命令
run_command('Get-Date -Format "yyyy-MM-dd HH:mm:ss"')

# 测试 3: 中文输出
run_command('Write-Output "你好世界"')

# 测试 4: Cmd 命令（确保不受影响）
run_command("dir", shell_type="cmd")

# 测试 5: 查询状态
query_command_status("<token>")
```

---

## 6. 回滚方案

如果新版本出现问题，可通过以下方式回滚：

### 6.1 代码回滚

```bash
# 恢复到上一版本
git checkout HEAD~1 -- src/winterm_mcp/service.py
```

### 6.2 版本回滚

```bash
# 安装上一版本
pip install winterm-mcp==0.1.3
```

### 6.3 临时解决方案

用户可在 MCP 配置中使用 cmd + 完整路径作为临时方案：

```json
{
  "command": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -Command \"Get-Date\"",
  "shell_type": "cmd"
}
```

---

## 7. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 标准路径不存在 | 低 | 中 | 多路径探测 + 环境变量配置 |
| 路径缓存导致问题 | 低 | 低 | 重启服务可刷新缓存 |
| 编码问题 | 低 | 中 | 保持现有编码处理逻辑 |
| 性能影响 | 极低 | 低 | 路径缓存避免重复探测 |

---

## 8. 实施检查清单

- [ ] 修改 `service.py` 添加导入语句
- [ ] 修改 `service.py` 添加路径常量和探测函数
- [ ] 修改 `service.py` 更新 `RunCmdService.__init__`
- [ ] 修改 `service.py` 添加 `_get_powershell_path` 方法
- [ ] 修改 `service.py` 更新 `_execute_command` 方法
- [ ] 修改 `service.py` 添加 `FileNotFoundError` 异常处理
- [ ] 更新 `README.md` 添加环境配置说明
- [ ] 更新 `pyproject.toml` 版本号
- [ ] 执行单元测试
- [ ] 执行集成测试
- [ ] 在沙箱环境中验证
- [ ] 提交代码并创建 Release

---

## 附录 A: 代码差异对比

### service.py 变更摘要

```diff
 import subprocess
 import threading
 import uuid
 import time
+import os
+import shutil
 from datetime import datetime
-from typing import Dict, Optional, Any
+from typing import Dict, Optional, Any, List


+# PowerShell 可执行文件的标准路径
+POWERSHELL_PATHS: List[str] = [...]
+PWSH_PATHS: List[str] = [...]
+ENV_POWERSHELL_PATH = "WINTERM_POWERSHELL_PATH"
+
+def _find_powershell() -> str:
+    ...
+

 class RunCmdService:
     def __init__(self):
         self.commands: Dict[str, Dict[str, Any]] = {}
         self.lock = threading.Lock()
+        self._powershell_path: Optional[str] = None

+    def _get_powershell_path(self) -> str:
+        ...

     def _execute_command(...):
         ...
         if shell_type == "powershell":
+            ps_path = self._get_powershell_path()
             cmd_args = [
-                "powershell",
+                ps_path,
                 ...
             ]
         ...
+        except FileNotFoundError as e:
+            ...
```

---

## 附录 B: 相关文档

| 文档 | 说明 |
|------|------|
| `winterm_powershell_issue.md` | 原始问题记录 |
| `powershell_sandbox_solution.md` | 方案分析文档 |
| `SDD.md` | 技术设计文档 |
| `README.md` | 用户使用文档 |
