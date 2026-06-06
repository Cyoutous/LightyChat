import json
from typing import Any, Callable, Dict

class Settings:
    DEFAULTS: Dict[str, Any] = {
        'port': 8080,
        'nickname': 'User',
        'roomname': 'LAN Chat Room',
        'max_users': 8,
    }

    VALIDATORS: Dict[str, Callable[[Any], bool]] = {
        'port':       lambda v: isinstance(v, int) and 1 <= v <= 65535,
        'nickname':   lambda v: isinstance(v, str) and 1 <= len(v) <= 16 and all(c.isalnum() or c == '_' for c in v),
        'roomname':   lambda v: isinstance(v, str) and 1 <= len(v.encode('utf-8')) <= 32,
        'max_users':  lambda v: isinstance(v, int) and v > 0,
    }

    def __init__(self, filepath: str = "config.json"):
        self._filepath = filepath
        self._data = dict(self.DEFAULTS)
        self._load()

    # ---------- 公开接口 ----------

    def get(self, key: str):
        """读取一项设置"""
        return self._data.get(key, self.DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> bool:
        """写入一项设置，校验失败返回 False"""
        validator = self.VALIDATORS.get(key)
        if validator is None:
            return False
        if not validator(value):
            return False
        self._data[key] = value
        self._save()
        return True

    def get_all(self) -> Dict[str, Any]:
        """返回所有设置"""
        return dict(self._data)

    # ---------- 内部 ----------

    def _load(self):
        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in self.VALIDATORS and self.VALIDATORS[k](v):
                    self._data[k] = v
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save(self):
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)