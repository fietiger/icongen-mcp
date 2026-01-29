"""
数据模型定义 - winterm-mcp
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Any


@dataclass
class CommandInfo:
    """
    命令信息数据类
    """
    token: str
    executable: str
    args: list[str]
    command: str
    shell_type: Literal["powershell", "cmd", "executable"]
    status: Literal["pending", "running", "completed", "not_found", "terminated"]
    start_time: datetime
    timeout: int
    working_directory: str | None
    stdout: str
    stderr: str
    exit_code: int | None
    execution_time: int | None
    timeout_occurred: bool
    pty_process: Any | None
    enable_streaming: bool
    last_output_timestamp: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))


@dataclass
class QueryStatusResponse:
    """
    状态查询响应数据类
    """
    token: str
    status: str
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    execution_time: int | None = None
    timeout_occurred: bool | None = None
    message: str | None = None


@dataclass
class VersionInfo:
    """
    版本信息数据类
    """
    version: str
    service_status: str
    python_version: str
    platform: str
    arch: str
    env: dict[str, str | None]


@dataclass
class RunCommandParams:
    """
    执行命令参数数据类
    """
    command: str
    executable: str | None = None
    args: list[str] | None = None
    shell_type: Literal["powershell", "cmd", "executable"] = "executable"
    timeout: int = 30
    working_directory: str | None = None
    enable_streaming: bool = False
