#!/usr/bin/env python3
"""客户端主入口 - 回声测试阶段"""
from lightychat.client.message_queue import MessageQueue
from lightychat.client.terminal_ui import TerminalUI
from lightychat.client.input_switch import InputSwitch


def main() -> None:
    # 1. 创建消息队列
    msg_queue = MessageQueue()

    # 2. 创建输入转移模块（暂不注入大厅和指令路由，使用内置回声逻辑）
    input_switch = InputSwitch(message_queue=msg_queue)

    # 3. 创建 TerminalUI，传入消息队列
    ui = TerminalUI(message_queue=msg_queue)

    # 4. 启动 UI 事件循环，用户输入通过 input_switch.route 处理
    ui.run(on_input=input_switch.route)

    #做一个测试


if __name__ == "__main__":
    main()