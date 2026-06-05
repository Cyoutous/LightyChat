# lightychat/server/server_controller.py
from __future__ import annotations
import threading
import logging
from typing import Any, Dict, Optional

from lightychat.common.protocol_handler import ProtocolHandler
from lightychat.server.user_table import UserTable
from lightychat.server.connection_manager import ConnectionManager
from lightychat.server.message_router import MessageRouter
from lightychat.server.command_handler import CommandHandler

logger = logging.getLogger(__name__)


# =============================================================================
# 子模块抽象接口 (后续由具体实现替换)
# =============================================================================

class _BaseModule:
    """所有子模块的基类，统一 start/stop 接口。"""
    def start(self) -> None: ...
    def stop(self) -> None: ...


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

        # 1. 基础组件（无依赖）
        self._proto = ProtocolHandler()
        self._user_table = UserTable()
        self._ready_event = threading.Event()

        # 2. 日志模块（几乎无依赖，暂用占位）
        self._message_logger = _Logger(self._room_name)

        # 3. 指令处理器（依赖 user_table）
        self._command_handler = CommandHandler({
            "user_table": self._user_table,
            "connection": None,  # 下面回填
            "admin_token": self._admin_token,
        })

        # 4. 消息路由器（依赖 user_table、command_handler、logger）
        self._message_router = MessageRouter(
            self._user_table,
            command_handler=self._command_handler,
            message_logger=self._message_logger,
        )

        # 5. 连接管理器（依赖 user_table、proto、router）
        self._connection_manager = ConnectionManager(
            self._port, self._user_table, self._proto,
            self._message_router, self._max_users,
        )

        # 6. 回填 connection 到 command_handler
        if self._command_handler:
            self._command_handler.set_connection(self._connection_manager)

        # 7. 心跳检测器（依赖 user_table、router）
        self._heartbeat_checker = _HeartbeatChecker(
            self._user_table, self._message_router
        )

        self._running = False
        self._acceptor_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
    
    # ====start====

    def start(self) -> None:
        """启动服务端线程。"""
        print("[DEBUG] ConnectionManager.start() called")
        if self._running:
            return
        self._running = True

        self._acceptor_thread = threading.Thread(
            target=self._run_connection_manager,
            daemon=True, name="Acceptor",
        )
        self._acceptor_thread.start()

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_checker.start,
            daemon=True, name="Heartbeat",
        )
        self._heartbeat_thread.start()

    def _run_connection_manager(self) -> None:
        try:
            self._connection_manager.start()
            self._ready_event.set()
        except Exception:
            logger.exception("服务端连接管理器启动失败")

    def wait_until_ready(self, timeout: Optional[float] = None) -> bool:
        """等待服务端就绪，返回是否在超时前准备完成。"""
        return self._ready_event.wait(timeout)
    

    # ====stop====

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