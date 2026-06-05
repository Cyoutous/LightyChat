# lightychat/server/commands/server_unlock_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerUnlockCommand(ServerBaseCommand):
    name = "unlock"
    brief = "解锁房间 - 管理员指令"
    detail = "/unlock  -  解锁聊天室，恢复新用户加入的权限。"
    admin_required = True # 管理员指令

    def execute(
        self, args: list[str], context: dict[str, Any]
    ) -> list[Message]:
        connection = context["connection"]

        # 解锁房间
        connection.set_locked(False)

        # 返回广播消息
        return [Message(
            type=MessageType.TYPE_SYSTEM,
            sender_id="",
            receiver_id="",  # 广播
            payload="聊天室已解锁，新用户可以加入。".encode("utf-8"),
        )]