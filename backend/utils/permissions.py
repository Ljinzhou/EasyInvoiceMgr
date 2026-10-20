"""权限与成员校验公共逻辑。

原先 `_check_student_event_access` 在 routes/invoices.py 与 routes/purchase_records.py
各复制一份、`ensure_event_membership` 寄居在 routes/events.py，导致 routes 层横向依赖。
现统一收敛到本模块，routes 之间不再互相 import。
"""

import logging

from models import db

logger = logging.getLogger(__name__)

# 特权用户：不受赛事成员限制
PRIVILEGED_USER_TYPES = ['admin', 'teacher', 'student_admin']


def check_student_event_access(event_id: int, user) -> bool:
    """学生用户能否访问（修改）某赛事的数据。特权用户直接放行。"""
    from models import Event, EventMember

    if user.user_type in PRIVILEGED_USER_TYPES:
        return True
    if user.user_type == 'student':
        is_member = EventMember.query.filter_by(
            event_id=event_id, user_id=user.user_id, is_deleted=False
        ).first()
        event = Event.query.get(event_id)
        if event and event.creator_id == user.user_id:
            return True
        return is_member is not None
    return False


def is_event_reviewer(event, user) -> bool:
    """能否审核该比赛的加入申请。

    只认三类人：admin、比赛负责人（Event.leader_id）、该比赛里
    role_in_event='teacher' 的成员。全局 user_type='teacher' 但既不是负责人
    也不是该比赛成员的老师**不在**其列。
    """
    if not event or not user:
        return False
    if user.user_type == 'admin':
        return True
    if event.leader_id and int(event.leader_id) == int(user.user_id):
        return True

    from models import EventMember

    teacher_member = EventMember.query.filter_by(
        event_id=event.event_id, user_id=user.user_id, is_deleted=False
    ).first()
    return bool(teacher_member and teacher_member.role_in_event == 'teacher')


def resolve_auto_reviewer_id():
    """自动审核时的审核人：admin 账号（多个时取 user_id 最小的），没有则返回 None。"""
    from models import User

    admin = User.query.filter_by(user_type='admin', is_deleted=False).order_by(User.user_id).first()
    return admin.user_id if admin else None


def ensure_event_membership(event_id: int, user_id: int) -> bool:
    """若用户在赛事成员列表中则直接返回，否则自动添加为赛事成员。

    仅对 admin/teacher/student_admin 执行添加。
    返回 True 表示已是成员或已成功添加，False 表示添加失败。
    """
    try:
        from models import User, EventMember, Event

        user = db.session.get(User, user_id)
        if not user or user.user_type not in PRIVILEGED_USER_TYPES:
            return True  # 非特权用户，无需检查

        event = db.session.get(Event, event_id)
        if not event:
            return False

        existing = EventMember.query.filter_by(
            event_id=event_id, user_id=user_id, is_deleted=False
        ).first()
        if existing:
            return True  # 已在名单中

        # 自动添加为赛事成员
        role = user.user_type if user.user_type in ['teacher', 'student_admin'] else 'teacher'
        member = EventMember(
            event_id=event_id,
            user_id=user_id,
            role_in_event=role,
            join_source='privileged_auto'
        )
        db.session.add(member)
        logger.info(f'自动添加赛事成员: event_id={event_id}, user_id={user_id}, role={role}')
        return True
    except Exception as e:
        logger.error(f'自动添加赛事成员失败: {e}', exc_info=True)
        return False