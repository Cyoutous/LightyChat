# lightychat/client/commands/chat/myid_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class MyIdCommand(Command):
    name = "myid"
    brief = "查看自己当前的用户 ID"
    detail = (
        "/myid\n"
        "  显示你在聊天室中的实际 ID。\n"
        "  如果加入时昵称被服务端自动修改（如重名或房主强制分配），"
        "  可以通过此指令查看最终生效的 ID。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        user_cache = context["user_cache"]
        user_info = user_cache()
        user_id = user_info.get("user_id", "未知")

        queue.put(f"你的 ID：{user_id}", MessageType.TYPE_LOCAL_INFO)