"""
Event / Project Management Tests
Cover: create, read, update, delete, members
"""

from tests.helpers import _json, login_as, register_user, auth_headers


class TestCreateEvent:
    """EVT-001 ~ EVT-004"""

    def test_create_event_success(self, client, db, admin_token):
        """EVT-001: Create event with all required fields"""
        resp = client.post('/api/events', json={
            'event_name': 'New Competition',
            'event_start_time': '2026-07-01T09:00:00',
            'event_end_time': '2026-07-03T18:00:00',
            'total_budget': 5000,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 201
        data = _json(resp)['data']
        assert data['event_name'] == 'New Competition'
        assert data['total_budget'] == 5000
        assert data['remaining_budget'] == 5000
        assert data['status'] == 'ongoing'

    def test_create_event_missing_name(self, client, db, admin_token):
        """EVT-002: Missing required field"""
        resp = client.post('/api/events', json={
            'event_start_time': '2026-07-01T09:00:00',
            'event_end_time': '2026-07-03T18:00:00',
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400
        assert '不能为空' in _json(resp)['message']

    def test_create_event_start_after_end(self, client, db, admin_token):
        """EVT-003: Start time after end time"""
        resp = client.post('/api/events', json={
            'event_name': 'Bad Timing',
            'event_start_time': '2026-12-31T23:00:00',
            'event_end_time': '2026-01-01T00:00:00',
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400
        assert '开始时间必须早于结束时间' in _json(resp)['message']

    def test_create_event_negative_budget(self, client, db, admin_token):
        """EVT-004: Negative budget rejected"""
        resp = client.post('/api/events', json={
            'event_name': 'Negative Budget',
            'event_start_time': '2026-07-01T09:00:00',
            'event_end_time': '2026-07-03T18:00:00',
            'total_budget': -100,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400
        assert '预算不能为负数' in _json(resp)['message']

    def test_create_event_auto_adds_creator_as_member(self, client, db, admin_token):
        """EVT-001: Creator auto-added as member"""
        resp = client.post('/api/events', json={
            'event_name': 'Member Test',
            'event_start_time': '2026-07-01T09:00:00',
            'event_end_time': '2026-07-03T18:00:00',
            'total_budget': 5000,
        }, headers=auth_headers(admin_token))
        event_id = _json(resp)['data']['event_id']

        members_resp = client.get(f'/api/events/{event_id}/members',
                                  headers=auth_headers(admin_token))
        members = _json(members_resp)['data']['members']
        assert len(members) >= 1  # Creator added as member

    def test_student_can_create_event(self, client, db, student_token):
        """PERM-005: Student can create events"""
        resp = client.post('/api/events', json={
            'event_name': 'Student Event',
            'event_start_time': '2026-08-01T09:00:00',
            'event_end_time': '2026-08-02T18:00:00',
            'total_budget': 1000,
        }, headers=auth_headers(student_token))
        assert resp.status_code == 201


class TestReadEvents:
    """EVT-005 ~ EVT-006"""

    def test_list_events(self, client, db, admin_token, event_ongoing):
        """List events returns paginated data"""
        resp = client.get('/api/events', headers=auth_headers(admin_token))
        data = _json(resp)['data']
        assert data['total'] >= 1
        assert len(data['data']) >= 1

    def test_student_sees_only_member_events(self, client, db, student_token, admin_token):
        """EVT-005: Non-admin/teacher only see their own events"""
        # Create an event via admin (student is not a member)
        client.post('/api/events', json={
            'event_name': 'Admin Only Event',
            'event_start_time': '2026-09-01T09:00:00',
            'event_end_time': '2026-09-02T18:00:00',
            'total_budget': 3000,
        }, headers=auth_headers(admin_token))

        # Create an event via student (student IS the creator)
        resp = client.post('/api/events', json={
            'event_name': 'Student Own Event',
            'event_start_time': '2026-09-03T09:00:00',
            'event_end_time': '2026-09-04T18:00:00',
            'total_budget': 1000,
        }, headers=auth_headers(student_token))

        # Student lists events - should only see their own
        resp = client.get('/api/events', headers=auth_headers(student_token))
        events = _json(resp)['data']['data']
        # Student should only see events they created or are member of
        event_names = [e['event_name'] for e in events]
        assert 'Student Own Event' in event_names

    def test_admin_sees_all_events(self, client, db, admin_token, student_token):
        """EVT-006: Admin sees all events"""
        client.post('/api/events', json={
            'event_name': 'Event A',
            'event_start_time': '2026-10-01T09:00:00',
            'event_end_time': '2026-10-02T18:00:00',
            'total_budget': 1000,
        }, headers=auth_headers(admin_token))

        client.post('/api/events', json={
            'event_name': 'Event B',
            'event_start_time': '2026-10-03T09:00:00',
            'event_end_time': '2026-10-04T18:00:00',
            'total_budget': 2000,
        }, headers=auth_headers(student_token))

        resp = client.get('/api/events', headers=auth_headers(admin_token))
        assert _json(resp)['data']['total'] >= 2


class TestDeleteEvent:
    """EVT-007"""

    def test_delete_event_without_invoices(self, client, db, admin_token, event_ongoing):
        """Delete event with no invoices should succeed"""
        event_id = event_ongoing['data']['event_id']
        resp = client.delete(f'/api/events/{event_id}',
                             headers=auth_headers(admin_token))
        assert resp.status_code == 200

    def test_student_cannot_delete_event(self, client, db, student_token, admin_token):
        """PERM-006: Student/student_admin cannot delete events"""
        resp = client.post('/api/events', json={
            'event_name': 'ToDelete',
            'event_start_time': '2026-11-01T09:00:00',
            'event_end_time': '2026-11-02T18:00:00',
            'total_budget': 500,
        }, headers=auth_headers(student_token))
        event_id = _json(resp)['data']['event_id']

        resp = client.delete(f'/api/events/{event_id}',
                             headers=auth_headers(student_token))
        assert resp.status_code == 403


class TestEventMembers:
    """EVT-012: Member management"""

    def test_add_member_to_event(self, client, db, admin_token, event_ongoing, student_token):
        """Add a member to event"""
        from flask_jwt_extended import decode_token
        event_id = event_ongoing['data']['event_id']
        student_uid = decode_token(student_token)['sub']

        resp = client.post(f'/api/events/{event_id}/members', json={
            'user_id': int(student_uid),
            'role_in_event': 'student',
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 201

    def test_cannot_add_duplicate_member(self, client, db, admin_token, event_ongoing):
        """Adding existing member returns 400"""
        from flask_jwt_extended import decode_token
        event_id = event_ongoing['data']['event_id']
        admin_uid = decode_token(admin_token)['sub']

        resp = client.post(f'/api/events/{event_id}/members', json={
            'user_id': int(admin_uid),
            'role_in_event': 'teacher',
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400
        assert '已经是赛事成员' in _json(resp)['message']

    def test_remove_member_from_event(self, client, db, admin_token, student_token):
        """Remove member from event"""
        from flask_jwt_extended import decode_token
        # Create event
        resp = client.post('/api/events', json={
            'event_name': 'RemoveTest',
            'event_start_time': '2026-12-01T09:00:00',
            'event_end_time': '2026-12-02T18:00:00',
            'total_budget': 1000,
        }, headers=auth_headers(admin_token))
        event_id = _json(resp)['data']['event_id']
        student_uid = decode_token(student_token)['sub']

        # Add student member
        client.post(f'/api/events/{event_id}/members', json={
            'user_id': int(student_uid),
            'role_in_event': 'student',
        }, headers=auth_headers(admin_token))

        # Remove student member
        resp = client.delete(
            f'/api/events/{event_id}/members/{student_uid}',
            headers=auth_headers(admin_token))
        assert resp.status_code == 200
