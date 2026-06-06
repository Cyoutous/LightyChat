# lightychat/client/heartbeat_client.py
import logging
import threading
import time
from typing import Optional

from lightychat.common.entities import Message, MessageType
from lightychat.common.sender import Sender

logger = logging.getLogger(__name__)


class HeartbeatClient:
    """客户端心跳发送器：独立线程定时发送 PING。"""

    INTERVAL = 10  # 心跳间隔（秒）

    def __init__(self, sender: Sender) -> None:
        self._sender = sender
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False

    def start(self) -> None:
        """启动心跳线程。"""
        if self._thread is not None:
            return
        self._stop_flag = False
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="HeartbeatClient"
        )
        self._thread.start()
        logger.info("客户端心跳已启动")

    def stop(self) -> None:
        """停止心跳线程。"""
        self._stop_flag = True
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("客户端心跳已停止")

    def _run(self) -> None:
        """心跳循环。"""
        while not self._stop_flag:
            time.sleep(self.INTERVAL)
            if self._stop_flag:
                break
            try:
                msg = Message(
                    type=MessageType.TYPE_HEARTBEAT,
                    sender_id="",
                    receiver_id="",
                    payload=b"",
                )
                self._sender.send(msg)
            except Exception:
                # 发送失败（连接断开），由 Receiver 的 on_disconnect 触发清理
                logger.debug("心跳发送失败，连接可能已断开")
                break