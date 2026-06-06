# lightychat/server/commands/server_kick_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerKickCommand(ServerBaseCommand):
    name = "kick"
    brief = "踢出指定用户 - 管理员指令"
    detail = "/kick <用户ID>  -  强制断开指定用户的连接。"
    admin_required = True

    def execute(
        self, args: list[str], context: dict[str, Any]
    ) -> list[Message]:
        sender_id = context["sender_id"]
        user_table = context["user_table"]
        connection = context["connection"]

        if not args:
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="参数不足。语法：/kick <用户ID>".encode("utf-8"),
            )]

        target_id = args[0].strip()
        target = user_table.get(target_id)
        # 如果完整 ID 找不到，尝试按短 ID 查找
        if target is None:
            try:
                short_id = int(target_id)
                target = user_table.get_by_short_id(short_id)
            except ValueError:
                pass

        if target is None:
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload=f"用户 '{target_id}' 不在线。".encode("utf-8"),
            )]

        if target.is_host:
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="不能踢出房主自己。".encode("utf-8"),
            )]

        actual_id = target.user_id

        # 断开目标用户连接
        connection.disconnect(actual_id)

        # 广播踢出消息
        return [Message(
            type=MessageType.TYPE_SYSTEM,
            sender_id="",
            receiver_id="",  # 广播
            payload=f"{actual_id} 被 {sender_id} 踢出了聊天室。".encode("utf-8"),
        )]