# pkg-publisher 功能需求说明书

**更新日期**: 2026-01-16
**版本**: 1.0

## 1. 概述

### 1.1 项目背景

在 Python 包开发流程中，构建和发布到 PyPI 是一个常见但繁琐的过程。当前流程需要手动执行多个命令，并需要手动配置 API Token，缺乏自动化支持。

### 1.2 项目目标

提供 Python 包构建和发布的 MCP 服务，支持从环境变量读取 PyPI API Token，实现自动化发布，简化 CI/CD 集成。

### 1.3 目标用户

- Python 包开发者
- DevOps 工程师
- 需要自动化发布流程的团队

## 2. 功能需求

### 2.1 构建功能

#### 2.1.1 build_package()

**描述**: 构建 Python 包

**输入参数**:
- `project_path` (string, optional): 项目路径，默认当前目录
- `clean` (boolean, optional): 是否清理旧的构建产物，默认 true

**输出**:
```json
{
  "success": boolean,
  "output": string,
  "error": string,
  "dist_files": string[],
  "project_path": string
}
```

**行为**:
- 执行 `python -m build` 命令
- 清理旧的构建产物（build/, dist/, *.egg-info）
- 返回构建产物路径列表（.whl, .tar.gz）
- 支持自定义项目路径

**异常处理**:
- 项目路径不存在 → 返回错误信息
- 构建失败 → 返回构建日志和错误信息
- 缺少 pyproject.toml → 返回明确错误提示

### 2.2 发布功能

#### 2.2.1 publish_package()

**描述**: 发布 Python 包到 PyPI

**输入参数**:
- `package_path` (string, optional): 包文件路径，默认 `dist/*`
- `repository` (string, optional): 仓库名称，`pypi` 或 `testpypi`，默认 `pypi`
- `skip_existing` (boolean, optional): 是否跳过已存在版本，默认 false
- `project_path` (string, optional): 项目路径，用于查找 dist 目录

**输出**:
```json
{
  "success": boolean,
  "output": string,
  "error": string,
  "repository": string,
  "package_files": string[]
}
```

**行为**:
- 从环境变量 `PYPI_API_TOKEN` 或 `TEST_PYPI_API_TOKEN` 读取 API Token
- 执行 `twine upload` 命令
- 支持发布到 PyPI 或 TestPyPI
- 返回发布状态和结果

**异常处理**:
- API Token 未设置 → 返回明确错误提示
- 认证失败（403）→ 返回认证失败提示
- 版本已存在 → 返回版本冲突信息（可选 skip_existing）
- 网络错误 → 返回网络错误信息

### 2.3 验证功能

#### 2.3.1 validate_package()

**描述**: 验证 Python 包是否符合 PyPI 规范

**输入参数**:
- `package_path` (string): 包文件路径

**输出**:
```json
{
  "success": boolean,
  "output": string,
  "error": string,
  "package_path": string
}
```

**行为**:
- 执行 `twine check` 命令
- 验证包的元数据和结构
- 返回验证结果

**异常处理**:
- 文件不存在 → 返回文件未找到错误
- 验证失败 → 返回验证错误信息

### 2.4 查询功能

#### 2.4.1 get_package_info()

**描述**: 查询 PyPI 上的包信息

**输入参数**:
- `package_name` (string): 包名
- `version` (string, optional): 版本号
- `repository` (string, optional): 仓库名称，`pypi` 或 `testpypi`，默认 `pypi`

**输出**:
```json
{
  "success": boolean,
  "package_name": string,
  "version": string | null,
  "info": object,
  "error": string | null
}
```

**行为**:
- 查询 PyPI API
- 返回包信息（版本列表、发布时间、下载量）
- 支持查询特定版本

**异常处理**:
- 包不存在 → 返回包未找到错误
- 网络错误 → 返回网络错误信息
- API 限流 → 返回限流提示

## 3. 环境变量配置

| 变量名 | 说明 | 必填 | 示例 |
|--------|------|------|------|
| `PYPI_API_TOKEN` | PyPI API Token | 发布到 PyPI 时必填 | `pypi-xxx...` |
| `TEST_PYPI_API_TOKEN` | TestPyPI API Token | 发布到 TestPyPI 时必填 | `pypi-xxx...` |
| `PKG_PUBLISHER_LOG_LEVEL` | 日志级别 | 否 | `DEBUG/INFO/WARNING/ERROR` |
| `PKG_PUBLISHER_LOG_FILE` | 自定义日志文件路径 | 否 | `/path/to/log.txt` |

## 4. 技术实现要点

### 4.1 依赖

```toml
dependencies = [
    "fastmcp>=0.1.0",
    "pydantic>=2.0.0",
    "build>=0.10.0",
    "twine>=4.0.0",
    "requests>=2.31.0",
]
```

### 4.2 Token 读取逻辑

```python
import os

def get_api_token(repository: str = "pypi") -> str:
    if repository == "testpypi":
        token = os.getenv("TEST_PYPI_API_TOKEN")
        env_var_name = "TEST_PYPI_API_TOKEN"
    else:
        token = os.getenv("PYPI_API_TOKEN")
        env_var_name = "PYPI_API_TOKEN"
    
    if not token:
        raise ValueError(
            f"{env_var_name} not found in environment variables. "
            f"Please set the {env_var_name} environment variable."
        )
    return token
```

### 4.3 发布命令

```bash
twine upload dist/* \
  --username __token__ \
  --password $PYPI_API_TOKEN \
  --repository https://upload.pypi.org/legacy/
```

### 4.4 日志配置

- 控制台输出（stderr）
- 文件输出：`%TEMP%/pkg-publisher.log` 或 `/tmp/pkg-publisher.log`
- 支持环境变量配置日志级别和文件路径

## 5. 使用示例

### 5.1 构建并发布

```json
{
  "tool": "pkg-publisher",
  "method": "build_package",
  "params": {
    "project_path": "/path/to/project",
    "clean": true
  }
}
```

```json
{
  "tool": "pkg-publisher",
  "method": "publish_package",
  "params": {
    "package_path": "dist/*.whl",
    "repository": "pypi"
  }
}
```

### 5.2 仅发布

```json
{
  "tool": "pkg-publisher",
  "method": "publish_package",
  "params": {
    "package_path": "dist/*.whl",
    "repository": "testpypi",
    "skip_existing": true
  }
}
```

### 5.3 验证包

```json
{
  "tool": "pkg-publisher",
  "method": "validate_package",
  "params": {
    "package_path": "dist/package-0.1.0-py3-none-any.whl"
  }
}
```

### 5.4 查询包信息

```json
{
  "tool": "pkg-publisher",
  "method": "get_package_info",
  "params": {
    "package_name": "requests",
    "version": "2.31.0",
    "repository": "pypi"
  }
}
```

## 6. 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| `PYPI_API_TOKEN` 未设置 | 返回明确错误提示，说明需要设置环境变量 |
| 构建失败 | 返回构建日志和错误信息 |
| 发布失败（403） | 返回认证失败提示，检查 API Token |
| 版本已存在 | 返回版本冲突信息（可选 skip_existing） |
| 网络错误 | 返回网络错误信息，建议重试 |
| 文件不存在 | 返回文件未找到错误，检查路径 |

## 7. 安全要求

- API Token 仅从环境变量读取，不记录到日志
- 支持临时 Token（有效期限制）
- 不在 MCP 响应中返回 Token
- 建议使用 PyPI 的 Trusted Publishers 或 Token API
- 日志中 Token 显示为 `***`

## 8. 非功能需求

### 8.1 性能

- 构建时间：取决于项目大小
- 发布时间：取决于网络速度和包大小
- 查询响应：< 5 秒

### 8.2 可靠性

- 支持重试机制（可选）
- 超时控制（构建、发布、查询）
- 错误恢复（清理临时文件）

### 8.3 可维护性

- 清晰的日志输出
- 详细的错误信息
- 完善的文档

## 9. 未来扩展

- 支持多个仓库配置
- 支持版本自动递增
- 支持 Git tag 自动创建
- 支持 Changelog 自动生成
- 支持发布后通知（邮件、Slack 等）

## 10. 附录

### 10.1 参考资料

- [PyPI 文档](https://pypi.org/help/)
- [Twine 文档](https://twine.readthedocs.io/)
- [Python 打包指南](https://packaging.python.org/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)

### 10.2 术语表

- **PyPI**: Python Package Index，Python 包索引
- **TestPyPI**: PyPI 的测试环境
- **MCP**: Model Context Protocol，模型上下文协议
- **API Token**: PyPI 认证令牌
- **whl**: Python Wheel 包格式
- **sdist**: Source Distribution，源码分发包（.tar.gz）
