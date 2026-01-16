from __future__ import annotations

from typing import Annotated, Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from .service import RunCmdService
from pydantic import Field

CommandStr = Annotated[
    str,
    Field(
        description="要执行的命令字符串",
        min_length=1,
        max_length=1000,
    ),
]

TimeoutInt = Annotated[
    Optional[int],
    Field(
        description="超时秒数 (1-3600)，默认 30 秒",
        ge=1,
        le=3600,
        default=30,
    ),
]

WorkingDirectoryStr = Annotated[
    Optional[str],
    Field(
        description="工作目录（可选，默认为当前目录）",
        default=None,
        max_length=1000,
    ),
]

# FastMCP app
app = FastMCP("runcmd-mcp")

# Injected at runtime by __main__.py
_service: Optional[RunCmdService] = None


def init_service(service: RunCmdService) -> None:
    global _service
    _service = service


def _svc() -> RunCmdService:
    if _service is None:
        raise RuntimeError(
            "Service not initialized. "
            "Call init_service() before running the server."
        )
    return _service


# ------------------ Tools ------------------


@app.tool(
    name="run_command",
    description="异步执行系统命令，立即返回 token。命令将在后台执行，可通过 query_command_status 查询结果。",
    annotations={
        "title": "异步命令执行器",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
def run_command(
    command: CommandStr,
    timeout: TimeoutInt = 30,
    working_directory: WorkingDirectoryStr = None,
) -> Dict[str, Any]:
    """
    异步执行系统命令

    Args:
        command: 要执行的命令
        timeout: 超时秒数 (1-3600)，默认 30 秒
        working_directory: 工作目录（可选，默认为当前目录）

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().run_command(command, timeout, working_directory)
        return {"token": token, "status": "pending", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="query_command_status",
    description="查询命令执行状态和结果。返回命令的当前状态、退出码、输出等信息。",
    annotations={
        "title": "命令状态查询器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def query_command_status(token: str) -> Dict[str, Any]:
    """
    查询命令执行状态和结果

    Args:
        token: 任务 token (GUID 字符串)

    Returns:
        包含命令状态和结果的字典
    """
    try:
        result = _svc().query_command_status(token)
        return result
    except Exception as e:
        return {"error": str(e)}
