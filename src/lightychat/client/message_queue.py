import queue

class MessageQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()  #报错Queue类型

    def put(self, text: str) -> None:
        """推入一条待显示文本"""
        self._queue.put(text)

    def get(self) -> str:
        """阻塞取出并移除一条文本"""
        return self._queue.get()

    def get_nowait(self) -> str | None:
        """非阻塞取出，队列为空返回 None"""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None