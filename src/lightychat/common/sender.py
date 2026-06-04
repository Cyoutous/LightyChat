import queue
import socket
import threading
from typing import Optional, Callable

from lightychat.common.entities import Message
from lightychat.common.protocol_handler import ProtocolHandler


class Sender:
    """通用发送模块：独立线程从队列取 Message，编码后写入 socket。"""

    def __init__(self, sock: socket.socket, proto: ProtocolHandler) -> None:
        self._sock = sock
        self._proto = proto
        self._queue: queue.Queue[Message | None] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False
        self._on_disconnect: Optional[Callable[[], None]] = None

    # ---------- 公开接口 ----------

    def start(self) -> None:
        """启动发送线程。"""
        if self._thread is not None:
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止发送线程，等待退出。"""
        self._stop_flag = True
        self._queue.put(None)  # 唤醒阻塞在 get() 的线程
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def send(self, msg: Message) -> None:
        """将消息推入发送队列。"""
        self._queue.put(msg)

    def set_on_disconnect(self, callback: Callable[[], None]) -> None:
        """注册连接断开回调。"""
        self._on_disconnect = callback

    # ---------- 内部 ----------

    def _run(self) -> None:
        while not self._stop_flag:
            msg = self._queue.get()
            if msg is None:
                break  # 停止信号

            try:
                data = self._proto.encode(msg)
            except Exception:
                # 编码失败（如消息超长），跳过这条消息
                continue

            try:
                self._sock.sendall(data)
            except (ConnectionError, OSError):
                if self._on_disconnect is not None:
                    self._on_disconnect()
                break