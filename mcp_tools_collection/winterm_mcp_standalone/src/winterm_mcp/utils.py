"""
工具函数 - winterm-mcp
"""

import os
import re
import shutil
import logging
from typing import Optional
from .constants import (
    ENV_POWERSHELL_PATH,
    ENV_CMD_PATH,
    POWERSHELL_PATHS,
    PWSH_PATHS,
    CMD_PATHS,
)

logger = logging.getLogger("winterm-mcp")


def find_powershell() -> str:
    """
    查找 PowerShell 可执行文件路径

    优先级:
    1. WINTERM_POWERSHELL_PATH 环境变量
    2. 标准 PowerShell 路径
    3. PowerShell Core 路径
    4. PATH 环境变量
    5. 抛出 FileNotFoundError

    Returns:
        PowerShell 可执行文件的绝对路径

    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    logger.debug("Starting PowerShell path discovery...")

    custom_path = os.environ.get(ENV_POWERSHELL_PATH)
    if custom_path:
        logger.debug(f"Found env var {ENV_POWERSHELL_PATH}={custom_path}")
        if os.path.isfile(custom_path):
            logger.info(f"Using custom PowerShell path: {custom_path}")
            return custom_path
        else:
            logger.warning(
                f"Custom PowerShell path not found: {custom_path}, "
                "falling back to standard paths"
            )

    for path in POWERSHELL_PATHS:
        logger.debug(f"Checking standard path: {path}")
        if os.path.isfile(path):
            logger.info(f"Found Windows PowerShell: {path}")
            return path

    for path in PWSH_PATHS:
        logger.debug(f"Checking PowerShell Core path: {path}")
        if os.path.isfile(path):
            logger.info(f"Found PowerShell Core: {path}")
            return path

    logger.debug("Checking PATH environment variable...")
    ps_path = shutil.which("powershell")
    if ps_path:
        logger.info(f"Found PowerShell in PATH: {ps_path}")
        return ps_path

    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        logger.info(f"Found pwsh in PATH: {pwsh_path}")
        return pwsh_path

    checked_paths = POWERSHELL_PATHS + PWSH_PATHS
    error_msg = (
        f"PowerShell not found. "
        f"Set {ENV_POWERSHELL_PATH} environment variable or "
        f"ensure PowerShell is installed. "
        f"Checked paths: {', '.join(checked_paths)}"
    )
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


def find_cmd() -> str:
    """
    查找 CMD 可执行文件路径

    优先级:
    1. WINTERM_CMD_PATH 环境变量
    2. 标准 CMD 路径
    3. PATH 环境变量
    4. 抛出 FileNotFoundError

    Returns:
        CMD 可执行文件的绝对路径

    Raises:
        FileNotFoundError: 如果找不到 CMD
    """
    logger.debug("Starting CMD path discovery...")

    custom_path = os.environ.get(ENV_CMD_PATH)
    if custom_path:
        logger.debug(f"Found env var {ENV_CMD_PATH}={custom_path}")
        if os.path.isfile(custom_path):
            logger.info(f"Using custom CMD path: {custom_path}")
            return custom_path
        else:
            logger.warning(
                f"Custom CMD path not found: {custom_path}, "
                "falling back to standard paths"
            )

    for path in CMD_PATHS:
        logger.debug(f"Checking standard path: {path}")
        if os.path.isfile(path):
            logger.info(f"Found CMD: {path}")
            return path

    logger.debug("Checking PATH environment variable...")
    cmd_path = shutil.which("cmd")
    if cmd_path:
        logger.info(f"Found CMD in PATH: {cmd_path}")
        return cmd_path

    error_msg = (
        f"CMD not found. "
        f"Set {ENV_CMD_PATH} environment variable or "
        f"ensure CMD is installed. "
        f"Checked paths: {', '.join(CMD_PATHS)}"
    )
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


def resolve_executable_path(executable: str) -> str:
    """
    解析可执行文件路径

    Args:
        executable: 可执行文件名称或路径

    Returns:
        解析后的可执行文件路径

    规则:
    - 如果是绝对路径，直接返回
    - 检查当前目录
    - 在 PATH 中搜索（支持 .exe, .bat, .cmd, .com, .ps1）
    - 返回原始名称（让系统处理错误）
    """
    if os.path.isabs(executable):
        logger.debug(f"Executable is absolute path: {executable}")
        return executable

    if os.path.isfile(executable):
        logger.debug(f"Executable found in current directory: {executable}")
        return os.path.abspath(executable)

    extensions = [".exe", ".bat", ".cmd", ".com", ".ps1"]

    for ext in extensions:
        if executable.lower().endswith(ext):
            path = shutil.which(executable)
            if path:
                logger.debug(f"Found executable in PATH: {path}")
                return path
            break
    else:
        for ext in extensions:
            full_path = shutil.which(executable + ext)
            if full_path:
                logger.debug(f"Found executable in PATH: {full_path}")
                return full_path

    logger.debug(f"Executable not found in PATH, returning original: {executable}")
    return executable


def strip_ansi_codes(text: str) -> str:
    """
    移除 ANSI 转义序列

    Args:
        text: 包含 ANSI 转义序列的文本

    Returns:
        清理后的文本

    支持的转义序列:
    - CSI 序列: \x1b[... 或 \u001b[...
    - OSC 序列: \x1b]...\x07
    - BEL 字符: \x07
    """
    ansi_escape = re.compile(
        r"""
        \x1b\[[0-9;]*[mGKHfABCDsuJK]  |  # CSI sequences
        \x1b\][0-9;]*\x07              |  # OSC sequences
        \x07                            |  # BEL character
        \x1b.                              # Other ESC sequences
        """,
        re.VERBOSE,
    )
    return ansi_escape.sub("", text)
