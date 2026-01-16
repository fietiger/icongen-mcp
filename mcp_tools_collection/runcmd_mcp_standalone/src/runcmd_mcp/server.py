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

UsePtyBool = Annotated[
    bool,
    Field(
        description="是否使用 PTY（伪终端）模式执行命令。启用后可正确捕获进度条等终端交互程序的输出。默认 False",
        default=False,
    ),
]

MaxBufferSizeInt = Annotated[
    int,
    Field(
        description="最大输出缓冲区大小（字节）。超过此大小时会截断旧数据保留最新输出。默认 10MB (10485760)",
        ge=1024,
        le=104857600,  # 最大 100MB
        default=10485760,
    ),
]

StdoutOffsetInt = Annotated[
    int,
    Field(
        description="stdout 输出偏移量。用于增量查询，只返回从该偏移量开始的新输出。默认 0（返回全部）",
        ge=0,
        default=0,
    ),
]

StderrOffsetInt = Annotated[
    int,
    Field(
        description="stderr 输出偏移量。用于增量查询，只返回从该偏移量开始的新输出。默认 0（返回全部）",
        ge=0,
        default=0,
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
    description=(
        "异步执行系统命令，立即返回 token。命令将在后台执行，可通过 query_command_status 查询结果。\n\n"
        "支持实时输出流功能：\n"
        "- 命令执行过程中可随时查询已产生的输出\n"
        "- 支持 PTY 模式，正确捕获进度条等终端交互程序的输出\n"
        "- 支持增量查询，只获取新增的输出内容"
    ),
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
    use_pty: UsePtyBool = False,
    max_buffer_size: MaxBufferSizeInt = 10485760,
) -> Dict[str, Any]:
    """
    异步执行系统命令

    Args:
        command: 要执行的命令
        timeout: 超时秒数 (1-3600)，默认 30 秒
        working_directory: 工作目录（可选，默认为当前目录）
        use_pty: 是否使用 PTY 模式（默认 False）
        max_buffer_size: 最大输出缓冲区大小（默认 10MB）

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().run_command(
            command,
            timeout,
            working_directory,
            use_pty=use_pty,
            max_buffer_size=max_buffer_size,
        )
        return {"token": token, "status": "pending", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="query_command_status",
    description=(
        "查询命令执行状态和结果。返回命令的当前状态、退出码、输出等信息。\n\n"
        "支持增量输出查询：\n"
        "- 使用 stdout_offset/stderr_offset 参数只获取新增的输出\n"
        "- 响应中包含 stdout_length/stderr_length 表示当前总长度，可作为下次查询的偏移量\n"
        "- 响应中包含 stdout_truncated/stderr_truncated 表示输出是否因超过缓冲区大小而被截断"
    ),
    annotations={
        "title": "命令状态查询器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def query_command_status(
    token: str,
    stdout_offset: StdoutOffsetInt = 0,
    stderr_offset: StderrOffsetInt = 0,
) -> Dict[str, Any]:
    """
    查询命令执行状态和结果

    Args:
        token: 任务 token (GUID 字符串)
        stdout_offset: stdout 输出偏移量（默认 0，返回全部）
        stderr_offset: stderr 输出偏移量（默认 0，返回全部）

    Returns:
        包含命令状态和结果的字典：
        - token: 命令 token
        - status: 状态 (pending/running/completed/not_found)
        - exit_code: 退出码（完成时）
        - stdout: stdout 输出（从偏移量开始）
        - stderr: stderr 输出（从偏移量开始）
        - stdout_length: stdout 总长度（可作为下次查询的偏移量）
        - stderr_length: stderr 总长度（可作为下次查询的偏移量）
        - stdout_truncated: stdout 是否被截断
        - stderr_truncated: stderr 是否被截断
        - execution_time: 执行时间（完成时）
        - timeout_occurred: 是否超时
    """
    try:
        result = _svc().query_command_status(
            token,
            stdout_offset=stdout_offset,
            stderr_offset=stderr_offset,
        )
        return result
    except Exception as e:
        return {"error": str(e)}
