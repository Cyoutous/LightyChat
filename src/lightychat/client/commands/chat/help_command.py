from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class HelpCommand(Command):
    name = "help"
    brief = "查看聊天室可用指令"
    detail = (
        "/help [指令名]\n"
        "  无参数时显示所有可用指令的简介。\n"
        "  带参数时显示指定指令的详细语法。\n"
        "  示例：/help msg"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        commands: dict[str, Command] = context["_commands"]

        if not args:
            lines = ["聊天室可用指令："]
            for name, cmd in sorted(commands.items()):
                lines.append(f"  /{name:<10} {cmd.brief}")
            queue.put("\n".join(lines), MessageType.TYPE_LOCAL_INFO)
            return

        target = args[0].lower()
        cmd = commands.get(target)
        if cmd is None:
            queue.put(
                f"[系统] 没有关于 '/{target}' 的帮助信息。输入 /help 查看可用指令列表。",
                MessageType.TYPE_LOCAL_ERROR,
            )
        elif not cmd.detail:
            queue.put(
                f"[系统] '/{target}' 暂无详细帮助信息。",
                MessageType.TYPE_LOCAL_INFO,
            )
        else:
            queue.put(cmd.detail, MessageType.TYPE_LOCAL_INFO)