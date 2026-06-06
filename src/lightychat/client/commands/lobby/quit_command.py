from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType

class QuitCommand(Command):
    '''
        仅作信息提示使用，实际执行处在terminal_ui。
    '''

    name = "quit"
    brief = "退出程序"
    detail = (
        f"/quit\n"
        f"直接退出程序。该指令不携带参数。"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]

        if args:
            queue.put(f"[系统] quit指令不能携带参数", MessageType.TYPE_LOCAL_ERROR)
