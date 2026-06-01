import importlib
import pkgutil
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

logger = logging.getLogger(__name__)


class Command(ABC):
    """指令抽象基类。子类必须定义 name 类属性并实现 execute 方法。"""

    name: str = ""

    @abstractmethod
    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        """执行指令。

        Args:
            args: 参数列表（不包含指令名本身）。
            context: 执行上下文，包含 message_queue、settings、on_create 回调等。
        """
        ...

    @classmethod
    def discover(cls, package_path: str) -> Dict[str, "Command"]:
        """扫描指定包路径，动态导入所有子模块，返回 {指令名: 指令实例} 字典。

        Args:
            package_path: 包的完整 Python 路径，如 "lightychat.client.commands.lobby"。

        Returns:
            已注册的指令名到指令实例的映射。
        """
        # 1. 动态导入包内所有模块
        package = importlib.import_module(package_path)
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            full_name = f"{package_path}.{module_name}"
            try:
                importlib.import_module(full_name)
            except Exception as e:
                logger.warning(f"跳过无法导入的指令模块 {full_name}: {e}")

        # 2. 收集所有 Command 子类
        commands: Dict[str, "Command"] = {}
        for subclass in cls._get_all_subclasses(Command):
            if subclass.name:
                commands[subclass.name] = subclass()
        return commands

    @staticmethod
    def _get_all_subclasses(base_class: Type["Command"]) -> list[Type["Command"]]:
        """递归获取所有子类。"""
        subclasses = base_class.__subclasses__()
        result: list[Type["Command"]] = []
        for sub in subclasses:
            result.append(sub)
            result.extend(Command._get_all_subclasses(sub))
        return result