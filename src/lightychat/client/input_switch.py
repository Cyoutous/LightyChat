from __future__ import annotations
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from lightychat.client.message_queue import MessageQueue

if TYPE_CHECKING:
    from lightychat.client.lobby_handler import LobbyHandler

class InputSwitch:
    """输入转移模块：根据连接状态路由用户输入，并缓存当前用户信息。"""

    def __init__(
        self,
        message_queue: MessageQueue,
        lobby_handler: Optional[LobbyHandler] = None,
        command_router: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Args:
            message_queue: 全局消息队列，用于本地回声测试或指令结果输出。
            lobby_handler: 大厅处理模块的主处理函数，未连接时调用。
            command_router: 指令路由模块的路由函数，已连接时调用。
        """
        self._queue = message_queue
        self._lobby = lobby_handler
        self._router = command_router

        # 连接状态
        self._connected: bool = False
        # 用户缓存
        self._user_id: str = ""
        self._is_host: bool = False
        self._admin_token: str = ""

    # ---------- 公开接口 ----------

    def route(self, text: str) -> None:
        """根据当前连接状态，将用户输入分发到对应处理器。"""
        if not self._connected:
            if self._lobby is not None:
                self._lobby.handle(text)
            else:
                # 测试期回声：未连接状态下的输入直接回显到消息区
                self._queue.put(f"[本地-未连接] {text}")
        else:
            if self._router is not None:
                self._router(text)
            else:
                # 测试期回声：已连接状态下的输入直接回显
                self._queue.put(f"[本地-已连接] {text}")

    def set_connected(
        self, user_id: str, is_host: bool, admin_token: str
    ) -> None:
        """切换为已连接状态，并缓存用户信息。"""
        self._connected = True
        self._user_id = user_id
        self._is_host = is_host
        self._admin_token = admin_token

    def set_disconnected(self) -> None:
        """切换为未连接状态，清空用户缓存。"""
        self._connected = False
        self._user_id = ""
        self._is_host = False
        self._admin_token = ""

    def is_connected(self) -> bool:
        """返回当前是否处于已连接状态。"""
        return self._connected

    def get_cached_user(self) -> Dict[str, Any]:
        """返回缓存的当前用户信息字典。"""
        return {
            "user_id": self._user_id,
            "is_host": self._is_host,
            "admin_token": self._admin_token,
        }

    # ---------- 后期扩展接口 ----------

    def bind_lobby_handler(self, handler: LobbyHandler) -> None:
        """注入大厅处理模块的处理函数。"""
        self._lobby = handler

    def bind_command_router(self, router: Callable[[str], None]) -> None:
        """注入指令路由模块的路由函数。"""
        self._router = router