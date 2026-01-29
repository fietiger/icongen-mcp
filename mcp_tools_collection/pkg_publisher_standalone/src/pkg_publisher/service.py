"""
pkg-publisher 服务模块 - Python 包构建和发布服务（PTY 版本）

支持实时输出流功能，包括：
- 流式输出捕获
- PTY 模式支持（解决 twine 进度条问题）
- 增量输出查询
"""

import os
import logging
import shutil
import threading
import uuid
import time
from datetime import datetime
from typing import Dict, Optional, List, Any
from pathlib import Path
import requests

from .streaming_buffer import StreamingBuffer
from .executors import execute_with_pty_fallback

__version__ = "0.1.6"

ENV_PYTHON_PATH = "PKG_PUBLISHER_PYTHON_PATH"

# 默认最大缓冲区大小：10MB
DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024

logger = logging.getLogger("pkg-publisher")


def _get_python_executable() -> str:
    """
    获取 Python 可执行文件路径
    
    Returns:
        Python 可执行文件路径
    """
    python_path = os.environ.get(ENV_PYTHON_PATH)
    if python_path and os.path.isfile(python_path):
        logger.info(f"PKG_PUBLISHER_PYTHON_PATH is set to: {python_path}")
        return python_path
    else:
        logger.info("PKG_PUBLISHER_PYTHON_PATH is not set, using default python")
        return "python"


def _get_python_env() -> Optional[dict]:
    """
    获取带有 Python 路径的环境变量

    Returns:
        修改后的环境变量字典，如果未设置则返回 None
    """
    python_path = os.environ.get(ENV_PYTHON_PATH)
    if python_path and os.path.isfile(python_path):
        env = os.environ.copy()
        python_dir = os.path.dirname(python_path)
        env["PATH"] = f"{python_dir}{os.pathsep}{env.get('PATH', '')}"
        return env
    return None


def setup_logging(level: int = logging.INFO) -> None:
    """
    配置日志输出
    
    Args:
        level: 日志级别，默认 INFO
    """
    import tempfile
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    log_file = os.environ.get("PKG_PUBLISHER_LOG_FILE")
    if not log_file:
        log_file = os.path.join(tempfile.gettempdir(), "pkg-publisher.log")
    
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Log file: {log_file}")
    except Exception as e:
        logger.warning(f"Failed to create log file {log_file}: {e}")
    
    logger.setLevel(level)
    
    env_level = os.environ.get("PKG_PUBLISHER_LOG_LEVEL", "").upper()
    if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        logger.setLevel(getattr(logging, env_level))


def get_version() -> str:
    """获取 pkg-publisher 版本号"""
    return __version__


def get_repository_url(repository: str = "pypi") -> str:
    """
    获取 PyPI 仓库 URL

    Args:
        repository: 仓库名称 (pypi 或 testpypi)

    Returns:
        仓库 URL 字符串
    """
    if repository == "testpypi":
        return "https://test.pypi.org/legacy/"
    else:
        return "https://upload.pypi.org/legacy/"


def _clean_build_artifacts(project_path: str) -> None:
    """清理旧的构建产物"""
    build_dir = os.path.join(project_path, "build")
    dist_dir = os.path.join(project_path, "dist")
    egg_info_dirs = list(Path(project_path).glob("*.egg-info"))
    src_egg_info_dirs = list(Path(project_path).glob("src/*.egg-info"))

    for directory in [build_dir, dist_dir] + egg_info_dirs + src_egg_info_dirs:
        if os.path.exists(directory):
            try:
                if os.path.isdir(directory):
                    shutil.rmtree(directory)
                else:
                    os.remove(directory)
                logger.debug(f"Removed: {directory}")
            except Exception as e:
                logger.warning(f"Failed to remove {directory}: {e}")


def _find_dist_files(project_path: str) -> List[str]:
    """查找构建产物文件"""
    dist_dir = os.path.join(project_path, "dist")
    dist_files = []

    if os.path.exists(dist_dir):
        for file in os.listdir(dist_dir):
            if file.endswith((".whl", ".tar.gz")):
                dist_files.append(os.path.join(dist_dir, file))

    return sorted(dist_files)


def _get_package_files(package_path: str) -> List[str]:
    """获取包文件列表"""
    import glob

    if "*" in package_path or "?" in package_path:
        return sorted(glob.glob(package_path))
    else:
        return [package_path] if os.path.exists(package_path) else []


class PkgPublisherService:
    """
    异步包构建和发布服务类
    
    支持实时输出流功能：
    - 流式输出捕获到 StreamingBuffer
    - PTY 模式执行（解决 twine 进度条问题）
    - 增量输出查询（通过偏移量）
    """

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def build_package(
        self,
        project_path: Optional[str] = None,
        clean: bool = True,
        use_pty: bool = True,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
    ) -> str:
        """
        异步构建 Python 包

        Args:
            project_path: 项目路径，默认为当前目录
            clean: 是否清理旧的构建产物
            use_pty: 是否使用 PTY 模式
            max_buffer_size: 最大输出缓冲区大小

        Returns:
            任务执行的token
        """
        token = str(uuid.uuid4())
        
        stdout_buffer = StreamingBuffer(max_size=max_buffer_size)
        stderr_buffer = StreamingBuffer(max_size=max_buffer_size)

        task_info = {
            "token": token,
            "task_type": "build_package",
            "project_path": project_path or os.getcwd(),
            "clean": clean,
            "use_pty": use_pty,
            "status": "pending",
            "start_time": datetime.now(),
            "stdout_buffer": stdout_buffer,
            "stderr_buffer": stderr_buffer,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
            "pty_used": False,
            "pty_fallback": False,
            "fallback_reason": "",
        }

        with self.lock:
            self.tasks[token] = task_info

        thread = threading.Thread(
            target=self._execute_build_package,
            args=(token, project_path, clean, use_pty),
        )
        thread.daemon = True
        thread.start()

        return token

    def publish_package(
        self,
        package_path: Optional[str] = None,
        repository: str = "pypi",
        skip_existing: bool = False,
        project_path: Optional[str] = None,
        use_pty: bool = True,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
    ) -> str:
        """
        异步发布 Python 包

        Args:
            package_path: 包文件路径，默认为 dist/*
            repository: 仓库名称 (pypi 或 testpypi)
            skip_existing: 是否跳过已存在的版本
            project_path: 项目路径
            use_pty: 是否使用 PTY 模式
            max_buffer_size: 最大输出缓冲区大小

        Returns:
            任务执行的token
        """
        token = str(uuid.uuid4())
        
        stdout_buffer = StreamingBuffer(max_size=max_buffer_size)
        stderr_buffer = StreamingBuffer(max_size=max_buffer_size)

        task_info = {
            "token": token,
            "task_type": "publish_package",
            "package_path": package_path,
            "repository": repository,
            "skip_existing": skip_existing,
            "project_path": project_path,
            "use_pty": use_pty,
            "status": "pending",
            "start_time": datetime.now(),
            "stdout_buffer": stdout_buffer,
            "stderr_buffer": stderr_buffer,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
            "pty_used": False,
            "pty_fallback": False,
            "fallback_reason": "",
        }

        with self.lock:
            self.tasks[token] = task_info

        thread = threading.Thread(
            target=self._execute_publish_package,
            args=(token, package_path, repository, skip_existing, project_path, use_pty),
        )
        thread.daemon = True
        thread.start()

        return token

    def validate_package(
        self,
        package_path: str,
        use_pty: bool = True,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
    ) -> str:
        """
        异步验证 Python 包

        Args:
            package_path: 包文件路径
            use_pty: 是否使用 PTY 模式
            max_buffer_size: 最大输出缓冲区大小

        Returns:
            任务执行的token
        """
        token = str(uuid.uuid4())
        
        stdout_buffer = StreamingBuffer(max_size=max_buffer_size)
        stderr_buffer = StreamingBuffer(max_size=max_buffer_size)

        task_info = {
            "token": token,
            "task_type": "validate_package",
            "package_path": package_path,
            "use_pty": use_pty,
            "status": "pending",
            "start_time": datetime.now(),
            "stdout_buffer": stdout_buffer,
            "stderr_buffer": stderr_buffer,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
            "pty_used": False,
            "pty_fallback": False,
            "fallback_reason": "",
        }

        with self.lock:
            self.tasks[token] = task_info

        thread = threading.Thread(
            target=self._execute_validate_package,
            args=(token, package_path, use_pty),
        )
        thread.daemon = True
        thread.start()

        return token

    def get_package_info(
        self,
        package_name: str,
        version: Optional[str] = None,
        repository: str = "pypi",
    ) -> str:
        """
        异步获取 Python 包信息

        Args:
            package_name: 包名
            version: 版本号（可选）
            repository: 仓库名称 (pypi 或 testpypi)

        Returns:
            任务执行的token
        """
        token = str(uuid.uuid4())

        task_info = {
            "token": token,
            "task_type": "get_package_info",
            "package_name": package_name,
            "version": version,
            "repository": repository,
            "status": "pending",
            "start_time": datetime.now(),
            "stdout_buffer": StreamingBuffer(),
            "stderr_buffer": StreamingBuffer(),
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "execution_time": None,
        }

        with self.lock:
            self.tasks[token] = task_info

        thread = threading.Thread(
            target=self._execute_get_package_info,
            args=(token, package_name, version, repository),
        )
        thread.daemon = True
        thread.start()

        return token


    def _execute_build_package(
        self, token: str, project_path: Optional[str], clean: bool, use_pty: bool
    ):
        """在单独线程中执行包构建"""
        start_time = time.time()

        try:
            with self.lock:
                if token in self.tasks:
                    self.tasks[token]["status"] = "running"
                    # 预设 pty_used 为 use_pty（实际值会在执行后更新）
                    self.tasks[token]["pty_used"] = use_pty
                    stdout_buffer = self.tasks[token]["stdout_buffer"]
                    stderr_buffer = self.tasks[token]["stderr_buffer"]

            if project_path is None:
                project_path = os.getcwd()
            project_path = os.path.abspath(project_path)
            
            logger.info(f"Building package in: {project_path}")

            if not os.path.isdir(project_path):
                error_msg = f"Project path does not exist: {project_path}"
                logger.error(error_msg)
                self._complete_task(token, start_time, -1, error_msg)
                return

            if clean:
                _clean_build_artifacts(project_path)

            python_executable = _get_python_executable()
            env_vars = _get_python_env()
            
            cmd = [python_executable, "-m", "build"]
            
            result = execute_with_pty_fallback(
                command=cmd,
                stdout_buffer=stdout_buffer,
                stderr_buffer=stderr_buffer,
                use_pty=use_pty,
                working_directory=project_path,
                env=env_vars,
                timeout=600,  # 10分钟超时
            )

            execution_time = time.time() - start_time
            dist_files = _find_dist_files(project_path)

            with self.lock:
                if token in self.tasks:
                    self.tasks[token].update({
                        "status": "completed",
                        "stdout": stdout_buffer.get_all(),
                        "stderr": stderr_buffer.get_all(),
                        "exit_code": result["exit_code"],
                        "execution_time": execution_time,
                        "pty_used": result["pty_used"],
                        "pty_fallback": result["pty_fallback"],
                        "fallback_reason": result.get("fallback_reason", ""),
                        "result_data": {
                            "success": result["exit_code"] == 0,
                            "dist_files": dist_files,
                            "project_path": project_path,
                        },
                    })

        except Exception as e:
            logger.error(f"Build failed with exception: {e}")
            self._complete_task(token, start_time, -1, str(e))

    def _execute_publish_package(
        self,
        token: str,
        package_path: Optional[str],
        repository: str,
        skip_existing: bool,
        project_path: Optional[str],
        use_pty: bool,
    ):
        """在单独线程中执行包发布"""
        start_time = time.time()

        try:
            with self.lock:
                if token in self.tasks:
                    self.tasks[token]["status"] = "running"
                    # 预设 pty_used 为 use_pty（实际值会在执行后更新）
                    self.tasks[token]["pty_used"] = use_pty
                    stdout_buffer = self.tasks[token]["stdout_buffer"]
                    stderr_buffer = self.tasks[token]["stderr_buffer"]

            logger.info(f"Publishing to {repository}")

            # 确定包文件路径
            if package_path is None:
                if project_path is None:
                    project_path = os.getcwd()
                dist_dir = os.path.join(project_path, "dist")
                if os.path.exists(dist_dir):
                    package_path = os.path.join(dist_dir, "*")
                else:
                    error_msg = f"dist directory not found: {dist_dir}"
                    logger.error(error_msg)
                    self._complete_task(token, start_time, -1, error_msg)
                    return

            python_executable = _get_python_executable()
            env_vars = _get_python_env()
            repository_url = get_repository_url(repository)
            
            # 获取 API Token
            if repository == "testpypi":
                api_token = os.environ.get("TEST_PYPI_API_TOKEN")
                token_env_name = "TEST_PYPI_API_TOKEN"
            else:
                api_token = os.environ.get("PYPI_API_TOKEN")
                token_env_name = "PYPI_API_TOKEN"
            
            # 构建 twine 命令
            cmd = [
                python_executable,
                "-m",
                "twine",
                "upload",
                package_path,
                "--repository-url",
                repository_url,
                "--non-interactive",
            ]
            
            # 如果有 API Token，添加认证参数
            if api_token:
                cmd.extend(["--username", "__token__", "--password", api_token])
                logger.info(f"Using API token from {token_env_name}")
            else:
                logger.warning(f"{token_env_name} not set, twine will use .pypirc or fail")

            if skip_existing:
                cmd.append("--skip-existing")

            result = execute_with_pty_fallback(
                command=cmd,
                stdout_buffer=stdout_buffer,
                stderr_buffer=stderr_buffer,
                use_pty=use_pty,
                working_directory=project_path,
                env=env_vars,
                timeout=300,  # 5分钟超时
            )

            execution_time = time.time() - start_time
            package_files = _get_package_files(package_path)

            with self.lock:
                if token in self.tasks:
                    self.tasks[token].update({
                        "status": "completed",
                        "stdout": stdout_buffer.get_all(),
                        "stderr": stderr_buffer.get_all(),
                        "exit_code": result["exit_code"],
                        "execution_time": execution_time,
                        "pty_used": result["pty_used"],
                        "pty_fallback": result["pty_fallback"],
                        "fallback_reason": result.get("fallback_reason", ""),
                        "result_data": {
                            "success": result["exit_code"] == 0,
                            "repository": repository,
                            "package_files": package_files,
                        },
                    })

        except Exception as e:
            logger.error(f"Publish failed with exception: {e}")
            self._complete_task(token, start_time, -1, str(e))

    def _execute_validate_package(self, token: str, package_path: str, use_pty: bool):
        """在单独线程中执行包验证"""
        start_time = time.time()

        try:
            with self.lock:
                if token in self.tasks:
                    self.tasks[token]["status"] = "running"
                    # 预设 pty_used 为 use_pty（实际值会在执行后更新）
                    self.tasks[token]["pty_used"] = use_pty
                    stdout_buffer = self.tasks[token]["stdout_buffer"]
                    stderr_buffer = self.tasks[token]["stderr_buffer"]

            logger.info(f"Validating package: {package_path}")

            if not os.path.exists(package_path):
                error_msg = f"Package file not found: {package_path}"
                logger.error(error_msg)
                self._complete_task(token, start_time, -1, error_msg)
                return

            python_executable = _get_python_executable()
            env_vars = _get_python_env()
            
            cmd = [python_executable, "-m", "twine", "check", package_path]

            result = execute_with_pty_fallback(
                command=cmd,
                stdout_buffer=stdout_buffer,
                stderr_buffer=stderr_buffer,
                use_pty=use_pty,
                env=env_vars,
                timeout=60,
            )

            execution_time = time.time() - start_time

            with self.lock:
                if token in self.tasks:
                    self.tasks[token].update({
                        "status": "completed",
                        "stdout": stdout_buffer.get_all(),
                        "stderr": stderr_buffer.get_all(),
                        "exit_code": result["exit_code"],
                        "execution_time": execution_time,
                        "pty_used": result["pty_used"],
                        "pty_fallback": result["pty_fallback"],
                        "fallback_reason": result.get("fallback_reason", ""),
                        "result_data": {
                            "success": result["exit_code"] == 0,
                            "package_path": package_path,
                        },
                    })

        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            self._complete_task(token, start_time, -1, str(e))


    def _execute_get_package_info(
        self,
        token: str,
        package_name: str,
        version: Optional[str],
        repository: str,
    ):
        """在单独线程中获取包信息"""
        start_time = time.time()

        try:
            with self.lock:
                if token in self.tasks:
                    self.tasks[token]["status"] = "running"

            logger.info(f"Getting package info: {package_name}")

            if repository == "testpypi":
                base_url = "https://test.pypi.org/pypi"
            else:
                base_url = "https://pypi.org/pypi"

            if version:
                url = f"{base_url}/{package_name}/{version}/json"
            else:
                url = f"{base_url}/{package_name}/json"

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            execution_time = time.time() - start_time

            with self.lock:
                if token in self.tasks:
                    self.tasks[token].update({
                        "status": "completed",
                        "stdout": "",
                        "stderr": "",
                        "exit_code": 0,
                        "execution_time": execution_time,
                        "result_data": {
                            "success": True,
                            "package_name": package_name,
                            "version": version,
                            "info": data,
                        },
                    })

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get package info: {e}"
            logger.error(error_msg)
            self._complete_task(token, start_time, -1, error_msg, {
                "success": False,
                "package_name": package_name,
                "version": version,
                "info": {},
            })
        except Exception as e:
            error_msg = f"Failed to get package info with exception: {e}"
            logger.error(error_msg)
            self._complete_task(token, start_time, -1, error_msg, {
                "success": False,
                "package_name": package_name,
                "version": version,
                "info": {},
            })

    def _complete_task(
        self,
        token: str,
        start_time: float,
        exit_code: int,
        error_msg: str,
        result_data: Optional[Dict] = None,
    ):
        """完成任务并更新状态"""
        execution_time = time.time() - start_time
        with self.lock:
            if token in self.tasks:
                stdout_buffer = self.tasks[token].get("stdout_buffer")
                stderr_buffer = self.tasks[token].get("stderr_buffer")
                
                self.tasks[token].update({
                    "status": "completed",
                    "stdout": stdout_buffer.get_all() if stdout_buffer else "",
                    "stderr": (stderr_buffer.get_all() if stderr_buffer else "") + f"\n{error_msg}",
                    "exit_code": exit_code,
                    "execution_time": execution_time,
                    "result_data": result_data or {"success": False, "error": error_msg},
                })

    def query_task_status(
        self,
        token: str,
        stdout_offset: int = 0,
        stderr_offset: int = 0,
    ) -> Dict[str, Any]:
        """
        查询任务执行状态

        Args:
            token: 任务的token
            stdout_offset: stdout 输出偏移量（默认 0，返回全部）
            stderr_offset: stderr 输出偏移量（默认 0，返回全部）

        Returns:
            包含任务状态的字典
        """
        with self.lock:
            if token not in self.tasks:
                return {
                    "token": token,
                    "status": "not_found",
                    "message": "Token not found",
                }

            task_info = self.tasks[token]
            
            # 获取缓冲区引用
            stdout_buffer = task_info.get("stdout_buffer")
            stderr_buffer = task_info.get("stderr_buffer")
            
            # 从缓冲区获取增量输出
            if stdout_buffer is not None:
                stdout_result = stdout_buffer.get_output(offset=stdout_offset)
                stdout_data = stdout_result["data"]
                stdout_length = stdout_result["length"]
                stdout_truncated = stdout_result["truncated"]
            else:
                stdout_data = task_info.get("stdout", "")[stdout_offset:]
                stdout_length = len(task_info.get("stdout", ""))
                stdout_truncated = False
            
            if stderr_buffer is not None:
                stderr_result = stderr_buffer.get_output(offset=stderr_offset)
                stderr_data = stderr_result["data"]
                stderr_length = stderr_result["length"]
                stderr_truncated = stderr_result["truncated"]
            else:
                stderr_data = task_info.get("stderr", "")[stderr_offset:]
                stderr_length = len(task_info.get("stderr", ""))
                stderr_truncated = False

            response = {
                "token": task_info["token"],
                "status": task_info["status"],
                "task_type": task_info["task_type"],
                "stdout": stdout_data,
                "stderr": stderr_data,
                "stdout_length": stdout_length,
                "stderr_length": stderr_length,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            }
            
            if task_info["status"] in ["completed", "pending"]:
                response.update({
                    "exit_code": task_info["exit_code"],
                    "execution_time": task_info["execution_time"],
                    "result_data": task_info.get("result_data"),
                })
            
            # 添加 PTY 相关信息
            if "pty_used" in task_info:
                response["pty_used"] = task_info["pty_used"]
                response["pty_fallback"] = task_info.get("pty_fallback", False)
                response["fallback_reason"] = task_info.get("fallback_reason", "")
            
            return response
