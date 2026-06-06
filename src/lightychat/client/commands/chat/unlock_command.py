# lightychat/client/commands/chat/unlock_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class UnlockCommand(Command):
    name = "unlock"
    brief = "解锁房间 - 管理员指令"
    detail = (
        "/unlock\n"
        "  解锁聊天室，恢复新用户加入的权限。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")
        user_cache = context["user_cache"]

        if args:
            queue.put("[系统] /unlock 不接受参数。", MessageType.TYPE_LOCAL_ERROR)
            return

        user_info = user_cache()
        if not user_info.get("is_host"):
            queue.put("[系统] 权限不足：仅房主可解锁房间。", MessageType.TYPE_LOCAL_ERROR)
            return

        if send_command is None:
            queue.put("[系统] 网络模块未就绪。", MessageType.TYPE_LOCAL_ERROR)
            return

        send_command("/unlock")