# pkg-publisher

**更新日期**: 2026-01-16
**版本**: 0.1.0

Python Package Publisher MCP Service - 专门用于构建和发布 Python 包到 PyPI 的 MCP 工具。

## 功能特性

- **包构建**: 自动构建 Python 包（.whl 和 .tar.gz）
- **包发布**: 一键发布到 PyPI 或 TestPyPI
- **包验证**: 验证包是否符合 PyPI 规范
- **包信息查询**: 查询 PyPI 上的包信息
- **环境变量支持**: 从环境变量读取 API Token
- **自动化友好**: 适合 CI/CD 集成

## 安装

```bash
cd pkg_publisher_standalone
pip install -e .
```

## 使用方法

### MCP 配置

在 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "pkg-publisher": {
      "command": "uvx",
      "args": [
        "pkg-publisher"
      ],
      "env": {
        "PYPI_API_TOKEN": "your-pypi-api-token"
      }
    }
  }
}
```

### 环境配置

#### PyPI API Token 配置

**方式一：系统环境变量**

```bash
# Windows CMD
set PYPI_API_TOKEN=pypi-xxx...

# Windows PowerShell
$env:PYPI_API_TOKEN = "pypi-xxx..."

# Linux/Mac
export PYPI_API_TOKEN="pypi-xxx..."
```

**方式二：MCP 配置**

```json
{
  "mcpServers": {
    "pkg-publisher": {
      "command": "uvx",
      "args": ["pkg-publisher"],
      "env": {
        "PYPI_API_TOKEN": "pypi-xxx...",
        "TEST_PYPI_API_TOKEN": "pypi-xxx..."
      }
    }
  }
}
```

#### 环境变量说明

| 变量名 | 说明 | 必填 | 示例 |
|--------|------|------|------|
| `PYPI_API_TOKEN` | PyPI API Token | 发布到 PyPI 时必填 | `pypi-xxx...` |
| `TEST_PYPI_API_TOKEN` | TestPyPI API Token | 发布到 TestPyPI 时必填 | `pypi-xxx...` |
| `PKG_PUBLISHER_PYTHON_PATH` | 指定使用的 Python 可执行文件路径 | 否 | `C:\Python39\python.exe` |
| `PKG_PUBLISHER_LOG_LEVEL` | 日志级别 | 否 | `DEBUG/INFO/WARNING/ERROR` |
| `PKG_PUBLISHER_LOG_FILE` | 自定义日志文件路径 | 否 | `/path/to/log.txt` |

### 工具接口

#### build_package

构建 Python 包。

**参数**:
- `project_path` (string, optional): 项目路径，默认当前目录
- `clean` (boolean, optional): 是否清理旧的构建产物，默认 true

**返回**:
```json
{
  "success": true,
  "output": "build output",
  "error": "",
  "dist_files": [
    "/path/to/package-0.1.0-py3-none-any.whl",
    "/path/to/package-0.1.0.tar.gz"
  ],
  "project_path": "/path/to/project"
}
```

#### publish_package

发布 Python 包到 PyPI。

**参数**:
- `package_path` (string, optional): 包文件路径，默认 `dist/*`
- `repository` (string, optional): 仓库名称，`pypi` 或 `testpypi`，默认 `pypi`
- `skip_existing` (boolean, optional): 是否跳过已存在的版本，默认 false
- `project_path` (string, optional): 项目路径，用于查找 dist 目录

**返回**:
```json
{
  "success": true,
  "output": "upload output",
  "error": "",
  "repository": "pypi",
  "package_files": [
    "/path/to/package-0.1.0-py3-none-any.whl",
    "/path/to/package-0.1.0.tar.gz"
  ]
}
```

#### validate_package

验证 Python 包是否符合 PyPI 规范。

**参数**:
- `package_path` (string): 包文件路径

**返回**:
```json
{
  "success": true,
  "output": "validation output",
  "error": "",
  "package_path": "/path/to/package-0.1.0-py3-none-any.whl"
}
```

#### get_package_info

查询 PyPI 上的包信息。

**参数**:
- `package_name` (string): 包名
- `version` (string, optional): 版本号
- `repository` (string, optional): 仓库名称，`pypi` 或 `testpypi`，默认 `pypi`

**返回**:
```json
{
  "success": true,
  "package_name": "package-name",
  "version": "0.1.0",
  "info": {
    "name": "package-name",
    "version": "0.1.0",
    "summary": "Package description",
    ...
  },
  "error": null
}
```

## 使用示例

### 构建并发布

```python
# 构建包
build_result = build_package()
if build_result["success"]:
    print(f"Built: {build_result['dist_files']}")

# 发布到 PyPI
publish_result = publish_package(repository="pypi")
if publish_result["success"]:
    print("Published successfully!")
```

### 发布到 TestPyPI

```python
# 构建包
build_result = build_package()

# 发布到 TestPyPI
publish_result = publish_package(
    repository="testpypi",
    skip_existing=True
)
```

### 验证包

```python
# 验证包
validate_result = validate_package("dist/package-0.1.0-py3-none-any.whl")
if validate_result["success"]:
    print("Package is valid")
```

### 查询包信息

```python
# 查询包信息
info_result = get_package_info("requests")
if info_result["success"]:
    print(f"Latest version: {info_result['info']['info']['version']}")

# 查询特定版本
info_result = get_package_info("requests", version="2.31.0")
```

## 技术架构

- **框架**: FastMCP
- **构建工具**: python-build
- **发布工具**: twine
- **HTTP 客户端**: requests
- **平台**: 跨平台

## 安全说明

- API Token 仅从环境变量读取，不记录到日志
- 支持临时 Token（有效期限制）
- 不在 MCP 响应中返回 Token
- 建议使用 PyPI 的 Trusted Publishers 或 Token API

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。
