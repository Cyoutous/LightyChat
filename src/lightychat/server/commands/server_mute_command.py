# lightychat/server/commands/server_mute_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerMuteCommand(ServerBaseCommand):
    name = "mute"
    brief = "禁言指定用户 - 管理员指令"
    detail = "/mute <用户ID>  -  禁止指定用户发送消息。"
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
                payload="参数不足。用法：/mute <用户ID>".encode("utf-8"),
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
                payload="不能禁言房主。".encode("utf-8"),
            )]

        actual_id = target.user_id

        # 设置禁言状态
        user_table.set_muted(actual_id, True)

        # 通知目标用户被禁言
        return [
            Message(
                type=MessageType.TYPE_SYSTEM,
                sender_id="",
                receiver_id=actual_id,  # 单播给被禁言用户
                payload="你已被房主禁言。".encode("utf-8"),
            ),
            Message(
                type=MessageType.TYPE_SYSTEM,
                sender_id="",
                receiver_id=sender_id,  # 单播给房主确认
                payload=f"已禁言 {actual_id}。".encode("utf-8"),
            ),
        ]