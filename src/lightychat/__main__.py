# lightychat/__main__.py
"""
客户端主入口：组装所有模块，启动终端界面。
"""
from lightychat.client.message_queue import MessageQueue
from lightychat.client.terminal_ui import TerminalUI
from lightychat.client.input_switch import InputSwitch
from lightychat.client.lobby_handler import LobbyHandler
from lightychat.client.session_controller import SessionController
from lightychat.client.command_router import CommandRouter
from lightychat.common.settings import Settings

#from lightychat.common.entities import  MessageType


def main() -> None:
    # 1. 基础服务模块
    msg_queue = MessageQueue()
    settings = Settings()

    # 2. 输入转移模块
    input_switch = InputSwitch(message_queue=msg_queue)

    # 3. 会话控制器
    session = SessionController(msg_queue, input_switch, settings)

    # 4. 大厅处理模块（未连接状态）
    lobby = LobbyHandler(msg_queue, settings, session=session)


    # 5. 聊天室上下文（连接状态下可用）
    chat_router = CommandRouter(
        message_queue=msg_queue,
        user_cache=input_switch.get_cached_user,
        session=session,
        # send_chat 和 send_command 暂时不传，后续远程指令实现后再注入
    )

    # 6. 依赖注入
    input_switch.bind_lobby_handler(lobby)
    input_switch.bind_command_router(chat_router)

    # 7. 终端界面
    ui = TerminalUI(message_queue=msg_queue)
    ui.run(on_input=input_switch.route)


if __name__ == "__main__":
    main()