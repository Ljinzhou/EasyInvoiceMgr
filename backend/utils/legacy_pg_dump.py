"""旧版 PostgreSQL dump 到 SQLite 的数据导入。

只解析 pg_dump 的 COPY 数据块，不执行任何 DDL —— 表结构由 SQLAlchemy
模型（db.create_all / Alembic）负责。dump 里的 CREATE TYPE / ALTER TABLE /
CREATE INDEX / setval 等语句全部忽略。
"""
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

_COPY_HEADER = re.compile(r'^COPY\s+(?P<table>[\w."]+)\s*\((?P<columns>.*?)\)\s+FROM\s+stdin;\s*$')
_TZ_SUFFIX = re.compile(r'([+-]\d{2})$')

# 父表在前，保证数据顺序天然满足外键
IMPORT_ORDER = [
    'users', 'events', 'event_members', 'invoices', 'vouchers',
    'purchase_records', 'invitation_codes', 'system_configs',
    'export_tasks', 'backup_records', 'operation_logs',
]

_UNESCAPE = {
    '\\': '\\', 't': '\t', 'n': '\n', 'r': '\r',
    'b': '\b', 'f': '\f', 'v': '\v',
}


def _unescape(value: str) -> str:
    """还原 COPY 文本格式的转义序列。"""
    if '\\' not in value:
        return value
    parts = []
    index = 0
    length = len(value)
    while index < length:
        char = value[index]
        if char == '\\' and index + 1 < length:
            nxt = value[index + 1]
            parts.append(_UNESCAPE.get(nxt, nxt))
            index += 2
            continue
        parts.append(char)
        index += 1
    return ''.join(parts)


@dataclass
class CopyBlock:
    table: str
    columns: list
    rows: list = field(default_factory=list)


@dataclass
class ImportReport:
    row_counts: dict = field(default_factory=dict)
    skipped_tables: list = field(default_factory=list)
    skipped_columns: dict = field(default_factory=dict)
    foreign_key_violations: list = field(default_factory=list)

    def summary(self) -> str:
        tables = ', '.join(f'{name}={count}' for name, count in self.row_counts.items())
        total = sum(self.row_counts.values())
        extra = f'；忽略的表: {self.skipped_tables}' if self.skipped_tables else ''
        return f'共导入 {total} 行（{tables}）{extra}'


def parse_copy_blocks(sql_text: str):
    """从 pg_dump 文本中按出现顺序产出 COPY 数据块。"""
    block = None
    for raw_line in sql_text.splitlines():
        if block is None:
            match = _COPY_HEADER.match(raw_line)
            if match:
                table = match.group('table').split('.')[-1].strip('"')
                columns = [item.strip().strip('"') for item in match.group('columns').split(',')]
                block = CopyBlock(table=table, columns=columns)
            continue

        if raw_line == '\\.':
            yield block
            block = None
            continue

        block.rows.append([
            None if item == '\\N' else _unescape(item)
            for item in raw_line.split('\t')
        ])

    if block is not None:
        raise ValueError(f'COPY 数据块未正常结束: {block.table}')


def _parse_timestamp(raw: str) -> str:
    """pg_dump 的 timestamptz 文本 -> naive UTC 字符串（SQLite 存储格式）。"""
    text = raw.strip()
    if ' ' in text and 'T' not in text:
        text = text.replace(' ', 'T', 1)
    # PostgreSQL 可能输出 +00 / +08 这类两位偏移，补成 +00:00 才能解析
    text = _TZ_SUFFIX.sub(r'\1:00', text)
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment.strftime('%Y-%m-%d %H:%M:%S.%f')


def _base_type(column_type):
    """剥掉 TypeDecorator 外壳，取出真正的存储类型。

    Task 3 之后时间列是 UTCDateTime（TypeDecorator），直接 isinstance 判断
    会落到 else 分支，所以这里统一先拆壳。
    """
    from sqlalchemy.types import TypeDecorator

    while isinstance(column_type, TypeDecorator):
        column_type = getattr(column_type, 'impl_instance', None) or column_type.impl
    return column_type


def _coerce_value(column, raw):
    """按 SQLAlchemy 列类型把 COPY 文本转成 SQLite 可写入的值。"""
    from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, JSON, Numeric, SmallInteger

    if raw is None:
        return None

    column_type = _base_type(column.type)

    if isinstance(column_type, JSON):
        return json.dumps(json.loads(raw), ensure_ascii=False)
    if isinstance(column_type, DateTime):
        return _parse_timestamp(raw)
    if isinstance(column_type, Date):
        return date.fromisoformat(raw[:10]).isoformat()
    if isinstance(column_type, Boolean):
        return 1 if raw in ('t', 'true', '1') else 0
    if isinstance(column_type, Numeric):
        return str(Decimal(raw))
    if isinstance(column_type, (Integer, BigInteger, SmallInteger)):
        return int(raw)
    return raw


def _load_tables():
    """加载 SQLAlchemy metadata（含 operation_logs）。"""
    import utils.operation_log  # noqa: F401  确保 operation_logs 表注册
    from models import db

    return db.metadata.tables


def import_pg_dump_file(db_path: str, sql_path: str) -> ImportReport:
    with open(sql_path, 'r', encoding='utf-8', errors='replace') as handle:
        return import_pg_dump_text(db_path, handle.read())


def import_pg_dump_text(db_path: str, sql_text: str) -> ImportReport:
    """把 dump 里的 COPY 数据灌进已建好表的 SQLite 数据库。"""
    tables = _load_tables()
    blocks = {}
    for block in parse_copy_blocks(sql_text):
        blocks.setdefault(block.table, block)

    report = ImportReport()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute('PRAGMA foreign_keys=OFF')

        ordered = [name for name in IMPORT_ORDER if name in blocks]
        ordered += sorted(name for name in blocks if name not in IMPORT_ORDER)

        for table_name in ordered:
            block = blocks[table_name]
            table = tables.get(table_name)
            if table is None:
                report.skipped_tables.append(table_name)
                logger.warning(f'dump 中的表 {table_name} 在当前模型中不存在，已跳过')
                continue

            usable = [(index, name) for index, name in enumerate(block.columns) if name in table.columns]
            missing = [name for name in block.columns if name not in table.columns]
            if missing:
                report.skipped_columns[table_name] = missing
                logger.warning(f'表 {table_name} 的列 {missing} 在当前模型中不存在，已跳过')

            columns = [table.columns[name] for _index, name in usable]
            column_sql = ', '.join(f'"{column.name}"' for column in columns)
            placeholder_sql = ', '.join('?' * len(columns))
            statement = f'INSERT INTO "{table_name}" ({column_sql}) VALUES ({placeholder_sql})'

            rows = []
            for raw_row in block.rows:
                rows.append([
                    _coerce_value(column, raw_row[index] if index < len(raw_row) else None)
                    for (index, _name), column in zip(usable, columns)
                ])

            connection.executemany(statement, rows)
            report.row_counts[table_name] = len(rows)

        connection.commit()
        violations = connection.execute('PRAGMA foreign_key_check').fetchall()
        report.foreign_key_violations = [tuple(item) for item in violations]
        if report.foreign_key_violations:
            logger.warning(
                f'外键完整性检查发现 {len(report.foreign_key_violations)} 条异常，'
                f'样例: {report.foreign_key_violations[:5]}'
            )
    finally:
        connection.close()

    logger.info(f'旧版 dump 导入完成: {report.summary()}')
    return report
