# lightychat/client/commands/chat/lock_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class LockCommand(Command):
    name = "lock"
    brief = "锁定房间（房主）"
    detail = (
        "/lock\n"
        "  锁定聊天室，此后新用户无法加入。\n"
        "  房主本人不受影响。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")
        user_cache = context["user_cache"]

        if args:
            queue.put("[系统] /lock 不接受参数。", MessageType.TYPE_LOCAL_ERROR)
            return

        user_info = user_cache()
        if not user_info.get("is_host"):
            queue.put("[系统] 权限不足：仅房主可锁定房间。", MessageType.TYPE_LOCAL_ERROR)
            return

        if send_command is None:
            queue.put("[系统] 网络模块未就绪。", MessageType.TYPE_LOCAL_ERROR)
            return

        send_command("/lock")
        #queue.put("[系统] 房间已锁定，新用户无法加入。", MessageType.TYPE_SYSTEM)
        #不执行上方语句，应该由服务器负责