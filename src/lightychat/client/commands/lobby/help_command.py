# lightychat/client/commands/lobby/help_command.py
from typing import Any

from lightychat.client.commands.base_command import Command


class HelpCommand(Command):
    name = "help"
    brief = "查看帮助信息，可携带指令名参数，如\"/help help\""
    detail = (
        "/help [指令名]\n"
        "  无参数时显示所有可用指令的简介。\n"
        "  带参数时显示指定指令的详细语法。\n"
        "  示例：/help create"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        commands: dict[str, Command] = context["_commands"]

        if not args:
            lines = ["可用指令："]
            for name, cmd in sorted(commands.items()):
                lines.append(f"  /{name:<10} {cmd.brief}")
            queue.put("\n".join(lines))
            return

        target = args[0].lower()
        cmd = commands.get(target)
        if cmd is None:
            queue.put(
                f"[系统] 没有关于 '/{target}' 的帮助信息。"
                f"输入 /help 查看可用指令列表。"
            )
        elif not cmd.detail:
            queue.put(f"[系统] '/{target}' 暂无详细帮助信息。")
        else:
            queue.put(cmd.detail)