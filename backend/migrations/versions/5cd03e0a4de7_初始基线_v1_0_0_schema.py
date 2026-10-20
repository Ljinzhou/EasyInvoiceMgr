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
    """基线：空操作。

    全新数据库的表结构由 `models.py` 经 `db.create_all()` 建立，
    随后由 `utils/schema_init.py` 的 `ensure_schema()` 把 alembic 版本戳到此基线，
    后续增量变更则由本目录下更新的 revision 承担。
    """
    pass


def downgrade():
    """基线降级 - 不适用。"""
    pass