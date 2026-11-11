"""add purchase record files

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-30

购买记录的购物凭证与发票支持一次上传多个文件：
- 新增 purchase_record_files 表（file_type='receipt' 购物凭证 / 'invoice' 发票）
- 把 purchase_records 里旧单文件列的数据回填成附件记录，
  旧列继续保留，并同步为「第一个文件」的兼容镜像
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def _columns(inspector, table_name):
    """取某张表已有的列名；表不存在时返回空列表。"""
    try:
        return [column['name'] for column in inspector.get_columns(table_name)]
    except sa.exc.NoSuchTableError:
        return []


def _create_table():
    op.create_table(
        'purchase_record_files',
        sa.Column('file_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
                  autoincrement=True, nullable=False),
        sa.Column('record_id', sa.BigInteger(), nullable=False),
        sa.Column('file_type', sa.String(length=20), nullable=False),
        sa.Column('file_key', sa.Text(), nullable=False),
        sa.Column('preview_key', sa.Text(), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('file_md5', sa.String(length=64), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['record_id'], ['purchase_records.record_id']),
        sa.PrimaryKeyConstraint('file_id'),
    )
    op.create_index('ix_purchase_record_files_record_id', 'purchase_record_files', ['record_id'])
    op.create_index('ix_purchase_record_files_record_type', 'purchase_record_files',
                    ['record_id', 'file_type'])


def _backfill(record_columns):
    """旧单文件列 → 附件表。仅在迁移首次执行（表刚建出）时调用。"""
    receipt_name = 'receipt_image_name' if 'receipt_image_name' in record_columns else 'NULL'
    receipt_md5 = 'receipt_file_md5' if 'receipt_file_md5' in record_columns else 'NULL'
    receipt_created = 'created_at' if 'created_at' in record_columns else 'NULL'
    op.execute(
        f"""
        INSERT INTO purchase_record_files
            (record_id, file_type, file_key, original_filename, file_md5, sort_order, created_at)
        SELECT record_id, 'receipt', receipt_image_url, {receipt_name}, {receipt_md5}, 0, {receipt_created}
        FROM purchase_records
        WHERE receipt_image_url IS NOT NULL AND receipt_image_url <> ''
        """
    )

    invoice_preview = 'invoice_preview_key' if 'invoice_preview_key' in record_columns else 'NULL'
    invoice_name = 'invoice_original_filename' if 'invoice_original_filename' in record_columns else 'NULL'
    invoice_md5 = 'invoice_md5' if 'invoice_md5' in record_columns else 'NULL'
    invoice_created = 'created_at' if 'created_at' in record_columns else 'NULL'
    invoice_guard = ('AND (cannot_invoice IS NULL OR cannot_invoice = 0)'
                     if 'cannot_invoice' in record_columns else '')
    op.execute(
        f"""
        INSERT INTO purchase_record_files
            (record_id, file_type, file_key, preview_key, original_filename, file_md5, sort_order, created_at)
        SELECT record_id, 'invoice', invoice_file_key, {invoice_preview}, {invoice_name}, {invoice_md5}, 0, {invoice_created}
        FROM purchase_records
        WHERE invoice_file_key IS NOT NULL AND invoice_file_key <> ''
          {invoice_guard}
        """
    )

    # 旧数据里 has_invoice 可能与 invoice_file_key 不一致，迁移时统一成真实状态
    if 'has_invoice' in record_columns:
        op.execute(
            f"""
            UPDATE purchase_records
            SET has_invoice = 1
            WHERE invoice_file_key IS NOT NULL AND invoice_file_key <> ''
              AND (has_invoice IS NULL OR has_invoice = 0)
              {invoice_guard}
            """
        )


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'purchase_record_files' in tables:
        return

    _create_table()

    if 'purchase_records' in tables:
        record_columns = set(_columns(inspector, 'purchase_records'))
        if 'receipt_image_url' in record_columns and 'invoice_file_key' in record_columns:
            _backfill(record_columns)


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'purchase_record_files' in tables:
        for index_name in ('ix_purchase_record_files_record_type',
                           'ix_purchase_record_files_record_id'):
            try:
                op.drop_index(index_name, table_name='purchase_record_files')
            except Exception:
                pass
        op.drop_table('purchase_record_files')
