"""
winterm服务模块 - 异步执行Windows终端命令服务
"""

import subprocess
import threading
import uuid
import time
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

# 版本号
__version__ = "0.1.5"

# 配置日志
logger = logging.getLogger("winterm-mcp")


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
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出
    log_file = os.environ.get("WINTERM_LOG_FILE")
    if not log_file:
        # 默认日志文件路径
        log_file = os.path.join(tempfile.gettempdir(), "winterm-mcp.log")
    
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Log file: {log_file}")
    except Exception as e:
        logger.warning(f"Failed to create log file {log_file}: {e}")
    
    logger.setLevel(level)
    
    # 检查环境变量设置日志级别
    env_level = os.environ.get("WINTERM_LOG_LEVEL", "").upper()
    if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        logger.setLevel(getattr(logging, env_level))


# PowerShell 可执行文件的标准路径（按优先级排序）
POWERSHELL_PATHS: List[str] = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

# PowerShell Core (pwsh) 的常见路径
PWSH_PATHS: List[str] = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
]

# 环境变量名称
ENV_POWERSHELL_PATH = "WINTERM_POWERSHELL_PATH"


def _find_powershell() -> str:
    """
    查找可用的 PowerShell 可执行文件路径

    查找顺序：
    1. 环境变量 WINTERM_POWERSHELL_PATH（用户自定义）
    2. Windows PowerShell 标准路径
    3. PowerShell Core 标准路径
    4. PATH 环境变量中的 powershell/pwsh（兼容正常环境）

    Returns:
        PowerShell 可执行文件的绝对路径

    Raises:
        FileNotFoundError: 如果找不到 PowerShell
    """
    logger.debug("Starting PowerShell path discovery...")
    
    # 1. 检查用户配置的环境变量
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

    # 2. 检查 Windows PowerShell 标准路径
    for path in POWERSHELL_PATHS:
        logger.debug(f"Checking standard path: {path}")
        if os.path.isfile(path):
            logger.info(f"Found Windows PowerShell: {path}")
            return path

    # 3. 检查 PowerShell Core 标准路径
    for path in PWSH_PATHS:
        logger.debug(f"Checking PowerShell Core path: {path}")
        if os.path.isfile(path):
            logger.info(f"Found PowerShell Core: {path}")
            return path

    # 4. 尝试 PATH 环境变量（兼容正常环境）
    logger.debug("Checking PATH environment variable...")
    ps_path = shutil.which("powershell")
    if ps_path:
        logger.info(f"Found PowerShell in PATH: {ps_path}")
        return ps_path

    pwsh_path = shutil.which("pwsh")
    if pwsh_path:
        logger.info(f"Found pwsh in PATH: {pwsh_path}")
        return pwsh_path

    # 所有方法都失败
    checked_paths = POWERSHELL_PATHS + PWSH_PATHS
    error_msg = (
        f"PowerShell not found. "
        f"Set {ENV_POWERSHELL_PATH} environment variable or "
        f"ensure PowerShell is installed. "
        f"Checked paths: {', '.join(checked_paths)}"
    )
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


def get_version() -> str:
    """
    获取 winterm-mcp 版本号
    
    Returns:
        版本号字符串
    """
    return __version__


class RunCmdService:
    """
    异步命令执行服务类，管理所有异步命令的执行和状态
    """

    def __init__(self):
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._powershell_path: Optional[str] = None

    def _get_powershell_path(self) -> str:
        """
        获取 PowerShell 可执行文件路径（带缓存）

        首次调用时查找并缓存路径，后续调用直接返回缓存值。

        Returns:
            PowerShell 可执行文件的绝对路径

        Raises:
            FileNotFoundError: 如果找不到 PowerShell
        """
        if self._powershell_path is None:
            self._powershell_path = _find_powershell()
            logger.debug(f"PowerShell path cached: {self._powershell_path}")
        return self._powershell_path

    def run_command(
        self,
        command: str,
        shell_type: str = "powershell",
        timeout: int = 30,
        working_directory: Optional[str] = None,
    ) -> str:
        """
        异步运行命令

        Args:
            command: 要执行的命令
            shell_type: Shell 类型 (powershell 或 cmd)
            timeout: 超时时间（秒）
            working_directory: 工作目录

        Returns:
            命令执行的token
        """
        token = str(uuid.uuid4())
        
        logger.info(
            f"Submitting command: token={token}, shell={shell_type}, "
            f"timeout={timeout}, cwd={working_directory}"
        )
        logger.debug(f"Command content: {command[:100]}{'...' if len(command) > 100 else ''}")

        cmd_info = {
            "token": token,
            "command": command,
            "shell_type": shell_type,
            "status": "pending",
            "start_time": datetime.now(),
            "timeout": timeout,
            "working_directory": working_directory,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
            "timeout_occurred": False,
        }

        with self.lock:
            self.commands[token] = cmd_info

        thread = threading.Thread(
            target=self._execute_command,
            args=(token, command, shell_type, timeout, working_directory),
        )
        thread.daemon = True
        thread.start()

        return token

    def _execute_command(
        self,
        token: str,
        command: str,
        shell_type: str,
        timeout: int,
        working_directory: Optional[str],
    ):
        """
        在单独线程中执行命令
        """
        try:
            start_time = time.time()
            logger.debug(f"[{token}] Starting command execution...")

            with self.lock:
                if token in self.commands:
                    self.commands[token]["status"] = "running"

            encoding = "gbk"

            if shell_type == "powershell":
                # 使用绝对路径调用 PowerShell，避免 PATH 环境变量限制
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
            else:
                logger.debug(f"[{token}] Using cmd.exe")
                cmd_args = ["cmd", "/c", command]

            logger.debug(f"[{token}] Executing: {cmd_args}")
            
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_directory,
                encoding=encoding,
                stdin=subprocess.DEVNULL,  # 防止等待输入导致挂起
            )

            execution_time = time.time() - start_time
            
            logger.info(
                f"[{token}] Command completed: exit_code={result.returncode}, "
                f"time={execution_time:.3f}s"
            )
            logger.debug(f"[{token}] stdout: {result.stdout[:200] if result.stdout else '(empty)'}")
            logger.debug(f"[{token}] stderr: {result.stderr[:200] if result.stderr else '(empty)'}")

            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "exit_code": result.returncode,
                            "execution_time": execution_time,
                        }
                    )

        except FileNotFoundError as e:
            execution_time = time.time() - start_time
            logger.error(f"[{token}] PowerShell not found: {e}")
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": f"PowerShell not found: {e}",
                            "exit_code": -2,
                            "execution_time": execution_time,
                            "timeout_occurred": False,
                        }
                    )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.warning(f"[{token}] Command timed out after {timeout}s")
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": (
                                f"Command timed out after {timeout} seconds"
                            ),
                            "exit_code": -1,
                            "execution_time": execution_time,
                            "timeout_occurred": True,
                        }
                    )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{token}] Command failed with exception: {e}")
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": str(e),
                            "exit_code": -1,
                            "execution_time": execution_time,
                            "timeout_occurred": False,
                        }
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
        
        with self.lock:
            if token not in self.commands:
                logger.warning(f"Token not found: {token}")
                return {
                    "token": token,
                    "status": "not_found",
                    "message": "Token not found",
                }

            cmd_info = self.commands[token].copy()
            logger.debug(f"[{token}] Status: {cmd_info['status']}")

            if cmd_info["status"] == "running":
                return {"token": cmd_info["token"], "status": "running"}
            elif cmd_info["status"] in ["completed", "pending"]:
                return {
                    "token": cmd_info["token"],
                    "status": cmd_info["status"],
                    "exit_code": cmd_info["exit_code"],
                    "stdout": cmd_info["stdout"],
                    "stderr": cmd_info["stderr"],
                    "execution_time": cmd_info["execution_time"],
                    "timeout_occurred": cmd_info["timeout_occurred"],
                }
            else:
                return cmd_info
