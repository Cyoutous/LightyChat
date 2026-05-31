import threading
from lightychat.common.entities import User


class UserTable:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._short_id_map: dict[int, str] = {}
        self._lock = threading.Lock()
        self._next_short_id = 1
        self._reusable_ids: list[int] = []  # 可用短ID池

    # ---------- 公开接口 ----------

    def add(self, user: User):
        """添加用户，自动分配短ID"""
        with self._lock:
            if self._reusable_ids:
                user.short_id = self._reusable_ids.pop()
            else:
                user.short_id = self._next_short_id
                self._next_short_id += 1
            self._users[user.user_id] = user
            self._short_id_map[user.short_id] = user.user_id

    def remove(self, user_id: str) -> User | None:
        """移除用户，返回被移除的 User 或 None"""
        with self._lock:
            user = self._users.pop(user_id, None)
            if user:
                self._short_id_map.pop(user.short_id, None)
                self._reusable_ids.append(user.short_id)  # 回收ID
            return user

    def get(self, user_id: str) -> User | None:
        """按完整ID查询"""
        with self._lock:
            return self._users.get(user_id)

    def get_by_short_id(self, short_id: int) -> User | None:
        """按短ID查询"""
        with self._lock:
            uid = self._short_id_map.get(short_id)
            if uid:
                return self._users.get(uid)
            return None

    def get_all(self) -> list[User]:
        """返回所有用户列表"""
        with self._lock:
            return list(self._users.values())

    def update_active(self, user_id: str):
        """更新最后活跃时间"""
        with self._lock:
            user = self._users.get(user_id)
            if user:
                import time
                user.last_active = time.time()

    def set_muted(self, user_id: str, muted: bool):
        """设置禁言状态"""
        with self._lock:
            user = self._users.get(user_id)
            if user:
                user.is_muted = muted

    def count(self) -> int:
        """返回在线人数"""
        with self._lock:
            return len(self._users)