# lightychat/client/commands/chat/exit_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class ExitCommand(Command):
    name = "exit"
    brief = "退出聊天室，返回大厅"
    detail = (
        "/exit\n"
        "  退出当前聊天室，断开连接并返回大厅。\n"
        "  其他用户会收到你离开的系统广播。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")
        session = context.get("session")

        if args:
            queue.put("[系统] /exit 不接受参数。", MessageType.TYPE_LOCAL_ERROR)
            return

        if send_command is not None:
            send_command("/exit")

        queue.put("[系统] 正在退出聊天室...", MessageType.TYPE_LOCAL_INFO)

        if session is not None:
            session.disconnect()