# lightychat/client/command_router.py
from typing import Any, Callable, Dict, Optional

from lightychat.client.commands.base_command import Command
from lightychat.client.message_queue import MessageQueue
from lightychat.common.entities import MessageType


class CommandRouter:
    """聊天室指令路由模块：处理已连接状态下的用户输入。"""

    def __init__(
        self,
        message_queue: MessageQueue,
        user_cache: Callable[[], dict[str, Any]],
        session: Any,                                    # SessionController 实例
        send_chat: Optional[Callable[[str], None]] = None,    # 发送公屏消息的回调
        send_command: Optional[Callable[[str], None]] = None, # 发送指令的回调
    ) -> None:
        self._queue = message_queue
        self._session = session

        # 内部组装 context
        self._context: Dict[str, Any] = {
            "queue": self._queue,
            "user_cache": user_cache,
            "session": self._session,
            "send_chat": send_chat,
            "send_command": send_command,
        }

        # 自动发现聊天室指令
        self._commands: Dict[str, Command] = Command.discover(
            "lightychat.client.commands.chat"
        )
        self._context["_commands"] = self._commands

    def route(self, text: str) -> None:
        """处理用户输入，解析指令名并分发给对应 Command。"""
        text = text.strip()

        # 非指令文本 -> 作为公屏消息发送
        if not text.startswith("/"):
            send_chat = self._context.get("send_chat")
            if send_chat:
                send_chat(text)
            else:
                self._queue.put(
                    "[系统] 网络模块未就绪，无法发送消息。",
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

    # ---------- 后期注入接口 ----------

    def set_send_chat(self, callback: Callable[[str], None]) -> None:
        """注入公屏消息发送回调。"""
        self._context["send_chat"] = callback

    def set_send_command(self, callback: Callable[[str], None]) -> None:
        """注入指令发送回调。"""
        self._context["send_command"] = callback