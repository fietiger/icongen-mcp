"""
Executors 模块 - 命令执行器

提供不同模式的命令执行器，支持流式输出捕获。
"""

import subprocess
import threading
import time
import os
import logging
from typing import Optional, Dict, Any

from .streaming_buffer import StreamingBuffer

# 尝试导入 pywinpty（仅 Windows 平台可用）
try:
    from winpty import PtyProcess
    PYWINPTY_AVAILABLE = True
except ImportError:
    PYWINPTY_AVAILABLE = False

logger = logging.getLogger(__name__)


class SubprocessExecutor:
    """
    标准 subprocess 模式执行器（带流式输出）
    
    使用 subprocess.Popen 执行命令，通过后台线程实时捕获
    stdout 和 stderr 输出到 StreamingBuffer。
    """
    
    def __init__(self, stdout_buffer: StreamingBuffer, stderr_buffer: StreamingBuffer):
        """
        初始化执行器
        
        Args:
            stdout_buffer: stdout 输出缓冲区
            stderr_buffer: stderr 输出缓冲区
        """
        self._stdout_buffer = stdout_buffer
        self._stderr_buffer = stderr_buffer
        self._process: Optional[subprocess.Popen] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def execute(
        self,
        command: list,
        working_directory: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        使用 subprocess 执行命令（流式捕获输出）
        
        Args:
            command: 要执行的命令列表
            working_directory: 工作目录
            env: 环境变量
            timeout: 超时时间（秒）
            
        Returns:
            {
                "exit_code": int,
                "timeout_occurred": bool
            }
        """
        self._stop_event.clear()
        timeout_occurred = False
        
        try:
            # 启动进程，配置管道捕获输出
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_directory,
                env=env,
            )
            
            # 启动后台线程读取输出
            self._stdout_thread = threading.Thread(
                target=self._read_output,
                args=(self._process.stdout, self._stdout_buffer),
                daemon=True
            )
            self._stderr_thread = threading.Thread(
                target=self._read_output,
                args=(self._process.stderr, self._stderr_buffer),
                daemon=True
            )
            
            self._stdout_thread.start()
            self._stderr_thread.start()
            
            # 等待进程完成或超时
            try:
                exit_code = self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timeout_occurred = True
                self.terminate()
                exit_code = -1
            
            # 等待读取线程完成
            self._stop_event.set()
            if self._stdout_thread.is_alive():
                self._stdout_thread.join(timeout=1.0)
            if self._stderr_thread.is_alive():
                self._stderr_thread.join(timeout=1.0)
            
            return {
                "exit_code": exit_code,
                "timeout_occurred": timeout_occurred
            }
            
        except Exception as e:
            # 确保进程被清理
            self.terminate()
            raise
    
    def _read_output(self, pipe, buffer: StreamingBuffer) -> None:
        """
        后台线程：持续读取管道输出
        
        使用逐行读取方式，将数据写入 StreamingBuffer。
        
        Args:
            pipe: 要读取的管道 (stdout 或 stderr)
            buffer: 目标缓冲区
        """
        try:
            # 逐行读取，直到管道关闭或收到停止信号
            for line in iter(pipe.readline, b''):
                if self._stop_event.is_set() and not line:
                    break
                if line:
                    buffer.write(line)
        except Exception:
            # 忽略读取错误，可能是管道已关闭
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass
    
    def terminate(self) -> None:
        """
        终止执行
        
        停止读取线程并终止进程。
        """
        self._stop_event.set()
        
        if self._process is not None:
            try:
                self._process.terminate()
                # 给进程一点时间优雅退出
                try:
                    self._process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    # 强制杀死
                    self._process.kill()
                    self._process.wait(timeout=1.0)
            except Exception:
                pass


class PtyInitializationError(Exception):
    """PTY 初始化失败异常"""
    pass


class PtyExecutor:
    """
    PTY 模式命令执行器
    
    使用 pywinpty 在伪终端环境中执行命令，支持：
    - 终端交互程序（如进度条）的正确输出
    - ANSI 转义序列的保留
    - 流式输出捕获到 StreamingBuffer
    
    注意：PTY 模式下 stdout 和 stderr 合并为单一输出流。
    """
    
    def __init__(self, stdout_buffer: StreamingBuffer, stderr_buffer: StreamingBuffer):
        """
        初始化执行器
        
        Args:
            stdout_buffer: stdout 输出缓冲区（PTY 模式下所有输出写入此缓冲区）
            stderr_buffer: stderr 输出缓冲区（PTY 模式下不使用，保持为空）
        """
        self._stdout_buffer = stdout_buffer
        self._stderr_buffer = stderr_buffer
        self._process: Optional[Any] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pty_available = PYWINPTY_AVAILABLE
    
    @property
    def is_available(self) -> bool:
        """检查 PTY 是否可用"""
        return self._pty_available

    def _prepare_command(self, command: list) -> str:
        """
        准备要执行的命令
        
        将命令列表转换为 PTY 可执行的命令字符串。
        
        Args:
            command: 命令列表
            
        Returns:
            准备好的命令字符串
        """
        # 将命令列表转换为字符串
        # 对于包含空格的参数，需要加引号
        parts = []
        for part in command:
            if ' ' in part or '"' in part:
                # 转义双引号并用双引号包围
                escaped = part.replace('"', '\\"')
                parts.append(f'"{escaped}"')
            else:
                parts.append(part)
        
        cmd_str = ' '.join(parts)
        
        # 检查第一个参数是否是可执行文件
        first_word = command[0].lower() if command else ''
        
        # 常见的可执行文件
        executable_prefixes = [
            'cmd', 'cmd.exe',
            'powershell', 'powershell.exe', 'pwsh', 'pwsh.exe',
            'python', 'python.exe', 'python3', 'python3.exe',
            'node', 'node.exe',
            'git', 'git.exe',
            'npm', 'npm.cmd',
            'pip', 'pip.exe',
            'twine',
        ]
        
        # 如果是绝对路径或已知可执行文件，直接使用
        if (first_word.endswith('.exe') or 
            first_word.endswith('.cmd') or
            first_word.endswith('.bat') or
            os.path.basename(first_word) in executable_prefixes or
            os.path.isabs(first_word)):
            return cmd_str
        
        # 否则使用 cmd.exe /c 包装
        return f'cmd.exe /c {cmd_str}'
    
    def execute(
        self,
        command: list,
        working_directory: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        在 PTY 中执行命令
        
        Args:
            command: 要执行的命令列表
            working_directory: 工作目录
            env: 环境变量
            timeout: 超时时间（秒）
            
        Returns:
            {
                "exit_code": int,
                "timeout_occurred": bool,
                "pty_fallback": bool
            }
            
        Raises:
            PtyInitializationError: PTY 初始化失败时抛出
        """
        if not self._pty_available:
            raise PtyInitializationError(
                "pywinpty is not available. Please install it with: pip install pywinpty"
            )
        
        self._stop_event.clear()
        timeout_occurred = False
        start_time = time.time()
        
        try:
            # 准备环境变量
            process_env = os.environ.copy()
            if env:
                process_env.update(env)
            
            # 准备工作目录
            cwd = working_directory or os.getcwd()
            
            # 准备命令
            prepared_command = self._prepare_command(command)
            
            # 使用 pywinpty 启动 PTY 进程
            try:
                self._process = PtyProcess.spawn(prepared_command, cwd=cwd, env=process_env)
            except Exception as e:
                raise PtyInitializationError(f"Failed to spawn PTY process: {e}")
            
            # 启动后台线程读取 PTY 输出
            self._reader_thread = threading.Thread(
                target=self._read_output,
                daemon=True
            )
            self._reader_thread.start()
            
            # 等待进程完成或超时
            exit_code = self._wait_for_completion(timeout, start_time)
            
            if exit_code is None:
                # 超时发生
                timeout_occurred = True
                self.terminate()
                exit_code = -1
            
            # 等待读取线程完成
            self._stop_event.set()
            if self._reader_thread and self._reader_thread.is_alive():
                self._reader_thread.join(timeout=1.0)
            
            return {
                "exit_code": exit_code,
                "timeout_occurred": timeout_occurred,
                "pty_fallback": False
            }
            
        except PtyInitializationError:
            raise
        except Exception as e:
            logger.error(f"PTY execution error: {e}")
            self.terminate()
            raise
    
    def _wait_for_completion(
        self, 
        timeout: Optional[int], 
        start_time: float
    ) -> Optional[int]:
        """
        等待进程完成
        
        Args:
            timeout: 超时时间（秒）
            start_time: 开始时间
            
        Returns:
            进程退出码，如果超时返回 None
        """
        while True:
            # 检查进程是否已结束
            if self._process is not None and not self._process.isalive():
                return self._process.exitstatus or 0
            
            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None
            
            # 短暂休眠，避免 CPU 空转
            time.sleep(0.1)
    
    def _read_output(self) -> None:
        """
        后台线程：持续读取 PTY 输出
        """
        try:
            while not self._stop_event.is_set():
                if self._process is None:
                    break
                    
                try:
                    if not self._process.isalive():
                        # 读取剩余输出
                        try:
                            remaining = self._process.read()
                            if remaining:
                                self._stdout_buffer.write(remaining.encode('utf-8', errors='replace'))
                        except Exception:
                            pass
                        break
                    
                    # 读取可用输出
                    try:
                        data = self._process.read(4096)
                        if data:
                            self._stdout_buffer.write(data.encode('utf-8', errors='replace'))
                    except EOFError:
                        break
                    except Exception:
                        time.sleep(0.01)
                        
                except Exception:
                    break
                    
        except Exception as e:
            logger.debug(f"PTY read thread error: {e}")
    
    def terminate(self) -> None:
        """
        终止执行
        """
        self._stop_event.set()
        
        if self._process is not None:
            try:
                if self._process.isalive():
                    try:
                        self._process.terminate(force=False)
                        time.sleep(0.5)
                    except Exception:
                        pass
                    
                    if self._process.isalive():
                        try:
                            self._process.terminate(force=True)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Error terminating PTY process: {e}")


def execute_with_pty_fallback(
    command: list,
    stdout_buffer: StreamingBuffer,
    stderr_buffer: StreamingBuffer,
    use_pty: bool = True,
    working_directory: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    执行命令，支持 PTY 模式和自动降级
    
    如果请求 PTY 模式但 PTY 初始化失败，将自动降级到 subprocess 模式。
    
    Args:
        command: 要执行的命令列表
        stdout_buffer: stdout 输出缓冲区
        stderr_buffer: stderr 输出缓冲区
        use_pty: 是否使用 PTY 模式（默认 True）
        working_directory: 工作目录
        env: 环境变量
        timeout: 超时时间（秒）
        
    Returns:
        {
            "exit_code": int,
            "timeout_occurred": bool,
            "pty_used": bool,
            "pty_fallback": bool,
            "fallback_reason": str
        }
    """
    pty_fallback = False
    fallback_reason = ""
    
    if use_pty:
        try:
            executor = PtyExecutor(stdout_buffer, stderr_buffer)
            
            if not executor.is_available:
                pty_fallback = True
                fallback_reason = "pywinpty is not installed"
                logger.warning(f"PTY mode requested but not available: {fallback_reason}. Falling back to subprocess.")
            else:
                try:
                    result = executor.execute(
                        command=command,
                        working_directory=working_directory,
                        env=env,
                        timeout=timeout
                    )
                    return {
                        "exit_code": result["exit_code"],
                        "timeout_occurred": result["timeout_occurred"],
                        "pty_used": True,
                        "pty_fallback": False,
                        "fallback_reason": ""
                    }
                except PtyInitializationError as e:
                    pty_fallback = True
                    fallback_reason = str(e)
                    logger.warning(f"PTY initialization failed: {e}. Falling back to subprocess.")
                    
        except Exception as e:
            pty_fallback = True
            fallback_reason = f"Unexpected error: {e}"
            logger.warning(f"PTY execution failed: {e}. Falling back to subprocess.")
    
    # 使用 subprocess 模式
    executor = SubprocessExecutor(stdout_buffer, stderr_buffer)
    result = executor.execute(
        command=command,
        working_directory=working_directory,
        env=env,
        timeout=timeout
    )
    
    return {
        "exit_code": result["exit_code"],
        "timeout_occurred": result["timeout_occurred"],
        "pty_used": False,
        "pty_fallback": pty_fallback,
        "fallback_reason": fallback_reason
    }
