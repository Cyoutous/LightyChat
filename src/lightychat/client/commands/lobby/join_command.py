# lightychat/client/commands/lobby/join_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class JoinCommand(Command):
    name = "join"
    brief = "加入已有聊天室"
    detail = (
        "/join <昵称> <地址:端口>\n"
        "  加入已有的聊天室。\n"
        "  昵称：字母、数字、下划线，1~16字符。\n"
        "  地址：局域网 IP（如 192.168.1.5:8080）或内网穿透地址。\n"
        "  示例：/join Bob 192.168.1.5:8080"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]

        if len(args) < 2:
            queue.put(
                "[系统] 参数不足。/join <昵称> <地址:端口>",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        user_id = args[0]
        address = args[1]

        # 校验昵称
        if not (1 <= len(user_id) <= 16 and all(c.isalnum() or c == "_" for c in user_id)):
            queue.put(
                "[系统] 昵称不合法（仅允许字母、数字、下划线，1~16字符）。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        # 校验地址格式 host:port
        if ":" not in address:
            queue.put(
                "[系统] 地址格式错误。应为 主机:端口，如 192.168.1.5:8080。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        host, _, port_str = address.rpartition(":")
        del host  #tmp
        try:
            port = int(port_str)
        except ValueError:
            queue.put(
                "[系统] 端口必须为整数。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return
        if not (1 <= port <= 65535):
            queue.put(
                "[系统] 端口必须在 1~65535 之间。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        queue.put(
            f"[系统] 正在加入 {address}（昵称 {user_id}）...",
            MessageType.TYPE_LOCAL_INFO,
        )

        # 调用预留的连接回调
        session = context.get("session")
        if session is not None:
            session.join_chat(address, user_id)
        else:
            queue.put(
                "[系统] 加入聊天室功能尚未就绪（session 为空）。",
                MessageType.TYPE_LOCAL_ERROR,
            )