# lightychat/common/receiver.py
import socket
import threading
from typing import Callable, Optional

from lightychat.common.entities import Message, ProtocolException
from lightychat.common.protocol_handler import ProtocolHandler


class Receiver:
    """通用接收模块：独立线程从 socket 收字节，解码为 Message，通过回调传出。"""

    def __init__(self, sock: socket.socket, proto: ProtocolHandler) -> None:
        self._sock = sock
        self._proto = proto
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._on_message: Optional[Callable[[Message], None]] = None
        self._on_disconnect: Optional[Callable[[], None]] = None

    # ---------- 公开接口 ----------

    def start(self) -> None:
        """启动接收线程。"""
        if self._thread is not None:
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止接收线程，等待退出。"""
        self._stop_flag = True
        # 强制关闭读取端以唤醒阻塞的 recv
        try:
            self._sock.shutdown(socket.SHUT_RD)
        except OSError:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def set_on_message(self, callback: Callable[[Message], None]) -> None:
        """注册消息回调，解码出完整消息时调用。"""
        self._on_message = callback

    def set_on_disconnect(self, callback: Callable[[], None]) -> None:
        """注册连接断开回调。"""
        self._on_disconnect = callback

    # ---------- 内部 ----------

    def _run(self) -> None:
        while not self._stop_flag:
            try:
                data = self._sock.recv(4096)
            except (ConnectionError, OSError):
                break

            if not data:
                # 对端正常关闭连接
                break

            try:
                messages = self._proto.feed(data)
            except ProtocolException:
                break  # 协议错误，断开连接

            for msg in messages:
                if self._on_message is not None:
                    try:
                        self._on_message(msg)
                    except Exception:
                        # 回调异常不应导致接收线程崩溃
                        pass

        # 连接断开通知
        if self._on_disconnect is not None:
            self._on_disconnect()