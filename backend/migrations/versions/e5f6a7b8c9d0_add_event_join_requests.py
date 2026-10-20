"""add event join requests

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-20

新增比赛加入申请能力：
- events.join_review_mode：创建比赛时选择「自动审核加入」或「人工审核加入」
- event_members.joined_by / join_source：记录成员是被谁、通过什么途径加进来的
- event_join_requests：加入申请表（pending / approved / rejected）
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def _columns(inspector, table_name):
    """取某张表已有的列名；表不存在时返回空列表。"""
    try:
        return [column['name'] for column in inspector.get_columns(table_name)]
    except sa.exc.NoSuchTableError:
        return []


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    # 1. 比赛增加「加入审核方式」
    if 'events' in tables:
        if 'join_review_mode' not in _columns(inspector, 'events'):
            op.add_column(
                'events',
                sa.Column('join_review_mode', sa.String(length=20), nullable=False,
                          server_default='manual')
            )

    # 2. 成员表记录加入途径与操作人
    if 'event_members' in tables:
        member_columns = _columns(inspector, 'event_members')
        if 'joined_by' not in member_columns:
            op.add_column('event_members', sa.Column('joined_by', sa.BigInteger(), nullable=True))
        if 'join_source' not in member_columns:
            op.add_column('event_members', sa.Column('join_source', sa.String(length=20), nullable=True))
        # 迁移前的历史成员没有审核人信息，统一标记为 legacy
        op.execute("UPDATE event_members SET join_source = 'legacy' WHERE join_source IS NULL")

    # 3. 加入申请表
    if 'event_join_requests' not in tables:
        op.create_table(
            'event_join_requests',
            sa.Column('request_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('event_id', sa.BigInteger(), nullable=False),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('review_mode', sa.String(length=20), nullable=False, server_default='manual'),
            sa.Column('reviewer_id', sa.BigInteger(), nullable=True),
            sa.Column('review_time', sa.DateTime(), nullable=True),
            sa.Column('reject_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default=sa.text('0')),
            sa.ForeignKeyConstraint(['event_id'], ['events.event_id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
            sa.ForeignKeyConstraint(['reviewer_id'], ['users.user_id']),
            sa.PrimaryKeyConstraint('request_id'),
        )
        op.create_index('ix_event_join_requests_event_id', 'event_join_requests', ['event_id'])
        op.create_index('ix_event_join_requests_event_status', 'event_join_requests',
                        ['event_id', 'status'])
        op.create_index('ix_event_join_requests_user_id', 'event_join_requests', ['user_id'])


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'event_join_requests' in tables:
        for index_name in ('ix_event_join_requests_user_id',
                           'ix_event_join_requests_event_status',
                           'ix_event_join_requests_event_id'):
            try:
                op.drop_index(index_name, table_name='event_join_requests')
            except Exception:
                pass
        op.drop_table('event_join_requests')

    if 'event_members' in tables:
        member_columns = _columns(inspector, 'event_members')
        if 'join_source' in member_columns:
            op.drop_column('event_members', 'join_source')
        if 'joined_by' in member_columns:
            op.drop_column('event_members', 'joined_by')

    if 'events' in tables and 'join_review_mode' in _columns(inspector, 'events'):
        op.drop_column('events', 'join_review_mode')
