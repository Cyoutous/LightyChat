from typing import Any, Callable, Dict, Optional

from lightychat.client.commands.base_command import Command
from lightychat.client.message_queue import MessageQueue
from lightychat.common.settings import Settings


class LobbyHandler:
    """大厅处理模块：管理未连接状态下的用户输入。"""

    def __init__(
        self,
        message_queue: MessageQueue,
        settings: Settings,
        on_create: Optional[Callable[[str, int, str, str], None]] = None,
        on_join: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """
        Args:
            message_queue: 全局消息队列，推送反馈消息。
            settings: 设置模块，读写默认配置。
            on_create: 创建聊天室后的回调。签名：(host, port, user_id, admin_token) -> None。
            on_join: 加入聊天室后的回调。签名：(address, user_id) -> None。
        """
        self._queue = message_queue
        self._settings = settings

        # 指令执行上下文
        self._context: Dict[str, Any] = {
            "queue": self._queue,
            "settings": self._settings,
            "on_create": on_create,
            "on_join": on_join,
        }

        # 自动发现并注册所有大厅指令
        self._commands: Dict[str, Command] = Command.discover(
            "lightychat.client.commands.lobby"
        )

    # ---------- 公开接口 ----------

    def handle(self, text: str) -> None:
        """处理用户输入，解析指令名并分发给对应 Command。

        Args:
            text: 用户输入的原始文本。
        """
        text = text.strip()

        # 非指令文本（不以 "/" 开头）→ 提示用户
        if not text.startswith("/"):
            self._queue.put("[系统] 大厅中不能发送聊天消息。输入 /help 查看可用指令。")
            return

        # 去掉 "/"，按空格分割
        parts = text[1:].split()
        if not parts:
            self._queue.put("[系统] 请输入指令。输入 /help 查看可用指令。")
            return

        cmd_name = parts[0].lower()
        args = parts[1:]

        command = self._commands.get(cmd_name)
        if command is None:
            self._queue.put(
                f"[系统] 未知指令：/{cmd_name}。输入 /help 查看可用指令。"
            )
            return

        try:
            command.execute(args, self._context)
        except Exception as e:
            self._queue.put(f"[系统] 指令执行出错：{e}")

    def set_on_create(
        self, callback: Callable[[str, int, str, str], None]
    ) -> None:
        """注入创建聊天室后的回调。"""
        self._context["on_create"] = callback

    def set_on_join(self, callback: Callable[[str, str], None]) -> None:
        """注入加入聊天室后的回调。"""
        self._context["on_join"] = callback