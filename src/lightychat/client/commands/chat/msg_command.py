# lightychat/client/commands/chat/msg_command.py
from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class MsgCommand(Command):
    name = "msg"
    brief = "发送私聊消息"
    detail = (
        "/msg <用户ID> <消息>\n"
        "  向指定用户发送私聊消息，仅你们两人可见。\n"
        "  示例：/msg Bob 你好，能听到吗？"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        send_command = context.get("send_command")

        if len(args) < 2:
            queue.put(
                "[系统] 参数不足。用法：/msg <用户ID> <消息>",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        target_id = args[0]
        # 将剩余部分拼接为消息内容，保持原样（含空格）
        message_text = " ".join(args[1:])

        # 消息内容不能是纯空白
        if not message_text.strip():
            queue.put(
                "[系统] 消息内容不能为空或纯空白。",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        if send_command is None:
            queue.put("[系统] 网络模块未就绪。", MessageType.TYPE_LOCAL_ERROR)
            return

        # 发送完整指令到服务端
        send_command(f"/msg {target_id} {message_text}")