# lightychat/server/commands/server_list_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerListCommand(ServerBaseCommand):
    name = "list"
    brief = "查看在线用户列表"
    detail = (
        "/list\n"
        "  显示聊天室中所有在线用户。\n"
        "  普通用户看到完整 ID 列表，房主额外看到短 ID 映射。"
    )

    def execute(
        self, args: list[str], context: dict[str, Any]
    ) -> list[Message]:
        user_table = context["user_table"]
        is_host = context["is_host"]
        sender_id = context["sender_id"]

        users = user_table.get_all()

        if not users:
            reply_text = "聊天室中暂无其他用户。"
        elif is_host:
            lines = [f"  [{u.short_id}] {u.user_id}" for u in users]
            reply_text = "在线用户（短ID 映射）：\n" + "\n".join(lines)
        else:
            lines = [f"  {u.user_id}" for u in users]
            reply_text = "在线用户：\n" + "\n".join(lines)

        return [Message(
            type=MessageType.TYPE_RESPONSE,
            sender_id="",
            receiver_id=sender_id,
            payload=reply_text.encode("utf-8"),
        )]