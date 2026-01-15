"""
winterm服务模块 - 异步执行Windows终端命令服务
"""

import subprocess
import threading
import uuid
import time
from datetime import datetime
from typing import Dict, Optional, Any


class RunCmdService:
    """
    异步命令执行服务类，管理所有异步命令的执行和状态
    """

    def __init__(self):
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

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

            with self.lock:
                if token in self.commands:
                    self.commands[token]["status"] = "running"

            encoding = "gbk"

            if shell_type == "powershell":
                # 添加 -ExecutionPolicy Bypass 避免执行策略阻塞
                # 添加 -NoLogo 减少启动输出
                cmd_args = [
                    "powershell",
                    "-NoProfile",
                    "-NoLogo",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ]
            else:
                cmd_args = ["cmd", "/c", command]

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

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            with self.lock:
                if token in self.commands:
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": "",
                            "stderr": (f"Command timed out after {timeout} seconds"),
                            "exit_code": -1,
                            "execution_time": execution_time,
                            "timeout_occurred": True,
                        }
                    )
        except Exception as e:
            execution_time = time.time() - start_time
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
        with self.lock:
            if token not in self.commands:
                return {
                    "token": token,
                    "status": "not_found",
                    "message": "Token not found",
                }

            cmd_info = self.commands[token].copy()

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
