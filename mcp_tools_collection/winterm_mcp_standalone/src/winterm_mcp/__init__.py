"""
winterm-mcp - Windows Terminal MCP Service
"""

from .service import __version__, get_version, setup_logging, CommandService
from .models import CommandInfo, QueryStatusResponse, VersionInfo, RunCommandParams
from .store import CommandStore
from .utils import find_powershell, find_cmd, resolve_executable_path, strip_ansi_codes
from .constants import NAME, VERSION, ENV_POWERSHELL_PATH, ENV_CMD_PATH, ENV_PYTHON_PATH

__author__ = "winterm-mcp contributors"

__all__ = [
    "__version__",
    "get_version",
    "setup_logging",
    "CommandService",
    "CommandInfo",
    "QueryStatusResponse",
    "VersionInfo",
    "RunCommandParams",
    "CommandStore",
    "find_powershell",
    "find_cmd",
    "resolve_executable_path",
    "strip_ansi_codes",
    "NAME",
    "VERSION",
    "ENV_POWERSHELL_PATH",
    "ENV_CMD_PATH",
    "ENV_PYTHON_PATH",
]
