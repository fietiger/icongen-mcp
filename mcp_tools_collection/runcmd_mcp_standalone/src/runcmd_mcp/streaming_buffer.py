"""
StreamingBuffer 模块 - 线程安全的流式输出缓冲区

用于在命令执行过程中实时捕获和管理输出数据。
"""

import threading
from typing import Dict, Any


class StreamingBuffer:
    """
    线程安全的流式输出缓冲区
    
    用于存储命令执行过程中产生的实时输出，支持：
    - 线程安全的数据写入
    - 偏移量查询（增量获取）
    - 缓冲区大小限制和自动截断
    """
    
    def __init__(self, max_size: int = 10 * 1024 * 1024):
        """
        初始化缓冲区
        
        Args:
            max_size: 最大缓冲区大小（字节），默认 10MB
        """
        self._buffer: bytearray = bytearray()
        self._lock: threading.Lock = threading.Lock()
        self._max_size: int = max_size
        self._truncated: bool = False
        self._truncated_bytes: int = 0
    
    def write(self, data: bytes) -> None:
        """
        写入数据到缓冲区
        
        线程安全地将数据追加到缓冲区。如果追加后超过最大大小，
        将截断旧数据，保留最新数据。
        
        Args:
            data: 要写入的字节数据
        """
        if not data:
            return
            
        with self._lock:
            self._buffer.extend(data)
            
            # 检查是否超过最大大小，需要截断
            if len(self._buffer) > self._max_size:
                overflow = len(self._buffer) - self._max_size
                # 截断旧数据，保留最新的 max_size 字节
                del self._buffer[:overflow]
                self._truncated = True
                self._truncated_bytes += overflow
    
    def get_output(self, offset: int = 0) -> Dict[str, Any]:
        """
        获取从指定偏移量开始的输出
        
        Args:
            offset: 起始偏移量，默认为 0（返回全部）
            
        Returns:
            包含以下字段的字典：
            - data: str - 输出内容（UTF-8 解码，错误时替换）
            - length: int - 当前缓冲区总长度
            - truncated: bool - 是否发生过截断
            - truncated_bytes: int - 被截断的字节数
        """
        with self._lock:
            current_length = len(self._buffer)
            
            # 如果偏移量超过当前长度，返回空数据
            if offset >= current_length:
                data = ""
            else:
                # 确保偏移量非负
                safe_offset = max(0, offset)
                data = self._buffer[safe_offset:].decode('utf-8', errors='replace')
            
            return {
                "data": data,
                "length": current_length,
                "truncated": self._truncated,
                "truncated_bytes": self._truncated_bytes
            }
    
    def get_all(self) -> str:
        """
        获取全部输出内容
        
        Returns:
            缓冲区中的全部内容（UTF-8 解码）
        """
        with self._lock:
            return self._buffer.decode('utf-8', errors='replace')
    
    @property
    def length(self) -> int:
        """
        当前缓冲区长度
        
        Returns:
            缓冲区中的字节数
        """
        with self._lock:
            return len(self._buffer)
    
    @property
    def truncated(self) -> bool:
        """
        是否发生过截断
        
        Returns:
            如果缓冲区曾经因超过最大大小而截断，返回 True
        """
        with self._lock:
            return self._truncated
    
    @property
    def truncated_bytes(self) -> int:
        """
        被截断的字节数
        
        Returns:
            累计被截断的字节数
        """
        with self._lock:
            return self._truncated_bytes
    
    def clear(self) -> None:
        """
        清空缓冲区
        
        重置缓冲区内容和截断状态。
        """
        with self._lock:
            self._buffer.clear()
            self._truncated = False
            self._truncated_bytes = 0
