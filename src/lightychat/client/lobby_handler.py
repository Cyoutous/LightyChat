from typing import Any, Callable, Dict, Optional

from lightychat.client.commands.base_command import Command
from lightychat.client.message_queue import MessageQueue
from lightychat.common.entities import MessageType
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
        self._queue = message_queue
        self._settings = settings

        self._context: Dict[str, Any] = {
            "queue": self._queue,
            "settings": self._settings,
            "on_create": on_create,
            "on_join": on_join,
        }

        self._commands: Dict[str, Command] = Command.discover(
            "lightychat.client.commands.lobby"
        )
        self._context["_commands"] = self._commands

    # ---------- 公开接口 ----------

    def handle(self, text: str) -> None:
        text = text.strip()

        if not text.startswith("/"):
            self._queue.put(
                "[系统] 大厅中不能发送聊天消息。输入 /help 查看可用指令。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        parts = text[1:].split()
        if not parts:
            self._queue.put(
                "[系统] 请输入指令。输入 /help 查看可用指令。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        cmd_name = parts[0].lower()
        args = parts[1:]

        command = self._commands.get(cmd_name)
        if command is None:
            self._queue.put(
                f"[系统] 未知指令：/{cmd_name}。输入 /help 查看可用指令。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        try:
            command.execute(args, self._context)
        except Exception as e:
            self._queue.put(
                f"[系统] 指令执行出错：{e}",
                MessageType.TYPE_LOCAL_ERROR,
            )

    def set_on_create(
        self, callback: Callable[[str, int, str, str], None]
    ) -> None:
        self._context["on_create"] = callback

    def set_on_join(self, callback: Callable[[str, str], None]) -> None:
        self._context["on_join"] = callback