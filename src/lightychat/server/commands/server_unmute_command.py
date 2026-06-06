# lightychat/server/commands/server_unmute_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerUnmuteCommand(ServerBaseCommand):
    name = "unmute"
    brief = "解除用户禁言 - 管理员指令"
    detail = "/unmute <用户ID>  -  解除指定用户的禁言状态。"
    admin_required = True

    def execute(
        self, args: list[str], context: dict[str, Any]
    ) -> list[Message]:
        sender_id = context["sender_id"]
        user_table = context["user_table"]

        if not args:
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="参数不足。用法：/unmute <用户ID>".encode("utf-8"),
            )]

        target_id = args[0].strip()
        target = user_table.get(target_id)
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
                payload="房主不需要禁言管理。".encode("utf-8"),
            )]

        actual_id = target.user_id

        # 解除禁言
        user_table.set_muted(actual_id, False)

        return [
            Message(
                type=MessageType.TYPE_SYSTEM,
                sender_id="",
                receiver_id=actual_id,
                payload="你的禁言已被解除。".encode("utf-8"),
            ),
            Message(
                type=MessageType.TYPE_SYSTEM,
                sender_id="",
                receiver_id=sender_id,
                payload=f"已解除 {actual_id} 的禁言。".encode("utf-8"),
            ),
        ]