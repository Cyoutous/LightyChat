# lightychat/server/heartbeat_checker.py
import logging
import threading
import time
from typing import Any, Optional

from lightychat.server.user_table import UserTable

logger = logging.getLogger(__name__)


class HeartbeatChecker:
    """心跳检测器：定期扫描在线用户表，踢出超时无活动的用户。"""

    SCAN_INTERVAL = 10   # 扫描间隔（秒）
    TIMEOUT = 30          # 超时阈值（秒）

    def __init__(
        self,
        user_table: UserTable,
        connection: Any,  # ConnectionManager 实例
    ) -> None:
        self._user_table = user_table
        self._connection = connection
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False

    def start(self) -> None:
        """启动心跳检测线程。"""
        if self._thread is not None:
            return
        self._stop_flag = False
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="HeartbeatChecker"
        )
        self._thread.start()
        logger.info("心跳检测器已启动")

    def stop(self) -> None:
        """停止心跳检测线程。"""
        self._stop_flag = True
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("心跳检测器已停止")

    def _run(self) -> None:
        """主循环，定时扫描。"""
        while not self._stop_flag:
            time.sleep(self.SCAN_INTERVAL)
            if self._stop_flag:
                break
            self._check()

    def _check(self) -> None:
        """检查所有在线用户的最后活跃时间，踢出超时者。"""
        now = time.time()
        for user in self._user_table.get_all():
            if user.is_host:
                # 房主断线时服务器整个关停，不需要心跳踢人
                continue
            if now - user.last_active > self.TIMEOUT:
                logger.info(f"用户 {user.user_id} 心跳超时，断开连接")
                self._connection.disconnect(user.user_id)