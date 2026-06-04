# lightychat/server/server_controller.py
from __future__ import annotations
import threading
import logging
from typing import Any, Dict, Optional

from lightychat.server.user_table import UserTable
from lightychat.common.protocol_handler import ProtocolHandler

logger = logging.getLogger(__name__)


# =============================================================================
# 子模块抽象接口 (后续由具体实现替换)
# =============================================================================

class _BaseModule:
    """所有子模块的基类，统一 start/stop 接口。"""
    def start(self) -> None: ...
    def stop(self) -> None: ...


class _ConnectionManager(_BaseModule):
    """连接管理器接口：监听端口，accept 新连接，管理所有客户端收发线程。"""
    def __init__(self, port: int, user_table: UserTable, proto: ProtocolHandler,
                 router: Any, max_users: int) -> None: ...


class _MessageRouter:
    """消息路由器接口：根据消息类型和接收方决定投递范围。"""
    def __init__(self, user_table: UserTable, command_handler: Any,
                 message_logger: Any) -> None: ...


class _CommandHandler:
    """指令处理器接口：解析并执行管理指令。"""
    def __init__(self, user_table: UserTable, admin_token: str) -> None: ...


class _HeartbeatChecker(_BaseModule):
    """心跳检测器接口：定期扫描在线用户表，踢出超时用户。"""
    def __init__(self, user_table: UserTable, router: Any) -> None: ...


class _Logger:
    """日志模块接口：记录公屏消息和系统事件到文件。"""
    def __init__(self, room_name: str) -> None: ...
    def log(self, text: str) -> None: ...
    def close(self) -> None: ...


# =============================================================================
# ServerController
# =============================================================================

class ServerController:
    """服务端生命周期管理器。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._port: int = config.get("port", 8080)
        self._room_name: str = config.get("room_name", "ChatRoom")
        self._max_users: int = config.get("max_users", 8)
        self._admin_token: str = config.get("admin_token", "")

        # 基础组件
        self._proto = ProtocolHandler()
        self._user_table = UserTable()

        # 高层组件 —— 全部使用空实现，待后续替换
        self._message_logger: _Logger = _Logger(self._room_name)
        self._command_handler: _CommandHandler = _CommandHandler(
            self._user_table, self._admin_token
        )
        self._message_router: _MessageRouter = _MessageRouter(
            self._user_table, self._command_handler, self._message_logger
        )
        self._connection_manager: _ConnectionManager = _ConnectionManager(
            self._port, self._user_table, self._proto,
            self._message_router, self._max_users,
        )
        self._heartbeat_checker: _HeartbeatChecker = _HeartbeatChecker(
            self._user_table, self._message_router
        )

        self._running = False
        self._acceptor_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动服务端线程。"""
        if self._running:
            return
        self._running = True

        self._acceptor_thread = threading.Thread(
            target=self._connection_manager.start,
            daemon=True, name="Acceptor",
        )
        self._acceptor_thread.start()

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_checker.start,
            daemon=True, name="Heartbeat",
        )
        self._heartbeat_thread.start()

    def stop(self) -> None:
        """优雅关闭服务端。"""
        if not self._running:
            return
        self._running = False

        self._connection_manager.stop()
        if self._acceptor_thread and self._acceptor_thread.is_alive():
            self._acceptor_thread.join(timeout=3.0)

        self._heartbeat_checker.stop()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)

        self._message_logger.close()

    def wait_for_shutdown(self) -> None:
        """阻塞直到服务端完全停止。"""
        if self._acceptor_thread:
            self._acceptor_thread.join()