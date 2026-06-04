# lightychat/__main__.py
"""
客户端主入口：组装所有模块，启动终端界面。
"""
from lightychat.client.message_queue import MessageQueue
from lightychat.client.terminal_ui import TerminalUI
from lightychat.client.input_switch import InputSwitch
from lightychat.client.lobby_handler import LobbyHandler
from lightychat.client.session_controller import SessionController
from lightychat.common.settings import Settings

from lightychat.common.entities import  MessageType


def main() -> None:
    # -----------------------------------------------
    # 1. 创建基础服务模块（无依赖）
    # -----------------------------------------------
    msg_queue = MessageQueue()
    settings = Settings()

    # -----------------------------------------------
    # 2. 创建输入转移模块（依赖消息队列）
    #    此时尚未注入大厅/指令路由，后续绑定
    # -----------------------------------------------
    input_switch = InputSwitch(message_queue=msg_queue)

    # -----------------------------------------------
    # 3. 创建会话控制器（依赖消息队列、输入转移、设置）
    #    负责建立/断开连接、管理收发线程
    # -----------------------------------------------
    session = SessionController(msg_queue, input_switch, settings)

    # -----------------------------------------------
    # 4. 创建大厅处理模块（依赖消息队列、设置、会话）
    #    负责未连接状态下的指令解析与执行
    # -----------------------------------------------
    lobby = LobbyHandler(msg_queue, settings, session=session)

    # -----------------------------------------------
    # 5. 完善依赖注入
    #    - 输入转移模块绑定大厅处理模块（未连接状态）
    #    - 已连接状态的指令路由模块尚未实现，预留 bind_command_router 接口
    # -----------------------------------------------
    input_switch.bind_lobby_handler(lobby)
    # input_switch.bind_command_router(chat_router)  # 待实现

     # ---------- 临时：已连接状态下的简易路由器 ----------
    def temp_chat_router(text: str) -> None:
        if text.startswith("/"):
            msg_queue.put(
                f"[系统] 指令 '{text}' 暂未实现。",
                MessageType.TYPE_LOCAL_ERROR,
            )
        else:
            session.send_chat_message(text)
    # -----------------------------------------------

    input_switch.bind_command_router(temp_chat_router)


    # -----------------------------------------------
    # 6. 启动终端界面（阻塞，直到用户退出）
    #    TerminalUI 会启动 curses 并进入事件循环
    #    用户输入 → input_switch.route() → 大厅/聊天室指令
    # -----------------------------------------------
    ui = TerminalUI(message_queue=msg_queue)
    ui.run(on_input=input_switch.route)


if __name__ == "__main__":
    main()