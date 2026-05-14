"""初始基线 - v1.0.0 schema

Revision ID: 5cd03e0a4de7
Revises:
Create Date: 2026-05-14 23:30:42.821285

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5cd03e0a4de7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """基线：schema 已由 base.sql 创建，无需操作。"""
    pass


def downgrade():
    """基线降级 - 不适用。"""
    pass