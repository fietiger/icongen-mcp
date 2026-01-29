"""
winterm服务模块 - 异步执行Windows终端命令服务
"""

import subprocess
import threading
import uuid
import time
import os
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List, Literal

try:
    import winpty
    WINPTY_AVAILABLE = True
except ImportError:
    WINPTY_AVAILABLE = False

from .models import CommandInfo, QueryStatusResponse, RunCommandParams
from .store import CommandStore
from .utils import find_powershell, find_cmd, resolve_executable_path, strip_ansi_codes
from .constants import (
    NAME,
    VERSION,
    ENV_POWERSHELL_PATH,
    ENV_CMD_PATH,
    ENV_PYTHON_PATH,
    PTY_COLS,
    PTY_ROWS,
    MIN_TIMEOUT,
    MAX_TIMEOUT,
    DEFAULT_TIMEOUT,
)

__version__ = VERSION

logger = logging.getLogger(NAME)


def setup_logging(level: int = logging.INFO) -> None:
    """
    配置日志输出

    Args:
        level: 日志级别，默认 INFO

    日志输出位置：
    1. 控制台 (stderr)
    2. 文件: %TEMP%/winterm-mcp.log 或 /tmp/winterm-mcp.log

    可通过环境变量配置：
    - WINTERM_LOG_LEVEL: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - WINTERM_LOG_FILE: 自定义日志文件路径
    """
    import tempfile

    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = os.environ.get("WINTERM_LOG_FILE")
    if not log_file:
        log_file = os.path.join(tempfile.gettempdir(), "winterm-mcp.log")

    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Log file: {log_file}")
    except Exception as e:
        logger.warning(f"Failed to create log file {log_file}: {e}")

    logger.setLevel(level)

    env_level = os.environ.get("WINTERM_LOG_LEVEL", "").upper()
    if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        logger.setLevel(getattr(logging, env_level))


def get_version() -> str:
    """
    获取 winterm-mcp 版本号

    Returns:
        版本号字符串
    """
    return __version__


class CommandService:
    """
    异步命令执行服务类，管理所有异步命令的执行和状态
    """

    def __init__(self):
        self._store = CommandStore()
        self._powershell_path: Optional[str] = None
        self._cmd_path: Optional[str] = None

    def _get_powershell_path(self) -> str:
        """
        获取 PowerShell 可执行文件路径（带缓存）

        Returns:
            PowerShell 可执行文件的绝对路径

        Raises:
            FileNotFoundError: 如果找不到 PowerShell
        """
        if self._powershell_path is None:
            self._powershell_path = find_powershell()
            logger.debug(f"PowerShell path cached: {self._powershell_path}")
        return self._powershell_path

    def _get_cmd_path(self) -> str:
        """
        获取 CMD 可执行文件路径（带缓存）

        Returns:
            CMD 可执行文件的绝对路径

        Raises:
            FileNotFoundError: 如果找不到 CMD
        """
        if self._cmd_path is None:
            self._cmd_path = find_cmd()
            logger.debug(f"CMD path cached: {self._cmd_path}")
        return self._cmd_path

    def run_command(
        self,
        command: str,
        executable: Optional[str] = None,
        args: Optional[List[str]] = None,
        shell_type: Literal["powershell", "cmd", "executable"] = "executable",
        timeout: int = DEFAULT_TIMEOUT,
        working_directory: Optional[str] = None,
        enable_streaming: bool = False,
    ) -> str:
        """
        异步运行命令

        Args:
            command: 要执行的命令
            executable: 可执行文件路径
            args: 可执行文件参数
            shell_type: Shell 类型 (powershell/cmd/executable)
            timeout: 超时时间（秒）
            working_directory: 工作目录
            enable_streaming: 启用实时流式输出

        Returns:
            命令执行的token
        """
        if not command:
            raise ValueError("command cannot be empty")

        if len(command) > 1000:
            raise ValueError("command length cannot exceed 1000 characters")

        if timeout < MIN_TIMEOUT or timeout > MAX_TIMEOUT:
            raise ValueError(f"timeout must be between {MIN_TIMEOUT} and {MAX_TIMEOUT}")

        if shell_type not in ["powershell", "cmd", "executable"]:
            raise ValueError("shell_type must be 'powershell', 'cmd', or 'executable'")

        token = str(uuid.uuid4())

        logger.info(
            f"Submitting command: token={token}, shell={shell_type}, "
            f"timeout={timeout}, cwd={working_directory}, streaming={enable_streaming}"
        )
        logger.debug(
            f"Command content: {command[:100]}"
            f"{'...' if len(command) > 100 else ''}"
        )

        cmd_info = CommandInfo(
            token=token,
            executable=executable or "",
            args=args or [],
            command=command,
            shell_type=shell_type,
            status="pending",
            start_time=datetime.now(),
            timeout=timeout,
            working_directory=working_directory,
            stdout="",
            stderr="",
            exit_code=None,
            execution_time=None,
            timeout_occurred=False,
            pty_process=None,
            enable_streaming=enable_streaming,
        )

        self._store.add_command(token, cmd_info)

        thread = threading.Thread(
            target=self._execute_command,
            args=(token, command, executable, args, shell_type, timeout, working_directory, enable_streaming),
        )
        thread.daemon = True
        thread.start()

        return token

    def _execute_command(
        self,
        token: str,
        command: str,
        executable: Optional[str],
        args: Optional[List[str]],
        shell_type: str,
        timeout: int,
        working_directory: Optional[str],
        enable_streaming: bool,
    ):
        """
        在单独线程中执行命令
        """
        try:
            start_time = time.time()
            logger.debug(f"[{token}] Starting command execution...")

            self._store.update_command(token, status="running")

            encoding = "gbk"

            if shell_type == "powershell":
                ps_path = self._get_powershell_path()
                logger.info(f"[{token}] Using PowerShell: {ps_path}")
                cmd_args = [
                    ps_path,
                    "-NoProfile",
                    "-NoLogo",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ]
            elif shell_type == "cmd":
                cmd_path = self._get_cmd_path()
                logger.info(f"[{token}] Using CMD: {cmd_path}")
                cmd_args = [cmd_path, "/c", command]
            else:
                if executable:
                    resolved_exec = resolve_executable_path(executable)
                    logger.info(f"[{token}] Using executable: {resolved_exec}")
                    cmd_args = [resolved_exec] + (args or [])
                else:
                    logger.debug(f"[{token}] Using shell=True for command")
                    cmd_args = command

            logger.debug(f"[{token}] Executing: {cmd_args}")

            env = None
            python_path = os.environ.get(ENV_PYTHON_PATH)
            if python_path and os.path.isfile(python_path):
                env = os.environ.copy()
                python_dir = os.path.dirname(python_path)
                env["PATH"] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"
                logger.debug(f"[{token}] Using custom Python path: {python_path}")

            if enable_streaming and WINPTY_AVAILABLE:
                self._execute_with_pty(
                    token, cmd_args, shell_type, timeout, working_directory, env, start_time
                )
            else:
                self._execute_with_subprocess(
                    token, cmd_args, shell_type, timeout, working_directory, env, start_time, encoding
                )

        except FileNotFoundError as e:
            execution_time = time.time() - start_time
            logger.error(f"[{token}] Executable not found: {e}")
            self._store.update_command(
                token,
                status="not_found",
                stdout="",
                stderr=f"Executable not found: {e}",
                exit_code=-2,
                execution_time=int(execution_time * 1000),
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{token}] Command failed with exception: {e}")
            self._store.update_command(
                token,
                status="completed",
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=int(execution_time * 1000),
            )

    def _execute_with_subprocess(
        self,
        token: str,
        cmd_args: List[str] | str,
        shell_type: str,
        timeout: int,
        working_directory: Optional[str],
        env: Optional[Dict[str, str]],
        start_time: float,
        encoding: str,
    ):
        """
        使用 subprocess 执行命令
        """
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_directory,
            encoding=encoding,
            stdin=subprocess.DEVNULL,
            env=env,
            shell=(shell_type == "executable" and isinstance(cmd_args, str)),
        )

        execution_time = time.time() - start_time

        stdout_clean = strip_ansi_codes(result.stdout) if result.stdout else ""
        stderr_clean = strip_ansi_codes(result.stderr) if result.stderr else ""

        logger.info(
            f"[{token}] Command completed: exit_code={result.returncode}, "
            f"time={execution_time:.3f}s"
        )
        logger.debug(
            f"[{token}] stdout: "
            f"{stdout_clean[:200] if stdout_clean else '(empty)'}"
        )
        logger.debug(
            f"[{token}] stderr: "
            f"{stderr_clean[:200] if stderr_clean else '(empty)'}"
        )

        self._store.update_command(
            token,
            status="completed",
            stdout=stdout_clean,
            stderr=stderr_clean,
            exit_code=result.returncode,
            execution_time=int(execution_time * 1000),
        )

    def _execute_with_pty(
        self,
        token: str,
        cmd_args: List[str] | str,
        shell_type: str,
        timeout: int,
        working_directory: Optional[str],
        env: Optional[Dict[str, str]],
        start_time: float,
    ):
        """
        使用 winpty 执行命令，支持交互式输入和实时流式输出
        """
        if isinstance(cmd_args, str):
            logger.warning(f"[{token}] PTY mode requires list of arguments, falling back to subprocess")
            self._execute_with_subprocess(
                token, cmd_args, shell_type, timeout, working_directory, env, start_time, "gbk"
            )
            return

        try:
            cwd = working_directory or os.getcwd()
            pty = winpty.PtyProcess.spawn(
                cmd_args,
                cols=PTY_COLS,
                rows=PTY_ROWS,
                cwd=cwd,
                env=env or os.environ,
            )

            self._store.update_command(token, pty_process=pty)
            logger.info(f"[{token}] PTY process started: pid={pty.pid}")

            stdout_buffer = ""
            stderr_buffer = ""
            timeout_timer = None
            timeout_occurred = False

            def on_timeout():
                nonlocal timeout_occurred
                timeout_occurred = True
                logger.warning(f"[{token}] Command timed out after {timeout}s")
                if pty and pty.isalive():
                    pty.terminate()

            if timeout > 0:
                timeout_timer = threading.Timer(timeout, on_timeout)
                timeout_timer.start()

            def on_data(data: str):
                nonlocal stdout_buffer
                stdout_buffer += data
                self._store.update_command(
                    token,
                    stdout=stdout_buffer,
                    last_output_timestamp=int(time.time() * 1000),
                )
                logger.debug(f"[{token}] Received {len(data)} bytes of output")

            pty.set_winpty_size(PTY_COLS, PTY_ROWS)

            while pty.isalive() and not timeout_occurred:
                try:
                    data = pty.read()
                    if data:
                        on_data(data)
                    time.sleep(0.01)
                except Exception as e:
                    logger.error(f"[{token}] Error reading from PTY: {e}")
                    break

            if timeout_timer:
                timeout_timer.cancel()

            exit_code = pty.get_exitstatus() if not pty.isalive() else -1

            stdout_clean = strip_ansi_codes(stdout_buffer) if stdout_buffer else ""
            execution_time = time.time() - start_time

            logger.info(
                f"[{token}] PTY command completed: exit_code={exit_code}, "
                f"time={execution_time:.3f}s"
            )
            logger.debug(
                f"[{token}] stdout: "
                f"{stdout_clean[:200] if stdout_clean else '(empty)'}"
            )

            self._store.update_command(
                token,
                status="terminated" if timeout_occurred else "completed",
                stdout=stdout_clean,
                stderr=stderr_buffer,
                exit_code=exit_code,
                execution_time=int(execution_time * 1000),
                timeout_occurred=timeout_occurred,
                pty_process=None,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{token}] PTY execution failed: {e}")
            self._store.update_command(
                token,
                status="completed",
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=int(execution_time * 1000),
                pty_process=None,
            )

    def query_command_status(self, token: str) -> Dict[str, Any]:
        """
        查询命令执行状态

        Args:
            token: 命令的token

        Returns:
            包含命令状态的字典
        """
        logger.debug(f"Querying status for token: {token}")

        cmd_info = self._store.get_command(token)

        if not cmd_info:
            logger.warning(f"Token not found: {token}")
            return {
                "token": token,
                "status": "not_found",
                "message": "Token not found",
            }

        logger.debug(f"[{token}] Status: {cmd_info.status}")

        if cmd_info.status == "running":
            return {"token": cmd_info.token, "status": "running"}
        elif cmd_info.status in ["completed", "pending", "not_found", "terminated"]:
            return {
                "token": cmd_info.token,
                "status": cmd_info.status,
                "exit_code": cmd_info.exit_code,
                "stdout": cmd_info.stdout,
                "stderr": cmd_info.stderr,
                "execution_time": cmd_info.execution_time,
                "timeout_occurred": cmd_info.timeout_occurred,
            }
        else:
            return {"token": cmd_info.token, "status": cmd_info.status}

    def enhanced_query_command_status(
        self, token: str, since_timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        增强版状态查询，支持流式输出

        Args:
            token: 命令令牌
            since_timestamp: 只返回此时间戳之后的输出（毫秒）

        Returns:
            包含命令状态和结果的字典
        """
        logger.debug(f"Enhanced query for token: {token}, since: {since_timestamp}")

        cmd_info = self._store.get_command(token)

        if not cmd_info:
            logger.warning(f"Token not found: {token}")
            return {
                "token": token,
                "status": "not_found",
                "message": "Token not found",
            }

        result = {
            "token": cmd_info.token,
            "status": cmd_info.status,
        }

        if cmd_info.status != "running":
            result.update({
                "exit_code": cmd_info.exit_code,
                "stdout": cmd_info.stdout,
                "stderr": cmd_info.stderr,
                "execution_time": cmd_info.execution_time,
                "timeout_occurred": cmd_info.timeout_occurred,
            })

        if since_timestamp is not None and cmd_info.last_output_timestamp > since_timestamp:
            result["stdout"] = cmd_info.stdout
            result["stderr"] = cmd_info.stderr

        return result

    def send_command_input(
        self, token: str, input: str, append_newline: bool = True
    ) -> Dict[str, Any]:
        """
        向运行中的命令发送输入

        Args:
            token: 命令令牌
            input: 要发送的输入
            append_newline: 是否追加换行符

        Returns:
            包含操作结果的字典
        """
        logger.debug(f"Sending input to token: {token}")

        cmd_info = self._store.get_command(token)

        if not cmd_info:
            logger.warning(f"Token not found: {token}")
            return {
                "success": False,
                "message": "Token not found",
                "token": token,
            }

        if cmd_info.status != "running":
            logger.warning(f"[{token}] Command is not running: {cmd_info.status}")
            return {
                "success": False,
                "message": f"Command is not running: {cmd_info.status}",
                "token": token,
            }

        if not cmd_info.pty_process:
            logger.warning(f"[{token}] No PTY process available")
            return {
                "success": False,
                "message": "PTY process not available",
                "token": token,
            }

        try:
            input_data = input
            if append_newline:
                input_data += "\r\n"

            cmd_info.pty_process.write(input_data)
            logger.debug(f"[{token}] Input sent successfully")
            return {
                "success": True,
                "message": "Input sent successfully",
                "token": token,
            }
        except Exception as e:
            logger.error(f"[{token}] Failed to send input: {e}")
            return {
                "success": False,
                "message": str(e),
                "token": token,
            }

    def terminate_command(self, token: str) -> Dict[str, Any]:
        """
        终止运行中的命令

        Args:
            token: 命令令牌

        Returns:
            包含操作结果的字典
        """
        logger.debug(f"Terminating token: {token}")

        cmd_info = self._store.get_command(token)

        if not cmd_info:
            logger.warning(f"Token not found: {token}")
            return {
                "success": False,
                "message": "Token not found",
                "token": token,
            }

        if cmd_info.status != "running":
            logger.warning(f"[{token}] Command is not running: {cmd_info.status}")
            return {
                "success": False,
                "message": f"Command is not running: {cmd_info.status}",
                "token": token,
            }

        try:
            if cmd_info.pty_process:
                cmd_info.pty_process.terminate()
                logger.debug(f"[{token}] PTY process terminated")

            self._store.update_command(
                token,
                status="terminated",
                exit_code=-1,
            )

            logger.info(f"[{token}] Command terminated successfully")
            return {
                "success": True,
                "message": "Command terminated successfully",
                "token": token,
            }
        except Exception as e:
            logger.error(f"[{token}] Failed to terminate command: {e}")
            return {
                "success": False,
                "message": str(e),
                "token": token,
            }

    def get_version_info(self) -> Dict[str, Any]:
        """
        获取版本信息

        Returns:
            包含版本信息的字典
        """
        import sys
        import platform

        try:
            ps_path = None
            ps_error = None
            try:
                ps_path = find_powershell()
            except FileNotFoundError as e:
                ps_error = str(e)

            return {
                "version": get_version(),
                "service_status": "running",
                "python_version": sys.version,
                "platform": sys.platform,
                "arch": platform.machine(),
                "env": {
                    "WINTERM_POWERSHELL_PATH": os.environ.get(ENV_POWERSHELL_PATH),
                    "WINTERM_CMD_PATH": os.environ.get(ENV_CMD_PATH),
                    "WINTERM_PYTHON_PATH": os.environ.get(ENV_PYTHON_PATH),
                    "WINTERM_LOG_LEVEL": os.environ.get("WINTERM_LOG_LEVEL"),
                },
            }
        except Exception as e:
            return {
                "version": get_version(),
                "service_status": "error",
                "error": str(e),
            }


RunCmdService = CommandService
