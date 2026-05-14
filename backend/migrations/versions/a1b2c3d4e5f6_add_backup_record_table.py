"""添加 backup_records 表

Revision ID: a1b2c3d4e5f6
Revises: 5cd03e0a4de7
Create Date: 2026-05-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '5cd03e0a4de7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'backup_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('backup_type', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('backup_scope', sa.String(20), nullable=False, server_default='full'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('progress_message', sa.String(200)),
        sa.Column('file_path', sa.Text()),
        sa.Column('file_size', sa.BigInteger()),
        sa.Column('file_count', sa.Integer()),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.user_id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('backup_records')
