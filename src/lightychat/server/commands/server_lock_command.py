# lightychat/server/commands/server_lock_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerLockCommand(ServerBaseCommand):
    name = "lock"
    brief = "锁定房间 - 管理员指令"
    detail = "/lock  -  锁定聊天室，拒绝新用户加入。"

    def execute(
        self, args: list[str], context: dict[str, Any]
    ) -> list[Message]:
        connection = context["connection"]

        # 锁定房间
        connection.set_locked(True)

        # 返回广播消息
        return [Message(
            type=MessageType.TYPE_SYSTEM,
            sender_id="",
            receiver_id="",  # 广播
            payload="聊天室已被房主锁定，新用户将无法加入。".encode("utf-8"),
        )]