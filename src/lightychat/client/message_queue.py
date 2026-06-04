import queue
from typing import Optional

from lightychat.common.entities import MessageType

class MessageQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, Optional[MessageType]]] = queue.Queue()

    def put(self, text: str, msg_type: Optional[MessageType] = None) -> None:
        """推入一条待显示文本，可附带消息类型用于颜色区分。

        Args:
            text: 显示文本。
            msg_type: 消息类型，None 表示使用默认颜色。
        """
        self._queue.put((text, msg_type))

    def get(self) -> tuple[str, Optional[MessageType]]:
        """阻塞取出并移除一条。"""
        return self._queue.get()

    def get_nowait(self) -> Optional[tuple[str, Optional[MessageType]]]:
        """非阻塞取出，队列为空返回 None。"""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None