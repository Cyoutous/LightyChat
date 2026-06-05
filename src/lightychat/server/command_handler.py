# lightychat/server/command_handler.py
from __future__ import annotations

import logging
from typing import Any, Dict, List

from lightychat.common.entities import Message, MessageType
from lightychat.server.commands.server_base_command import ServerBaseCommand

logger = logging.getLogger(__name__)


class CommandHandler:
    """服务端指令路由器：解析 TYPE_COMMAND 消息，分发给对应的 ServerBaseCommand 执行。"""

    ADMIN_COMMANDS = {
        "kick", "mute", "unmute", "lock", "unlock",
    }

    def __init__(self, context: Dict[str, Any]) -> None:
        """
        context 必须包含：
            - "user_table":      UserTable           # 在线用户表
            - "connection":      ConnectionManager   # 连接管理器
            - "admin_token":     str                 # 房主令牌
        """
        self._context = context

        self._commands: Dict[str, ServerBaseCommand] = ServerBaseCommand.discover(
            "lightychat.server.commands"
        )

    # ---------- 公开接口 ----------

    def handle(
        self, msg: Message, sender_id: str, sender_sender: Any
    ) -> List[Message]:
        """处理来自客户端的 TYPE_COMMAND 消息。

        Returns:
            需要发送的消息列表。每条消息的 receiver_id 决定发送方式：
            - 空字符串 → 广播给所有人
            - 特定用户ID → 单播给该用户
            - "__DISCONNECT__" → 断开指定用户连接（特殊标记）
        """
        payload_text = msg.payload.decode("utf-8", errors="replace").strip()

        if not payload_text.startswith("/"):
            return [self._error_msg(sender_id, "无效的指令格式")]

        parts = payload_text[1:].split()
        if not parts:
            return [self._error_msg(sender_id, "空指令")]

        cmd_name = parts[0].lower()
        args = parts[1:]

        command = self._commands.get(cmd_name)
        if command is None:
            return [self._error_msg(sender_id, f"未知指令：/{cmd_name}")]

        if cmd_name in self.ADMIN_COMMANDS:
            if not self._verify_admin(sender_id):
                return [self._error_msg(sender_id, "权限不足：仅房主可执行此操作")]

        user_table = self._context["user_table"]
        user = user_table.get(sender_id)
        is_host = user.is_host if user else False

        exec_context: Dict[str, Any] = {
            "user_table": user_table,
            "connection": self._context["connection"],
            "sender_id": sender_id,
            "sender_sender": sender_sender,
            "is_host": is_host,
        }

        try:
            return command.execute(args, exec_context)
        except Exception as e:
            logger.error(f"指令 /{cmd_name} 执行失败: {e}", exc_info=True)
            return [self._error_msg(sender_id, f"指令执行失败：{e}")]
        
    def set_connection(self, connection: Any) -> None:
        """延迟注入连接管理器，避免循环依赖。"""
        self._context["connection"] = connection

    # ---------- 内部 ----------

    def _verify_admin(self, sender_id: str) -> bool:
        user_table = self._context["user_table"]
        user = user_table.get(sender_id)
        return user is not None and user.is_host

    def _error_msg(self, receiver_id: str, reason: str) -> Message:
        """构造错误响应消息，统一格式。"""
        return Message(
            type=MessageType.TYPE_RESPONSE,
            sender_id="",
            receiver_id=receiver_id,
            payload=reason.encode("utf-8"),
        )