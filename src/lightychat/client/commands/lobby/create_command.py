import secrets
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class CreateCommand(Command):
    name = "create"
    brief = "创建新聊天室"
    detail = (
        "/create <房间名> <昵称> <端口>\n"
        "  在本机创建新聊天室，自动以房主身份加入。\n"
        "  房间名：UTF-8，1~32字符，含空格需用引号包裹。\n"
        "  昵称  ：字母、数字、下划线，1~16字符。\n"
        "  端口  ：1~65535。\n"
        "  示例：/create \"我的房间\" Alice 8080"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]

        if len(args) < 3:
            queue.put(
                "[系统] 参数不足。/create <房间名> <昵称> <端口>",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        room_name = args[0]
        user_id = args[1]
        port_str = args[2]

        # 校验房间名
        room_name_bytes = room_name.encode("utf-8")
        if not (1 <= len(room_name_bytes) <= 32):
            queue.put(
                "[系统] 房间名长度不合法（UTF-8 编码后 1~32 字节）。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        # 校验昵称
        if not (1 <= len(user_id) <= 16 and all(c.isalnum() or c == "_" for c in user_id)):
            queue.put(
                "[系统] 昵称不合法（仅允许字母、数字、下划线，1~16字符）。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        # 校验端口
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

        # 生成管理令牌
        admin_token = secrets.token_hex(16)

        queue.put(
            f"[系统] 正在创建聊天室 \"{room_name}\"（端口 {port}）...",
            MessageType.TYPE_LOCAL_INFO,
        )

        # 调用预留的连接回调
        session = context.get("session")
        if session is not None:
            session.create_chat("127.0.0.1", port, user_id, admin_token)
        else:
            queue.put(
                "[系统] 创建聊天室功能尚未就绪（session 为空）。",
                MessageType.TYPE_LOCAL_ERROR,
            )