# lightychat/client/commands/chat/list_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class ListCommand(Command):
    name = "list"
    brief = "查看在线用户列表"
    detail = (
        "/list\n"
        "  显示聊天室中所有在线用户。\n"
        "  普通用户看到完整 ID 列表，房主额外看到短 ID 映射。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")

        # /list 不接受参数
        if args:
            queue.put(
                "[系统] /list 不接受额外参数。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        if send_command is None:
            queue.put(
                "[系统] 网络模块未就绪，无法发送指令。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        # 发送指令请求到服务器
        send_command("/list")
        queue.put("[系统] 正在查询在线用户...", MessageType.TYPE_LOCAL_INFO)