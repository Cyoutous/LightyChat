# lightychat/client/commands/chat/clear_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class ClearCommand(Command):
    name = "clear"
    brief = "清空消息区域"
    detail = (
        "/clear\n"
        "  清空当前屏幕上的所有聊天消息。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        # 留待 TerminalUI 重构后实现
        # 届时 TerminalUI 应在消息队列中检测 "__CLEAR__" 标记并清屏
        queue.put("[系统] 清屏功能暂未实现。", MessageType.TYPE_LOCAL_INFO)