# lightychat/server/message_router.py
from __future__ import annotations

import logging
from typing import Any, Optional

from lightychat.common.entities import Message, MessageType
from lightychat.server.user_table import UserTable
from lightychat.server.command_handler import CommandHandler

logger = logging.getLogger(__name__)


class MessageRouter:
    """消息路由器：根据消息类型和接收方决定投递范围。"""

    def __init__(
        self,
        user_table: UserTable,
        command_handler: CommandHandler,
        message_logger: Optional[Any] = None,
    ) -> None:
        self._user_table = user_table
        self._command_handler = command_handler
        self._logger = message_logger

    # ---------- 公开接口 ----------

    def handle_message(self, msg: Message, sender_id: str, sender_sender: Any) -> None:
        """处理从客户端收到的消息。"""
        self._user_table.update_active(sender_id)

        if msg.type == MessageType.TYPE_MESSAGE:
            self._handle_chat_message(msg, sender_id, sender_sender)
        elif msg.type == MessageType.TYPE_COMMAND:
            self._handle_command(msg, sender_id, sender_sender)
        elif msg.type == MessageType.TYPE_HEARTBEAT:
            self._handle_heartbeat(msg, sender_id, sender_sender)

    def broadcast_system_message(self, text: str) -> None:
        """向所有在线用户广播系统消息。"""
        system_msg = Message(
            type=MessageType.TYPE_SYSTEM,
            sender_id="",
            receiver_id="",
            payload=text.encode("utf-8"),
        )
        for user in self._user_table.get_all():
            if user.sender:
                user.sender.send(system_msg)

    # ---------- 内部处理 ----------

    def _handle_chat_message(self, msg: Message, sender_id: str, sender_sender: Any) -> None:
        user = self._user_table.get(sender_id)
        if user and user.is_muted:
            resp = Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="您已被禁言，无法发送消息。".encode("utf-8"),
            )
            sender_sender.send(resp)
            return

        deliver_msg = Message(
            type=MessageType.TYPE_MESSAGE_DELIVER,
            sender_id=sender_id,
            receiver_id=msg.receiver_id,
            payload=msg.payload,
        )

        if msg.receiver_id == "" or msg.receiver_id == "ALL":
            for user in self._user_table.get_all():
                if user.sender:
                    user.sender.send(deliver_msg)
            self._log_event(f"公屏 {sender_id}: {msg.payload.decode('utf-8', errors='replace')}")
        else:
            target = self._user_table.get(msg.receiver_id)
            if target and target.sender:
                target.sender.send(deliver_msg)
                sender_sender.send(deliver_msg)
            else:
                resp = Message(
                    type=MessageType.TYPE_RESPONSE,
                    sender_id="",
                    receiver_id=sender_id,
                    payload=f"用户 '{msg.receiver_id}' 不在线。".encode("utf-8"),
                )
                sender_sender.send(resp)

    def _handle_command(self, msg: Message, sender_id: str, sender_sender: Any) -> None:
        if self._command_handler:
            results = self._command_handler.handle(msg, sender_id, sender_sender)

            for result_msg in results:
                if result_msg.receiver_id == "":
                    # 广播给所有人
                    for user in self._user_table.get_all():
                        if user.sender:
                            user.sender.send(result_msg)
                else:
                    # 单播给指定用户
                    target = self._user_table.get(result_msg.receiver_id)
                    if target and target.sender:
                        target.sender.send(result_msg)
        else:
            resp = Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id=sender_id,
                payload="指令功能尚未实现。".encode("utf-8"),
            )
            sender_sender.send(resp)

    def _handle_heartbeat(self, msg: Message, sender_id: str, sender_sender: Any) -> None:
        pong = Message(
            type=MessageType.TYPE_HEARTBEAT_ACK,
            sender_id="",
            receiver_id="",
            payload=b"",
        )
        sender_sender.send(pong)

    def _log_event(self, text: str) -> None:
        if self._logger:
            self._logger.log(text)