from __future__ import annotations

from typing import Annotated, Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from .service import PkgPublisherService, get_version, setup_logging, __version__
from pydantic import Field

ProjectPathStr = Annotated[
    Optional[str],
    Field(
        description="项目路径（可选，默认为当前目录）",
        default=None,
        max_length=1000,
    ),
]

PackagePathStr = Annotated[
    Optional[str],
    Field(
        description="包文件路径（可选，默认为 dist/*）",
        default=None,
        max_length=1000,
    ),
]

RepositoryStr = Annotated[
    str,
    Field(
        description="仓库名称 (pypi 或 testpypi)，默认 pypi",
        pattern="^(pypi|testpypi)$",
    ),
]

PackageNameStr = Annotated[
    str,
    Field(
        description="包名",
        min_length=1,
        max_length=100,
    ),
]

VersionStr = Annotated[
    Optional[str],
    Field(
        description="版本号（可选）",
        default=None,
        max_length=50,
    ),
]

SkipExistingBool = Annotated[
    bool,
    Field(
        description="是否跳过已存在的版本，默认 False",
        default=False,
    ),
]

CleanBool = Annotated[
    bool,
    Field(
        description="是否清理旧的构建产物，默认 True",
        default=True,
    ),
]

UsePtyBool = Annotated[
    bool,
    Field(
        description="是否使用 PTY 模式（默认 True，解决进度条显示问题）",
        default=True,
    ),
]

app = FastMCP("pkg-publisher")

_service: Optional[PkgPublisherService] = None


def init_service(service: PkgPublisherService) -> None:
    global _service
    _service = service


def _svc() -> PkgPublisherService:
    if _service is None:
        raise RuntimeError(
            "Service not initialized. "
            "Call init_service() before running the server."
        )
    return _service


@app.tool(
    name="build_package",
    description=(
        "异步构建 Python 包，立即返回 token。"
        "包将在后台构建，可通过 query_task_status 查询结果。"
        "支持 PTY 模式以正确显示构建进度。"
    ),
    annotations={
        "title": "异步包构建器",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def build_package(
    project_path: ProjectPathStr = None,
    clean: CleanBool = True,
    use_pty: UsePtyBool = True,
) -> Dict[str, Any]:
    """
    异步构建 Python 包

    Args:
        project_path: 项目路径（可选，默认为当前目录）
        clean: 是否清理旧的构建产物，默认 True
        use_pty: 是否使用 PTY 模式，默认 True

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().build_package(project_path, clean, use_pty)
        return {"token": token, "status": "pending", "task_type": "build_package", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="publish_package",
    description=(
        "异步发布 Python 包到 PyPI，立即返回 token。"
        "包将在后台发布，可通过 query_task_status 查询结果。"
        "使用 PTY 模式解决 twine 进度条显示问题。"
        "认证信息通过 .pypirc 文件或环境变量配置。"
    ),
    annotations={
        "title": "异步包发布器",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def publish_package(
    package_path: PackagePathStr = None,
    repository: RepositoryStr = "pypi",
    skip_existing: SkipExistingBool = False,
    project_path: ProjectPathStr = None,
    use_pty: UsePtyBool = True,
) -> Dict[str, Any]:
    """
    异步发布 Python 包到 PyPI

    Args:
        package_path: 包文件路径（可选，默认为 dist/*）
        repository: 仓库名称 (pypi 或 testpypi)，默认 pypi
        skip_existing: 是否跳过已存在的版本，默认 False
        project_path: 项目路径，用于查找 dist 目录
        use_pty: 是否使用 PTY 模式，默认 True

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().publish_package(package_path, repository, skip_existing, project_path, use_pty)
        return {"token": token, "status": "pending", "task_type": "publish_package", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="validate_package",
    description=(
        "异步验证 Python 包是否符合 PyPI 规范，立即返回 token。"
        "可通过 query_task_status 查询验证结果。"
    ),
    annotations={
        "title": "异步包验证器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def validate_package(
    package_path: str,
    use_pty: UsePtyBool = True,
) -> Dict[str, Any]:
    """
    异步验证 Python 包

    Args:
        package_path: 包文件路径
        use_pty: 是否使用 PTY 模式，默认 True

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().validate_package(package_path, use_pty)
        return {"token": token, "status": "pending", "task_type": "validate_package", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="get_package_info",
    description=(
        "异步查询 PyPI 上的包信息，立即返回 token。"
        "可通过 query_task_status 查询查询结果。"
    ),
    annotations={
        "title": "异步包信息查询器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
def get_package_info(
    package_name: PackageNameStr,
    version: VersionStr = None,
    repository: RepositoryStr = "pypi",
) -> Dict[str, Any]:
    """
    异步获取 Python 包信息

    Args:
        package_name: 包名
        version: 版本号（可选）
        repository: 仓库名称 (pypi 或 testpypi)，默认 pypi

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().get_package_info(package_name, version, repository)
        return {"token": token, "status": "pending", "task_type": "get_package_info", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


StdoutOffsetInt = Annotated[
    int,
    Field(
        description="stdout 输出偏移量（默认 0，返回全部）",
        default=0,
        ge=0,
    ),
]

StderrOffsetInt = Annotated[
    int,
    Field(
        description="stderr 输出偏移量（默认 0，返回全部）",
        default=0,
        ge=0,
    ),
]


@app.tool(
    name="query_task_status",
    description="查询异步任务执行状态和结果。支持增量输出查询，通过偏移量获取新增输出。",
    annotations={
        "title": "任务状态查询器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def query_task_status(
    token: str,
    stdout_offset: StdoutOffsetInt = 0,
    stderr_offset: StderrOffsetInt = 0,
) -> Dict[str, Any]:
    """
    查询异步任务执行状态和结果

    Args:
        token: 任务 token (GUID 字符串)
        stdout_offset: stdout 输出偏移量（默认 0，返回全部）
        stderr_offset: stderr 输出偏移量（默认 0，返回全部）

    Returns:
        包含任务状态和结果的字典，包括：
        - token: 任务 token
        - status: 状态 (pending/running/completed/not_found)
        - task_type: 任务类型
        - stdout: stdout 输出（从偏移量开始）
        - stderr: stderr 输出（从偏移量开始）
        - stdout_length: stdout 总长度
        - stderr_length: stderr 总长度
        - exit_code: 退出码（完成时）
        - execution_time: 执行时间（完成时）
        - pty_used: 是否使用了 PTY 模式
        - pty_fallback: 是否发生了 PTY 降级
    """
    try:
        result = _svc().query_task_status(token, stdout_offset, stderr_offset)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="get_version",
    description="获取 pkg-publisher 版本号。",
    annotations={
        "title": "版本查询器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def get_version_tool() -> Dict[str, str]:
    """
    获取 pkg-publisher 版本号

    Returns:
        包含版本号的字典
    """
    try:
        version = get_version()
        return {"version": version}
    except Exception as e:
        return {"error": str(e)}
