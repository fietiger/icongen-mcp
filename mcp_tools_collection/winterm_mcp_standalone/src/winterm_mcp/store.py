"""
命令存储管理 - winterm-mcp
"""

import threading
import logging
from typing import Optional
from .models import CommandInfo

logger = logging.getLogger("winterm-mcp")


class CommandStore:
    """
    命令存储管理类，线程安全
    """

    def __init__(self) -> None:
        self._commands: dict[str, CommandInfo] = {}
        self._lock = threading.Lock()

    def add_command(self, token: str, info: CommandInfo) -> None:
        """
        添加命令信息到存储

        Args:
            token: 命令令牌
            info: 命令信息对象
        """
        with self._lock:
            self._commands[token] = info
            logger.debug(f"Added command to store: token={token}")

    def get_command(self, token: str) -> Optional[CommandInfo]:
        """
        获取命令信息

        Args:
            token: 命令令牌

        Returns:
            命令信息对象，如果不存在则返回 None
        """
        with self._lock:
            return self._commands.get(token)

    def remove_command(self, token: str) -> bool:
        """
        移除命令信息

        Args:
            token: 命令令牌

        Returns:
            如果命令存在并被移除返回 True，否则返回 False
        """
        with self._lock:
            if token in self._commands:
                del self._commands[token]
                logger.debug(f"Removed command from store: token={token}")
                return True
            return False

    def get_all_tokens(self) -> list[str]:
        """
        获取所有命令令牌

        Returns:
            令牌列表
        """
        with self._lock:
            return list(self._commands.keys())

    def update_command(self, token: str, **kwargs) -> bool:
        """
        更新命令信息

        Args:
            token: 命令令牌
            **kwargs: 要更新的字段

        Returns:
            如果命令存在并被更新返回 True，否则返回 False
        """
        with self._lock:
            if token in self._commands:
                for key, value in kwargs.items():
                    if hasattr(self._commands[token], key):
                        setattr(self._commands[token], key, value)
                logger.debug(f"Updated command in store: token={token}, fields={list(kwargs.keys())}")
                return True
            return False
