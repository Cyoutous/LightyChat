# lightychat/server/commands/server_msg_command.py
from typing import Any

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand


class ServerMsgCommand(ServerBaseCommand):
    name = "msg"
    brief = "发送私聊消息"
    detail = "/msg <用户ID> <消息> - 向指定用户发送私聊消息，仅你们两人可见。"

    def execute(
        self, args: list[str], context: dict[str, Any]
    ) -> list[Message]:
        sender_id = context["sender_id"]
        user_table = context["user_table"]

        # 检查发送者是否被禁言
        sender = user_table.get(sender_id)
        if sender and sender.is_muted:
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="您已被禁言，无法发送消息。".encode("utf-8"),
            )]

        if len(args) < 2:
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="参数不足。用法：/msg <用户ID> <消息>".encode("utf-8"),
            )]

        target_id = args[0]
        message_text = " ".join(args[1:])

        if not message_text.strip():
            return [Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="消息内容不能为空。".encode("utf-8"),
            )]

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

        actual_target_id = target.user_id

        # 给接收方的消息：[发送方id悄悄对你说] 消息内容
        private_msg = Message(
            type=MessageType.TYPE_PRIVATE_DELIVER,
            sender_id=sender_id,
            receiver_id=actual_target_id,
            payload=f"[{sender_id}悄悄对你说] {message_text}".encode("utf-8"),
        )

        # 回显给发送方：[你悄悄对接收方id说] 消息内容
        echo_msg = Message(
            type=MessageType.TYPE_PRIVATE_DELIVER,
            sender_id=sender_id,
            receiver_id=sender_id,
            payload=f"[你悄悄对{actual_target_id}说] {message_text}".encode("utf-8"),
        )

        return [private_msg, echo_msg]