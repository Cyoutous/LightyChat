# lightychat/server/connection_manager.py
"""
连接管理器：负责监听端口、接受新连接、管理客户端会话的完整生命周期。
"""
from __future__ import annotations

import logging
import socket
import threading
import time
from typing import Any, Optional

from lightychat.common.entities import Message, MessageType, User, ProtocolException
from lightychat.common.protocol_handler import ProtocolHandler
from lightychat.common.sender import Sender
from lightychat.common.receiver import Receiver
from lightychat.server.user_table import UserTable

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理所有客户端连接：监听、认证、注册、收发线程生命周期。"""

    HANDSHAKE_TIMEOUT = 5.0

    def __init__(
        self,
        port: int,
        user_table: UserTable,
        proto: ProtocolHandler,
        router: Any,          # MessageRouter 实例，传入 Any 避免循环导入
        max_users: int = 8,
    ) -> None:
        self._port = port
        self._user_table = user_table
        self._proto = proto
        self._router = router
        self._max_users = max_users

        self._listen_socket: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._is_locked = False

    # ---------- 公开接口 ----------

    def start(self) -> None:
        """启动监听循环（独立线程）。"""
        if self._accept_thread is not None:
            return

        self._stop_flag = False
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_socket.bind(("", self._port))
        self._listen_socket.listen(5)
        self._listen_socket.settimeout(1.0)

        logger.info(f"连接管理器已在端口 {self._port} 上监听")

        self._accept_thread = threading.Thread(
            target=self._run_accept_loop, daemon=True, name="Acceptor"
        )
        self._accept_thread.start()

    def stop(self) -> None:
        """关闭监听，断开所有客户端，等待接受线程退出。"""
        self._stop_flag = True
        if self._listen_socket:
            try:
                self._listen_socket.close()
            except OSError:
                pass

        for user in self._user_table.get_all():
            self._disconnect_user(user.user_id)

        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=3.0)

    def disconnect(self, user_id: str) -> None:
        """公开的断开接口，供外部（如指令处理器）调用。"""
        self._disconnect_user(user_id)

    def set_locked(self, locked: bool) -> None:
        """设置房间锁定状态。"""
        self._is_locked = locked

    # ---------- 内部 ----------

    def _run_accept_loop(self) -> None:
        assert self._listen_socket is not None
        while not self._stop_flag:
            try:
                client_sock, addr = self._listen_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=self._handle_new_connection,
                args=(client_sock, addr),
                daemon=True,
                name=f"Client-{addr}",
            ).start()

    def _handle_new_connection(self, sock: socket.socket, addr: Any) -> None:
        """处理新连接：握手 -> 注册 -> 建立会话。"""
        sock.settimeout(self.HANDSHAKE_TIMEOUT)

        # ------- 第一阶段：魔数校验 -------
        try:
            header = self._recv_exact(sock, 14)
        except (socket.timeout, ConnectionError):
            sock.close()
            return

        if not self._proto.validate_magic(header):
            sock.close()
            return

        # ------- 第二阶段：接收注册消息 -------
        proto = ProtocolHandler()
        # 已经读取了完整的 header，把它放入解析器的缓冲区，
        # 这样后续从 socket 读取的 body 能和 header 一起被解析为完整消息。
        proto.feed(header)
        try:
            msg = self._recv_one_message(sock, proto)
        except (socket.timeout, ConnectionError, ProtocolException):
            sock.close()
            return

        if msg is None or msg.type != MessageType.TYPE_COMMAND:
            sock.close()
            return

        payload = msg.payload.decode("utf-8", errors="replace").strip()
        if not payload.startswith("/register"):
            self._send_error_and_close(sock, "无效的注册请求")
            return

        parts = payload.split(" ", 2)
        if len(parts) < 3:
            self._send_error_and_close(sock, "注册参数缺失")
            return

        _, requested_id, is_host_str = parts
        is_host = (is_host_str == "1")

        if not (
            1 <= len(requested_id) <= 16
            and all(c.isalnum() or c == "_" for c in requested_id)
        ):
            self._send_error_and_close(sock, "昵称格式非法")
            return

        if self._is_locked and not is_host:
            self._send_error_and_close(sock, "房间已锁定")
            return
        if self._user_table.count() >= self._max_users:
            self._send_error_and_close(sock, "房间已满")
            return

        actual_id = requested_id
        if self._user_table.get(requested_id):
            actual_id : str = self._generate_fallback_id(requested_id)

        # ------- 第三阶段：创建收发线程并注册 -------
        sender = Sender(sock, self._proto)
        receiver_proto = ProtocolHandler()
        receiver = Receiver(sock, receiver_proto)

        user = User(
            user_id=actual_id,
            short_id=0,
            sock=sock,
            is_host=is_host,
            is_muted=False,
            last_active=time.time(),
            addr=addr,
        )

        self._user_table.add(user)

        # 保存 Sender / Receiver 引用，用于优雅停止
        user.sender = sender
        user.receiver = receiver

        # 恢复阻塞模式（握手时设置了超时，正常通信必须是阻塞的）
        sock.settimeout(None)

        def on_message(msg: Message) -> None:
            if self._router and hasattr(self._router, "handle_message"):
                self._router.handle_message(msg, actual_id, sender)
            else:
                logger.warning(f"路由器未就绪，丢弃来自 {actual_id} 的消息")

        def on_disconnect() -> None:
            self._disconnect_user(actual_id)

        receiver.set_on_message(on_message)
        receiver.set_on_disconnect(on_disconnect)
        sender.set_on_disconnect(on_disconnect)

        sender.start()
        receiver.start()

        # ------- 第四阶段：回复注册成功 -------
        response = f"/register ok {actual_id} {1 if is_host else 0}"
        resp_msg = Message(
            type=MessageType.TYPE_RESPONSE,
            sender_id="",
            receiver_id=actual_id,
            payload=response.encode("utf-8"),
        )
        sender.send(resp_msg)

        if self._router and hasattr(self._router, "broadcast_system_message"):
            self._router.broadcast_system_message(f"{actual_id} 加入了聊天室")

        logger.info(f"用户 {actual_id} ({addr}) 注册成功，房主={is_host}")

    def _disconnect_user(self, user_id: str) -> None:
        """内部断开逻辑：优雅停止收发线程、清理用户表、广播离线消息。"""
        user = self._user_table.remove(user_id)
        if user is None:
            return

        # 🔑 先关 socket，让阻塞中的 recv() 立即抛异常退出；
        #    否则 Windows 上 shutdown(SHUT_RD) 不能中断 recv()，join 会卡满 2s。
        try:
            user.sock.close()
        except OSError:
            pass

        if user.sender:
            user.sender.stop()
        if user.receiver:
            user.receiver.stop()

        if self._router and hasattr(self._router, "broadcast_system_message"):
            self._router.broadcast_system_message(f"{user_id} 离开了聊天室")

        logger.info(f"用户 {user_id} 已断开")

    # ---------- 辅助方法 ----------

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("连接在读取时关闭")
            data += chunk
        return data

    def _recv_one_message(
        self, sock: socket.socket, proto: ProtocolHandler
    ) -> Optional[Message]:
        while True:
            data = sock.recv(4096)
            if not data:
                raise ConnectionError("连接在读取时关闭")
            msgs = proto.feed(data)
            if msgs:
                return msgs[0]

    def _send_error_and_close(self, sock: socket.socket, reason: str) -> None:
        try:
            response = f"/register err {reason}"
            resp_msg = Message(
                type=MessageType.TYPE_RESPONSE,
                sender_id="",
                receiver_id="",
                payload=response.encode("utf-8"),
            )
            data = self._proto.encode(resp_msg)
            sock.sendall(data)
        except OSError:
            pass
        finally:
            sock.close()

    def _generate_fallback_id(self, original_id: str) -> str:
        import random

        while True:
            uid = f"{original_id}{random.randint(1000, 9999)}"
            if not self._user_table.get(uid):
                return uid