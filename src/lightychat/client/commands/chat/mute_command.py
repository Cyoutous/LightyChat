# lightychat/client/commands/chat/mute_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class MuteCommand(Command):
    name = "mute"
    brief = "禁言指定用户 - 管理员指令"
    detail = (
        "/mute <用户ID>\n"
        "  禁止指定用户发送公屏和私聊消息。\n"
        "  可使用短ID（数字）或完整ID。\n"
        "  示例：/mute Bob"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")
        user_cache = context["user_cache"]

        if len(args) < 1:
            queue.put(
                "[系统] 参数不足。用法：/mute <用户ID>",
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
                "[系统] 权限不足：仅房主可禁言。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        if send_command is None:
            queue.put("[系统] 网络模块未就绪。", MessageType.TYPE_LOCAL_ERROR)
            return

        send_command(f"/mute {target_id}")  