# Python 路径环境变量支持实施计划

**更新日期**: 2026-01-16
**版本**: 1.0

## 背景分析

当前问题：
- `runcmd_mcp_standalone` 和 `winterm_mcp_standalone` 执行 Python 命令时，可能使用 uv 创建的 python.exe
- 需要通过环境变量指定系统 Python 路径，确保使用正确的 Python

参考设计：
- `winterm_mcp_standalone` 已有 `WINTERM_POWERSHELL_PATH` 环境变量机制，可复用此模式

---

## 实施计划

### 1. runcmd_mcp_standalone 修改

**文件**: `src/runcmd_mcp/service.py`

**修改点**:
- 添加环境变量常量 `ENV_PYTHON_PATH = "RUNCMD_PYTHON_PATH"`
- 添加 `_find_python()` 函数（可选，用于验证路径有效性）
- 修改 `_execute_command()` 方法：
  - 读取 `RUNCMD_PYTHON_PATH` 环境变量
  - 如果存在，在 `subprocess.run()` 的 `env` 参数中设置 `PATH` 环境变量
  - 将指定的 Python 路径添加到 PATH 的最前面

**文件**: `src/runcmd_mcp/server.py` (可选)

**修改点**:
- 在 `get_version_tool()` 中添加 Python 路径信息展示（如果需要）

---

### 2. winterm_mcp_standalone 修改

**文件**: `src/winterm_mcp/service.py`

**修改点**:
- 添加环境变量常量 `ENV_PYTHON_PATH = "WINTERM_PYTHON_PATH"`
- 添加 `_find_python()` 函数（可选，用于验证路径有效性）
- 修改 `_execute_command()` 方法：
  - 读取 `WINTERM_PYTHON_PATH` 环境变量
  - 如果存在，在 `subprocess.run()` 的 `env` 参数中设置 `PATH` 环境变量
  - 将指定的 Python 路径添加到 PATH 的最前面

**文件**: `src/winterm_mcp/server.py`

**修改点**:
- 在 `get_version_tool()` 的 `env` 字段中添加 `WINTERM_PYTHON_PATH` 信息

---

## 技术细节

### 环境变量设置策略

```python
# 伪代码示例
python_path = os.environ.get(ENV_PYTHON_PATH)
if python_path and os.path.isfile(python_path):
    # 创建新的环境变量字典
    env = os.environ.copy()
    # 将 Python 路径添加到 PATH 的最前面
    python_dir = os.path.dirname(python_path)
    env["PATH"] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"
    
    subprocess.run(..., env=env, ...)
```

### 优先级设计

1. 用户配置的环境变量（最高优先级）
2. 系统默认 PATH

### 日志记录

- 记录检测到的 Python 路径
- 记录 PATH 环境变量的修改
- 路径不存在时记录警告

---

## 测试验证计划

### 1. 功能测试
- 设置环境变量后执行 `python --version`
- 验证使用的是指定的 Python 路径

### 2. 边界测试
- 环境变量未设置时的行为
- 环境变量路径不存在时的行为
- 环境变量路径无效时的行为

### 3. 兼容性测试
- 确保不影响其他命令的执行
- 验证 PowerShell 和 cmd 模式都正常工作

---

## 文档更新（可选）

如果需要，可以在 README 中添加环境变量说明：
- `RUNCMD_PYTHON_PATH`: 指定 runcmd 使用的 Python 路径
- `WINTERM_PYTHON_PATH`: 指定 winterm 使用的 Python 路径

---

## 风险评估

- **低风险**: 修改仅影响环境变量设置，不改变核心执行逻辑
- **向后兼容**: 环境变量未设置时，行为与之前完全一致
