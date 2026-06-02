# lightychat/__main__.py
from lightychat.client.message_queue import MessageQueue
from lightychat.client.terminal_ui import TerminalUI
from lightychat.client.input_switch import InputSwitch
from lightychat.client.lobby_handler import LobbyHandler
from lightychat.common.settings import Settings


def main() -> None:
    msg_queue = MessageQueue()
    settings = Settings()

    # 大厅处理模块（on_create / on_join 暂时为 None）
    lobby = LobbyHandler(message_queue=msg_queue, settings=settings)

    # 输入转移模块，注入大厅处理模块
    input_switch = InputSwitch(message_queue=msg_queue, lobby_handler=lobby)

    # TerminalUI
    ui = TerminalUI(message_queue=msg_queue)
    ui.run(on_input=input_switch.route)


if __name__ == "__main__":
    main()