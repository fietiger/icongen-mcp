"""
runcmd服务模块 - 异步执行系统命令服务

支持实时输出流功能，包括：
- 流式输出捕获
- PTY 模式支持
- 增量输出查询
"""

import subprocess
import threading
import uuid
import time
import os
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from .streaming_buffer import StreamingBuffer
from .executors import execute_with_pty_fallback

# 环境变量名称
ENV_PYTHON_PATH = "RUNCMD_PYTHON_PATH"

# 默认最大缓冲区大小：10MB
DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024

logger = logging.getLogger(__name__)


class RunCmdService:
    """
    异步命令执行服务类，管理所有异步命令的执行和状态
    
    支持实时输出流功能：
    - 流式输出捕获到 StreamingBuffer
    - PTY 模式执行（可选）
    - 增量输出查询（通过偏移量）
    """

    def __init__(self):
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def run_command(
        self,
        command: str,
        timeout: int = 30,
        working_directory: Optional[str] = None,
        use_pty: bool = False,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
    ) -> str:
        """
        异步运行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            working_directory: 工作目录
            use_pty: 是否使用 PTY 模式（默认 False）
            max_buffer_size: 最大输出缓冲区大小（默认 10MB）

        Returns:
            命令执行的token
        """
        token = str(uuid.uuid4())
        
        # 创建 StreamingBuffer 实例
        stdout_buffer = StreamingBuffer(max_size=max_buffer_size)
        stderr_buffer = StreamingBuffer(max_size=max_buffer_size)

        # 创建命令信息字典
        cmd_info = {
            "token": token,
            "command": command,
            "status": "pending",
            "start_time": datetime.now(),
            "timeout": timeout,
            "working_directory": working_directory,
            "use_pty": use_pty,
            "max_buffer_size": max_buffer_size,
            # 使用 StreamingBuffer 替代字符串
            "stdout_buffer": stdout_buffer,
            "stderr_buffer": stderr_buffer,
            # 保留旧字段用于向后兼容
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
            "timeout_occurred": False,
            # 新增字段
            "pty_used": False,
            "pty_fallback": False,
            "fallback_reason": "",
        }

        # 存储命令信息
        with self.lock:
            self.commands[token] = cmd_info

        # 在新线程中执行命令
        thread = threading.Thread(
            target=self._execute_command,
            args=(token, command, timeout, working_directory, use_pty),
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
        use_pty: bool = False,
    ):
        """
        在单独线程中执行命令
        
        使用新的执行器（SubprocessExecutor 或 PtyExecutor）替代原有 subprocess.run，
        支持流式输出捕获和 PTY 模式。
        
        Args:
            token: 命令的 token
            command: 要执行的命令
            timeout: 超时时间（秒）
            working_directory: 工作目录
            use_pty: 是否使用 PTY 模式
        """
        try:
            start_time = time.time()

            # 更新状态为运行中
            with self.lock:
                if token in self.commands:
                    self.commands[token]["status"] = "running"

            # 获取缓冲区引用
            with self.lock:
                if token not in self.commands:
                    return
                stdout_buffer = self.commands[token]["stdout_buffer"]
                stderr_buffer = self.commands[token]["stderr_buffer"]

            # 处理 Python 路径环境变量
            env = None
            python_path = os.environ.get(ENV_PYTHON_PATH)
            if python_path and os.path.isfile(python_path):
                env = os.environ.copy()
                python_dir = os.path.dirname(python_path)
                env["PATH"] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"

            # 使用新的执行器执行命令（支持 PTY 降级）
            result = execute_with_pty_fallback(
                command=command,
                stdout_buffer=stdout_buffer,
                stderr_buffer=stderr_buffer,
                use_pty=use_pty,
                working_directory=working_directory,
                env=env,
                timeout=timeout,
            )

            execution_time = time.time() - start_time

            # 更新命令结果
            with self.lock:
                if token in self.commands:
                    # 从缓冲区获取最终输出（用于向后兼容）
                    final_stdout = stdout_buffer.get_all()
                    final_stderr = stderr_buffer.get_all()
                    
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": final_stdout,
                            "stderr": final_stderr,
                            "exit_code": result["exit_code"],
                            "execution_time": execution_time,
                            "timeout_occurred": result["timeout_occurred"],
                            "pty_used": result["pty_used"],
                            "pty_fallback": result["pty_fallback"],
                            "fallback_reason": result.get("fallback_reason", ""),
                        }
                    )

        except Exception as e:
            # 处理其他异常
            logger.error(f"Command execution error: {e}")
            execution_time = time.time() - start_time
            with self.lock:
                if token in self.commands:
                    # 尝试从缓冲区获取已捕获的输出
                    try:
                        stdout_buffer = self.commands[token]["stdout_buffer"]
                        stderr_buffer = self.commands[token]["stderr_buffer"]
                        partial_stdout = stdout_buffer.get_all()
                        partial_stderr = stderr_buffer.get_all()
                    except Exception:
                        partial_stdout = ""
                        partial_stderr = ""
                    
                    self.commands[token].update(
                        {
                            "status": "completed",
                            "stdout": partial_stdout,
                            "stderr": partial_stderr + f"\nError: {str(e)}",
                            "exit_code": -1,
                            "execution_time": execution_time,
                            "timeout_occurred": False,
                        }
                    )

    def query_command_status(
        self,
        token: str,
        stdout_offset: int = 0,
        stderr_offset: int = 0,
    ) -> Dict[str, Any]:
        """
        查询命令执行状态

        Args:
            token: 命令的token
            stdout_offset: stdout 输出偏移量（默认 0，返回全部）
            stderr_offset: stderr 输出偏移量（默认 0，返回全部）

        Returns:
            包含命令状态的字典，包括：
            - token: 命令 token
            - status: 状态 (pending/running/completed/not_found)
            - exit_code: 退出码（完成时）
            - stdout: stdout 输出（从偏移量开始）
            - stderr: stderr 输出（从偏移量开始）
            - stdout_length: stdout 总长度
            - stderr_length: stderr 总长度
            - stdout_truncated: stdout 是否被截断
            - stderr_truncated: stderr 是否被截断
            - execution_time: 执行时间（完成时）
            - timeout_occurred: 是否超时
        """
        with self.lock:
            if token not in self.commands:
                return {
                    "token": token,
                    "status": "not_found",
                    "message": "Token not found",
                }

            cmd_info = self.commands[token]
            
            # 获取缓冲区引用
            stdout_buffer = cmd_info.get("stdout_buffer")
            stderr_buffer = cmd_info.get("stderr_buffer")
            
            # 从缓冲区获取增量输出
            if stdout_buffer is not None:
                stdout_result = stdout_buffer.get_output(offset=stdout_offset)
                stdout_data = stdout_result["data"]
                stdout_length = stdout_result["length"]
                stdout_truncated = stdout_result["truncated"]
            else:
                # 向后兼容：如果没有缓冲区，使用旧的字符串字段
                stdout_data = cmd_info.get("stdout", "")[stdout_offset:]
                stdout_length = len(cmd_info.get("stdout", ""))
                stdout_truncated = False
            
            if stderr_buffer is not None:
                stderr_result = stderr_buffer.get_output(offset=stderr_offset)
                stderr_data = stderr_result["data"]
                stderr_length = stderr_result["length"]
                stderr_truncated = stderr_result["truncated"]
            else:
                # 向后兼容：如果没有缓冲区，使用旧的字符串字段
                stderr_data = cmd_info.get("stderr", "")[stderr_offset:]
                stderr_length = len(cmd_info.get("stderr", ""))
                stderr_truncated = False

            # 构建响应
            response = {
                "token": cmd_info["token"],
                "status": cmd_info["status"],
                "stdout": stdout_data,
                "stderr": stderr_data,
                "stdout_length": stdout_length,
                "stderr_length": stderr_length,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            }
            
            # 添加完成状态的额外字段
            if cmd_info["status"] in ["completed", "pending"]:
                response.update({
                    "exit_code": cmd_info["exit_code"],
                    "execution_time": cmd_info["execution_time"],
                    "timeout_occurred": cmd_info["timeout_occurred"],
                })
            
            return response
