# lightychat/server/commands/base_command.py
from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, List

from lightychat.common.entities import Message


class ServerBaseCommand(ABC):
    """服务端指令抽象基类。子类必须定义 name 类属性并实现 execute 方法。"""

    name: str = ""
    brief: str = ""   # 简介，供 /help 使用（服务端也可能需要）
    detail: str = ""  # 详细帮助

    @abstractmethod
    def execute(self, args: list[str], context: dict[str, Any]) -> List[Message]:
        """
        执行指令。

        context 包含以下键（由 CommandHandler 注入）：
            - "user_table":      UserTable      # 在线用户表
            - "connection":      ConnectionManager  # 连接管理器（踢人/锁房）
            - "router":          MessageRouter      # 消息路由器（广播/单播）
            - "sender_id":       str                # 指令发送者的用户ID
            - "sender_sender":   Sender             # 发送者对应的 Sender 实例
            - "is_host":         bool               # 发送者是否为房主
        """
        ...

    @classmethod
    def discover(cls, package_path: str) -> Dict[str, "ServerBaseCommand"]:
        """扫描指定包路径，动态导入所有子模块，返回 {指令名: 指令实例} 字典。"""
        package = importlib.import_module(package_path)
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            full_name = f"{package_path}.{module_name}"
            try:
                importlib.import_module(full_name)
            except Exception:
                pass

        commands: Dict[str, "ServerBaseCommand"] = {}
        for subclass in cls._get_all_subclasses(ServerBaseCommand):
            if subclass.name:
                module_path = subclass.__module__
                if module_path.startswith(package_path):
                    commands[subclass.name] = subclass()
        return commands

    @staticmethod
    def _get_all_subclasses(base_class: Type["ServerBaseCommand"]) -> list[Type["ServerBaseCommand"]]:
        subclasses = base_class.__subclasses__()
        result: list[Type["ServerBaseCommand"]] = []
        for sub in subclasses:
            result.append(sub)
            result.extend(ServerBaseCommand._get_all_subclasses(sub))
        return result