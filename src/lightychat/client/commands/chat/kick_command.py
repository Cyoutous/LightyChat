# lightychat/client/commands/chat/kick_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class KickCommand(Command):
    name = "kick"
    brief = "踢出指定用户 - 管理员指令"
    detail = (
        "/kick <用户ID>\n"
        "  强制断开指定用户的连接，将其移出聊天室。\n"
        "  可使用短ID（数字）或完整ID。\n"
        "  示例：/kick Bob"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")
        user_cache = context["user_cache"]

        if len(args) < 1:
            queue.put(
                "[系统] 参数不足。用法：/kick <用户ID>",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        target_id = args[0].strip()
        if not target_id:
            queue.put(
                "[系统] 用户ID不能为空。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        user_info = user_cache()
        if not user_info.get("is_host"):
            queue.put(
                "[系统] 权限不足：仅房主可踢人。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        if send_command is None:
            queue.put("[系统] 网络模块未就绪。", MessageType.TYPE_LOCAL_ERROR)
            return

        send_command(f"/kick {target_id}")