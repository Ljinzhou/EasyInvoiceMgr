"""SQLite 友好的列类型。

SQLite 的 DATETIME 不保存时区，读回来是 naive datetime，而业务代码大量
直接与 datetime.now(timezone.utc) 比较。这里在 ORM 层把语义统一为
「库内 naive UTC，Python 侧 aware UTC」，避免改动任何业务代码。
"""
from datetime import timezone

from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator):
    """始终以 naive UTC 落库、以 aware UTC 读出的 DateTime。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        # 传入 naive 时间时一律视为 UTC（库内既有数据即为此约定）
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
