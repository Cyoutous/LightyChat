# lightychat/client/commands/lobby/help_command.py
from typing import Any

from lightychat.client.commands.base_command import Command


class HelpCommand(Command):
    name = "help"

    # 帮助文本直接作为类属性维护，方便后续扩展为从文件加载
    _OVERVIEW = """可用指令：
/create  <房间名> <你的昵称> <端口>  创建新聊天室
/join    <你的昵称> <地址:端口>      加入已有聊天室
/config  <设置项> <值>               修改默认配置
/help    [指令名]                    查看帮助
/quit                                退出程序"""

    _DETAILS: dict[str, str] = {
        "create": (
            "/create <房间名> <你的昵称> <端口>\n"
            "  创建新聊天室，本机将作为服务器运行。\n"
            "  房间名：UTF-8字符串，1~32字符，含空格需用引号包裹。\n"
            "  昵称  ：仅允许英文字母、数字、下划线，1~16字符。\n"
            "  端口  ：1~65535 之间的整数。\n"
            "  示例：/create \"我的房间\" Alice 8080"
        ),
        "join": (
            "/join <你的昵称> <地址:端口>\n"
            "  加入已有的聊天室。\n"
            "  昵称  ：仅允许英文字母、数字、下划线，1~16字符。\n"
            "  地址  ：可以是局域网 IP（如 192.168.1.5:8080）或内网穿透地址。\n"
            "  示例：/join Bob 192.168.1.5:8080"
        ),
        "config": (
            "/config <设置项> <值>\n"
            "  修改默认配置，修改后自动保存。\n"
            "  可用的设置项：\n"
            "    port      默认端口（1~65535）\n"
            "    nickname  默认昵称（字母、数字、下划线，1~16字符）\n"
            "    roomname  默认房间名（UTF-8，1~32字符）\n"
            "    max_users 默认最大人数（正整数）\n"
            "  示例：/config port 9090"
        ),
        "help": (
            "/help [指令名]\n"
            "  无参数时显示所有可用指令的简介。\n"
            "  带参数时显示指定指令的详细语法。\n"
            "  示例：/help create"
        ),
        "quit": (
            "/quit\n"
            "  直接退出程序，无论当前处于何种状态。"
        ),
    }

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]

        if not args:
            queue.put(self._OVERVIEW)
            return

        target = args[0].lower()
        detail = self._DETAILS.get(target)
        if detail is None:
            queue.put(f"[系统] 没有关于 '/{target}' 的帮助信息。输入 /help 查看可用指令列表。")
        else:
            queue.put(detail)