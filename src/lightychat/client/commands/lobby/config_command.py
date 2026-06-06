from typing import Any

from lightychat.client.commands.base_command import Command
from lightychat.common.entities import MessageType


class ConfigCommand(Command):
    name = "config"
    brief = "修改默认配置"
    detail = (
        "/config <设置项> <值>\n"
        "  修改默认配置并自动保存。\n"
        "  可用的设置项：\n"
        "    port      默认端口（1~65535）\n"
        "    nickname  默认昵称（字母、数字、下划线，1~16字符）\n"
        "    roomname  默认房间名（UTF-8，1~32字符）\n"
        "    max_users 默认最大人数（正整数）\n"
        "  示例：/config port 9090"
    )

    def execute(self, args: list[str], context: dict[str, Any]) -> None:
        queue = context["queue"]
        settings = context["settings"]

        if not args:
            all_settings = settings.get_all()
            lines = ["当前默认配置："]
            for key, value in all_settings.items():
                lines.append(f"  {key} = {value}")
            queue.put("\n".join(lines), MessageType.TYPE_LOCAL_INFO)
            return

        if len(args) < 2:
            queue.put(
                "[系统] 参数不足。/config <设置项> <值>",
                MessageType.TYPE_LOCAL_ERROR,
            )
            return

        key = args[0].lower()
        raw_value = args[1]

        # 根据设置项类型转换值
        if key in ("port", "max_users"):
            try:
                value: str | int = int(raw_value)
            except ValueError:
                queue.put(
                    f"[系统] '{key}' 的值必须为整数。",
                    MessageType.TYPE_LOCAL_ERROR,
                )
                return
        else:
            value = raw_value

        # 调用 Settings.set 进行校验和持久化
        success = settings.set(key, value)
        if success:
            queue.put(
                f"[系统] 设置已更新：{key} = {value}",
                MessageType.TYPE_LOCAL_INFO,
            )
        else:
            queue.put(
                f"[系统] 设置失败：'{key}' 的值 '{raw_value}' 不合法。输入 /help config 查看帮助。",
                MessageType.TYPE_LOCAL_ERROR,
            )