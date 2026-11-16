"""add invoice fields to purchase record files

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-17

一张购买记录可以上传多张发票，原先只能把发票信息存在记录级单列上，
导致第二张及以后的发票解析结果被丢弃。这里给附件表补上逐张发票的
号码/日期/税号/类型/项目/金额与解析状态，记录级字段继续作为汇总镜像。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None

NEW_COLUMNS = (
    ('invoice_number', sa.String(length=50)),
    ('invoice_date', sa.Date()),
    ('invoice_tax_number', sa.String(length=50)),
    ('invoice_type', sa.String(length=50)),
    ('invoice_item_name', sa.String(length=200)),
    ('invoice_amount', sa.Numeric(12, 2)),
    ('parse_status', sa.String(length=20)),
    ('parse_error', sa.Text()),
    ('parsed_at', sa.DateTime()),
)


def _existing_columns():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    try:
        return {column['name'] for column in inspector.get_columns('purchase_record_files')}
    except sa.exc.NoSuchTableError:
        return set()


def upgrade():
    existing = _existing_columns()
    if not existing:
        return

    for name, column_type in NEW_COLUMNS:
        if name not in existing:
            op.add_column('purchase_record_files', sa.Column(name, column_type, nullable=True))

    # 历史数据：把记录级发票信息回填到第一条 PDF/图片发票上，
    # 让旧记录在多发票界面里也能看到已有解析结果。
    if {'invoice_number', 'invoice_amount'} <= _existing_columns():
        op.execute(
            """
            UPDATE purchase_record_files
            SET invoice_number = (
                    SELECT invoice_number FROM purchase_records
                    WHERE purchase_records.record_id = purchase_record_files.record_id
                ),
                invoice_date = (
                    SELECT invoice_date FROM purchase_records
                    WHERE purchase_records.record_id = purchase_record_files.record_id
                ),
                invoice_tax_number = (
                    SELECT invoice_tax_number FROM purchase_records
                    WHERE purchase_records.record_id = purchase_record_files.record_id
                ),
                invoice_type = (
                    SELECT invoice_type FROM purchase_records
                    WHERE purchase_records.record_id = purchase_record_files.record_id
                ),
                invoice_amount = (
                    SELECT total_amount FROM purchase_records
                    WHERE purchase_records.record_id = purchase_record_files.record_id
                ),
                parse_status = 'parsed'
            WHERE file_type = 'invoice'
              AND sort_order = 0
              AND (invoice_number IS NULL OR invoice_number = '')
              AND (invoice_amount IS NULL OR invoice_amount = 0)
              -- 只回填「历史上只有一张发票」的记录，避免把多张发票的合计金额记到第一张上
              AND (
                    SELECT COUNT(*) FROM purchase_record_files AS f2
                    WHERE f2.record_id = purchase_record_files.record_id
                      AND f2.file_type = 'invoice'
                ) = 1
              AND EXISTS (
                    SELECT 1 FROM purchase_records
                    WHERE purchase_records.record_id = purchase_record_files.record_id
                      AND purchase_records.invoice_number IS NOT NULL
                      AND purchase_records.invoice_number <> ''
              )
            """
        )


def downgrade():
    existing = _existing_columns()
    for name, _ in NEW_COLUMNS:
        if name in existing:
            with op.batch_alter_table('purchase_record_files') as batch_op:
                batch_op.drop_column(name)
