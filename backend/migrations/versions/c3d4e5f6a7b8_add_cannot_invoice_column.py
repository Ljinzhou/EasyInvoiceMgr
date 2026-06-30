"""添加 purchase_records.cannot_invoice 列

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # 先检查列是否已存在，避免重复添加
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('purchase_records')]
    if 'cannot_invoice' not in columns:
        op.add_column('purchase_records',
            sa.Column('cannot_invoice', sa.Boolean(), server_default=sa.text('FALSE'))
        )


def downgrade():
    op.drop_column('purchase_records', 'cannot_invoice')
