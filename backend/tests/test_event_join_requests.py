"""比赛加入申请与审核：接口级回归测试。

覆盖四条需求：
1. 未加入进行中比赛的用户可以提交加入申请；
2. 「自动审核加入」当场通过，审核人记为 admin；
3. 「人工审核加入」只有负责人/指导老师/admin 能审核，其他人 403；
4. 人员管理能查到成员的加入时间与审核人。
"""
import importlib

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """真实 create_app + 临时 SQLite，返回 (application, ids)。"""
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + (tmp_path / 'api.sqlite').as_posix())
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin')

    import config
    importlib.reload(config)
    import app as app_module
    importlib.reload(app_module)

    application = app_module.create_app()

    with application.app_context():
        from models import db, Event, EventMember, User

        admin = User.query.filter_by(username='admin').first()

        leader = User(username='leader', password_hash='x', real_name='张负责人', user_type='teacher')
        project_teacher = User(username='pteacher', password_hash='x', real_name='李指导', user_type='teacher')
        outsider_teacher = User(username='outsider', password_hash='x', real_name='王路人', user_type='teacher')
        student = User(username='student', password_hash='x', real_name='赵同学', user_type='student')
        student2 = User(username='student2', password_hash='x', real_name='钱同学', user_type='student')
        db.session.add_all([leader, project_teacher, outsider_teacher, student, student2])
        db.session.commit()

        manual_event = Event(
            event_name='人工审核比赛',
            creator_id=leader.user_id,
            leader_id=leader.user_id,
            status='ongoing',
            join_review_mode='manual',
            total_budget=1000,
            remaining_budget=1000,
        )
        auto_event = Event(
            event_name='自动审核比赛',
            creator_id=leader.user_id,
            leader_id=leader.user_id,
            status='ongoing',
            join_review_mode='auto',
            total_budget=1000,
            remaining_budget=1000,
        )
        db.session.add_all([manual_event, auto_event])
        db.session.commit()

        # 负责人 + 一名本项目的指导老师（role_in_event='teacher'）已是成员
        db.session.add_all([
            EventMember(event_id=manual_event.event_id, user_id=leader.user_id,
                        role_in_event='teacher', joined_by=leader.user_id, join_source='creator'),
            EventMember(event_id=manual_event.event_id, user_id=project_teacher.user_id,
                        role_in_event='teacher', joined_by=leader.user_id, join_source='direct_add'),
        ])
        db.session.commit()

        ids = {
            'admin': admin.user_id,
            'leader': leader.user_id,
            'project_teacher': project_teacher.user_id,
            'outsider_teacher': outsider_teacher.user_id,
            'student': student.user_id,
            'student2': student2.user_id,
            'manual_event': manual_event.event_id,
            'auto_event': auto_event.event_id,
        }

    client = application.test_client()

    def token_for(key):
        from flask_jwt_extended import create_access_token
        with application.app_context():
            return create_access_token(identity=str(ids[key]))

    def auth(key):
        return {'Authorization': f'Bearer {token_for(key)}'}

    yield application, client, ids, auth
    application = None


def _join_requests(client, event_id, key, auth):
    return client.get(f'/api/events/{event_id}/join-requests', headers=auth(key))


def test_auto_mode_approves_immediately_with_admin_as_reviewer(env):
    """自动审核：申请即刻通过，成员记录的审核人是 admin。"""
    application, client, ids, auth = env
    event_id = ids['auto_event']

    response = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()['data']
    assert payload['is_member'] is True
    assert payload['request']['status'] == 'approved'
    assert payload['request']['review_mode'] == 'auto'
    assert payload['request']['reviewer_id'] == ids['admin']
    assert payload['request']['review_time'] is not None

    with application.app_context():
        from models import EventMember

        member = EventMember.query.filter_by(
            event_id=event_id, user_id=ids['student'], is_deleted=False
        ).first()
        assert member is not None
        assert member.join_source == 'auto_review'
        assert member.joined_by == ids['admin']


def test_manual_mode_creates_pending_request_and_hides_review_from_student(env):
    """人工审核：申请是 pending，普通学生看不到也能不审核。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    response = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()['data']
    assert payload['is_member'] is False
    assert payload['request']['status'] == 'pending'
    assert payload['request']['reviewer_id'] is None

    with application.app_context():
        from models import EventMember

        assert EventMember.query.filter_by(
            event_id=event_id, user_id=ids['student'], is_deleted=False
        ).first() is None

    # 申请人自己不是审核人
    assert _join_requests(client, event_id, 'student', auth).status_code == 403
    # 全局是 teacher 但不是本项目成员/负责人，也不能审核
    assert _join_requests(client, event_id, 'outsider_teacher', auth).status_code == 403

    # 负责人可以审核
    leader_view = _join_requests(client, event_id, 'leader', auth)
    assert leader_view.status_code == 200, leader_view.get_json()
    data = leader_view.get_json()['data']
    assert data['pending_count'] == 1
    assert data['requests'][0]['user_id'] == ids['student']


def test_leader_approval_creates_member_with_reviewer_and_time(env):
    """负责人通过后：成员记录的加入来源与审核人正确，人员管理可展示。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    created = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    request_id = created.get_json()['data']['request']['request_id']

    approved = client.post(
        f'/api/events/{event_id}/join-requests/{request_id}/review',
        headers=auth('leader'),
        json={'action': 'approve'},
    )
    assert approved.status_code == 200, approved.get_json()
    assert approved.get_json()['data']['is_member'] is True

    with application.app_context():
        from models import EventJoinRequest, EventMember

        record = EventJoinRequest.query.filter_by(request_id=request_id).first()
        assert record.status == 'approved'
        assert record.reviewer_id == ids['leader']
        assert record.review_time is not None

        member = EventMember.query.filter_by(
            event_id=event_id, user_id=ids['student'], is_deleted=False
        ).first()
        assert member is not None
        assert member.joined_by == ids['leader']
        assert member.join_source == 'manual_review'

    members = client.get(f'/api/events/{event_id}/members', headers=auth('leader'))
    assert members.status_code == 200, members.get_json()
    data = members.get_json()['data']
    assert data['can_review_join'] is True
    row = next(item for item in data['members'] if item['user_id'] == ids['student'])
    assert row['joined_by'] == ids['leader']
    assert row['joined_by_name'] == '张负责人'
    assert row['join_source'] == 'manual_review'
    assert row['join_source_label'] == '人工审核通过'
    assert row['join_time'] is not None


def test_project_teacher_can_review_and_admin_too(env):
    """本项目指导老师与 admin 都能审核。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    first = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student2'))
    second = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    assert first.status_code == 201 and second.status_code == 201

    assert _join_requests(client, event_id, 'project_teacher', auth).status_code == 200
    assert _join_requests(client, event_id, 'admin', auth).status_code == 200

    approved = client.post(
        f'/api/events/{event_id}/join-requests/'
        f"{second.get_json()['data']['request']['request_id']}/review",
        headers=auth('project_teacher'),
        json={'action': 'approve'},
    )
    assert approved.status_code == 200, approved.get_json()


def test_reject_keeps_user_out_and_records_reason(env):
    """驳回：不产生成员记录，理由被保存。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    created = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    request_id = created.get_json()['data']['request']['request_id']

    rejected = client.post(
        f'/api/events/{event_id}/join-requests/{request_id}/review',
        headers=auth('leader'),
        json={'action': 'reject', 'reject_reason': '名额已满'},
    )
    assert rejected.status_code == 200, rejected.get_json()
    assert rejected.get_json()['data']['request']['status'] == 'rejected'
    assert rejected.get_json()['data']['request']['reject_reason'] == '名额已满'

    with application.app_context():
        from models import EventJoinRequest, EventMember

        assert EventMember.query.filter_by(
            event_id=event_id, user_id=ids['student'], is_deleted=False
        ).first() is None
        record = EventJoinRequest.query.filter_by(request_id=request_id).first()
        assert record.status == 'rejected'
        assert record.reviewer_id == ids['leader']


def test_duplicate_pending_request_is_rejected(env):
    """同一用户重复申请要给出明确提示，而不是堆积多条 pending。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    assert client.post(f'/api/events/{event_id}/join-requests',
                       headers=auth('student')).status_code == 201
    again = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    assert again.status_code == 400
    assert '审核中' in again.get_json()['message']


def test_member_cannot_apply_again_and_finished_event_closed(env):
    """已是成员不能申请；已结束的比赛不能申请。"""
    application, client, ids, auth = env

    # 负责人在 manual_event 里已是成员
    member_apply = client.post(f"/api/events/{ids['manual_event']}/join-requests",
                               headers=auth('leader'))
    assert member_apply.status_code == 400

    with application.app_context():
        from models import Event, db

        event = db.session.get(Event, ids['auto_event'])
        event.status = 'finished'
        db.session.commit()

    finished_apply = client.post(f"/api/events/{ids['auto_event']}/join-requests",
                                 headers=auth('student2'))
    assert finished_apply.status_code == 400
    assert '已结束' in finished_apply.get_json()['message']


def test_events_list_exposes_join_state_for_students(env):
    """赛事列表要带上审核方式与我的申请状态，前端据此渲染「请求加入」按钮。"""
    application, client, ids, auth = env

    client.post(f"/api/events/{ids['manual_event']}/join-requests", headers=auth('student'))

    listing = client.get('/api/events?page=1&page_size=20', headers=auth('student'))
    assert listing.status_code == 200, listing.get_json()
    rows = {row['event_id']: row for row in listing.get_json()['data']['data']}

    manual_row = rows[ids['manual_event']]
    assert manual_row['is_member'] is False
    assert manual_row['join_review_mode'] == 'manual'
    assert manual_row['join_request_status'] == 'pending'

    auto_row = rows[ids['auto_event']]
    assert auto_row['join_review_mode'] == 'auto'
    assert auto_row['join_request_status'] is None


def test_pending_summary_counts_only_reviewable_events(env):
    """红点数据：只统计自己有权审核的赛事，别人的待办不算数。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    assert client.post(f'/api/events/{event_id}/join-requests',
                       headers=auth('student')).status_code == 201
    assert client.post(f'/api/events/{event_id}/join-requests',
                       headers=auth('student2')).status_code == 201

    def summary(key):
        response = client.get('/api/events/join-requests/pending-summary', headers=auth(key))
        assert response.status_code == 200, response.get_json()
        return response.get_json()['data']

    leader_data = summary('leader')
    assert leader_data['total'] == 2
    assert leader_data['by_event'][str(event_id)] == 2

    assert summary('admin')['total'] == 2              # admin 可审全部
    assert summary('project_teacher')['total'] == 2    # 本项目的指导老师
    assert summary('outsider_teacher')['total'] == 0   # 全局老师但不是该项目成员
    assert summary('student')['total'] == 0


def test_events_list_includes_pending_join_count(env):
    """项目列表带 pending_join_request_count，只有审核人拿到非零值。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    assert client.post(f'/api/events/{event_id}/join-requests',
                       headers=auth('student')).status_code == 201

    def rows_for(key):
        response = client.get('/api/events?page=1&page_size=20', headers=auth(key))
        assert response.status_code == 200, response.get_json()
        return {row['event_id']: row for row in response.get_json()['data']['data']}

    leader_rows = rows_for('leader')
    assert leader_rows[event_id]['pending_join_request_count'] == 1
    assert leader_rows[ids['auto_event']]['pending_join_request_count'] == 0

    student_rows = rows_for('student')
    assert student_rows[event_id]['pending_join_request_count'] == 0


def test_update_event_can_switch_join_review_mode(env):
    """编辑比赛可以改审核方式：manual→auto 后新申请当场通过，非法值被拒绝。"""
    application, client, ids, auth = env
    event_id = ids['manual_event']

    switched = client.put(f'/api/events/{event_id}',
                          json={'join_review_mode': 'auto'}, headers=auth('leader'))
    assert switched.status_code == 200, switched.get_json()
    assert switched.get_json()['data']['join_review_mode'] == 'auto'

    listing = client.get('/api/events?page=1&page_size=20', headers=auth('leader'))
    rows = {row['event_id']: row for row in listing.get_json()['data']['data']}
    assert rows[event_id]['join_review_mode'] == 'auto'

    applied = client.post(f'/api/events/{event_id}/join-requests', headers=auth('student'))
    assert applied.status_code == 201, applied.get_json()
    assert applied.get_json()['data']['is_member'] is True

    # 切回人工审核
    back = client.put(f'/api/events/{event_id}',
                      json={'join_review_mode': 'manual'}, headers=auth('leader'))
    assert back.status_code == 200
    assert back.get_json()['data']['join_review_mode'] == 'manual'

    bad = client.put(f'/api/events/{event_id}',
                     json={'join_review_mode': 'whatever'}, headers=auth('leader'))
    assert bad.status_code == 400
    assert '加入审核方式' in bad.get_json()['message']

    with application.app_context():
        from utils.operation_log import OperationLog

        latest = (
            OperationLog.query
            .filter_by(action_type='update_event')
            .order_by(OperationLog.log_id.desc())
            .first()
        )
        assert latest is not None
        detail = latest.detail
        if isinstance(detail, str):
            import json

            detail = json.loads(detail)
        assert 'join_review_mode' in (detail or {}).get('changes', {})
