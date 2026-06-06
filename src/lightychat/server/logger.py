# lightychat/server/logger.py
import logging
import os
import threading
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 项目根目录：本文件在 src/lightychat/server/ 下，往上 3 级到项目根
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Logger:
    """日志模块：记录公屏消息和系统事件到文件。"""

    DEFAULT_LOG_DIR = str(_PROJECT_ROOT / "logs")

    def __init__(self, room_name: str = "chatroom", log_dir: str = "") -> None:
        if not log_dir:
            log_dir = self.DEFAULT_LOG_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in room_name
        )
        os.makedirs(log_dir, exist_ok=True)
        filename = os.path.join(log_dir, f"{safe_name}_{timestamp}.log")

        self._file: Optional[TextIOWrapper] = None
        self._lock = threading.Lock()

        try:
            self._file = open(filename, "w", encoding="utf-8")
            self._file.write(f"=== 聊天室 '{room_name}' 日志 ===\n")
            self._file.write(
                f"创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            self._file.flush()
        except OSError as e:
            logger.warning(f"无法创建日志文件 {filename}: {e}")
            self._file = None

    def log(self, text: str) -> None:
        """写入一条日志，自动添加时间戳。"""
        if self._file is None:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {text}\n"

        with self._lock:
            try:
                self._file.write(line)
                self._file.flush()
            except OSError:
                pass

    def close(self) -> None:
        """关闭日志文件。"""
        with self._lock:
            if self._file is not None:
                try:
                    self._file.write("\n=== 聊天室关闭 ===\n")
                    self._file.flush()
                    self._file.close()
                except OSError:
                    pass
                finally:
                    self._file = None