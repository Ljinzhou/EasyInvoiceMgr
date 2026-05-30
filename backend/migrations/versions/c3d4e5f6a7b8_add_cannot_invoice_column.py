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
    op.add_column('purchase_records',
        sa.Column('cannot_invoice', sa.Boolean(), server_default=sa.text('FALSE'))
    )


def downgrade():
    op.drop_column('purchase_records', 'cannot_invoice')
