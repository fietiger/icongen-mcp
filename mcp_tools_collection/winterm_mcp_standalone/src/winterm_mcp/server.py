from __future__ import annotations

from typing import Annotated, Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from .service import CommandService, get_version, __version__
from pydantic import Field

CommandStr = Annotated[
    str,
    Field(
        description="要执行的命令字符串",
        min_length=1,
        max_length=1000,
    ),
]

ShellTypeStr = Annotated[
    str,
    Field(
        description="Shell 类型 (powershell, cmd, executable)，默认 executable",
        pattern="^(powershell|cmd|executable)$",
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

ExecutableStr = Annotated[
    Optional[str],
    Field(
        description="可执行文件路径（仅当 shell_type 为 executable 时使用）",
        default=None,
    ),
]

ArgsList = Annotated[
    Optional[list[str]],
    Field(
        description="可执行文件参数列表（仅当 shell_type 为 executable 时使用）",
        default=None,
    ),
]

app = FastMCP("winterm-mcp")

_service: Optional[CommandService] = None


def init_service(service: CommandService) -> None:
    global _service
    _service = service


def _svc() -> CommandService:
    if _service is None:
        raise RuntimeError(
            "Service not initialized. "
            "Call init_service() before running the server."
        )
    return _service


@app.tool(
    name="run_command",
    description=(
        "异步执行Windows终端命令，立即返回 token。"
        "命令将在后台执行，可通过 query_command_status 查询结果。"
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
    shell_type: ShellTypeStr = "executable",
    timeout: TimeoutInt = 30,
    working_directory: WorkingDirectoryStr = None,
    executable: ExecutableStr = None,
    args: ArgsList = None,
    enable_streaming: bool = False,
) -> Dict[str, Any]:
    """
    异步执行Windows终端命令

    Args:
        command: 要执行的命令
        shell_type: Shell 类型 (powershell, cmd, executable)，默认 executable
        timeout: 超时秒数 (1-3600)，默认 30 秒
        working_directory: 工作目录（可选，默认为当前目录）
        executable: 可执行文件路径（仅当 shell_type 为 executable 时使用）
        args: 可执行文件参数列表（仅当 shell_type 为 executable 时使用）
        enable_streaming: 启用实时流式输出

    Returns:
        包含token和状态信息的字典
    """
    try:
        token = _svc().run_command(
            command,
            executable,
            args,
            shell_type,
            timeout,
            working_directory,
            enable_streaming,
        )
        return {"token": token, "status": "pending", "message": "submitted"}
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="query_command_status",
    description=("查询命令执行状态和结果。" "返回命令的当前状态、退出码、输出等信息。"),
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


@app.tool(
    name="enhanced_query_command_status",
    description=(
        "增强版命令状态查询，支持流式输出。"
        "可以指定时间戳，只返回该时间戳之后的输出。"
    ),
    annotations={
        "title": "增强版命令状态查询器",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def enhanced_query_command_status(
    token: str,
    since_timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    """
    增强版命令状态查询，支持流式输出

    Args:
        token: 任务 token (GUID 字符串)
        since_timestamp: 时间戳（毫秒），只返回此时间戳之后的输出

    Returns:
        包含命令状态和结果的字典
    """
    try:
        result = _svc().enhanced_query_command_status(token, since_timestamp)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="send_command_input",
    description=(
        "向正在运行的命令发送输入。"
        "用于交互式命令，例如需要用户输入的程序。"
    ),
    annotations={
        "title": "命令输入发送器",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def send_command_input(
    token: str,
    input: str,
    append_newline: bool = True,
) -> Dict[str, Any]:
    """
    向正在运行的命令发送输入

    Args:
        token: 任务 token (GUID 字符串)
        input: 要发送的输入内容
        append_newline: 是否在输入后追加换行符，默认 True

    Returns:
        包含操作结果的字典
    """
    try:
        result = _svc().send_command_input(token, input, append_newline)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="terminate_command",
    description=(
        "终止正在运行的命令。"
        "强制停止命令执行，适用于长时间运行的命令。"
    ),
    annotations={
        "title": "命令终止器",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def terminate_command(token: str) -> Dict[str, Any]:
    """
    终止正在运行的命令

    Args:
        token: 任务 token (GUID 字符串)

    Returns:
        包含操作结果的字典
    """
    try:
        result = _svc().terminate_command(token)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.tool(
    name="get_version",
    description="获取 winterm-mcp 服务的版本信息和运行状态。",
    annotations={
        "title": "版本信息",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def get_version_tool() -> Dict[str, Any]:
    """
    获取 winterm-mcp 版本信息

    Returns:
        包含版本号和服务状态的字典
    """
    try:
        result = _svc().get_version_info()
        return result
    except Exception as e:
        return {"error": str(e), "version": __version__}
