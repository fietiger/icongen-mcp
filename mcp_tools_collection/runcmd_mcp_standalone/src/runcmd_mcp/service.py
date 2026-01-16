"""
runcmd服务模块 - 异步执行系统命令服务
"""

import subprocess
import threading
import uuid
import time
import os
from datetime import datetime
from typing import Dict, Optional, Any

# 环境变量名称
ENV_PYTHON_PATH = "RUNCMD_PYTHON_PATH"


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
        timeout: int = 30,
        working_directory: Optional[str] = None,
    ) -> str:
        """
        异步运行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            working_directory: 工作目录

        Returns:
            命令执行的token
        """
        token = str(uuid.uuid4())

        # 创建命令信息字典
        cmd_info = {
            "token": token,
            "command": command,
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

        # 存储命令信息
        with self.lock:
            self.commands[token] = cmd_info

        # 在新线程中执行命令
        thread = threading.Thread(
            target=self._execute_command,
            args=(token, command, timeout, working_directory),
        )
        thread.daemon = True
        thread.start()

        return token

    def _execute_command(
        self,
        token: str,
        command: str,
        timeout: int,
        working_directory: Optional[str],
    ):
        """
        在单独线程中执行命令
        """
        try:
            start_time = time.time()

            # 更新状态为运行中
            with self.lock:
                if token in self.commands:
                    self.commands[token]["status"] = "running"

            # 处理 Python 路径环境变量
            env = None
            python_path = os.environ.get(ENV_PYTHON_PATH)
            if python_path and os.path.isfile(python_path):
                env = os.environ.copy()
                python_dir = os.path.dirname(python_path)
                env["PATH"] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"

            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_directory,
                env=env,
            )

            execution_time = time.time() - start_time

            # 更新命令结果
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
            # 处理超时
            execution_time = time.time() - start_time
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
            # 处理其他异常
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

            # 如果命令仍在运行中，不返回输出内容以节省资源
            if cmd_info["status"] == "running":
                # 只返回基本信息
                return {"token": cmd_info["token"], "status": "running"}
            elif cmd_info["status"] in ["completed", "pending"]:
                # 返回完整信息
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
