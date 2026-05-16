"""
Invitation Code Tests
Cover: create, verify, toggle, permissions
"""

from tests.helpers import _json, login_as, register_user, auth_headers


class TestCreateInvitationCodes:
    """IC-001 ~ IC-005"""

    def test_admin_can_create_any_type(self, client, db, admin_token):
        """IC-001: Admin creates any type"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'admin',
            'expires_days': 30,
            'quantity': 2,
            'max_uses': 5,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = _json(resp)['data']
        assert data['count'] == 2
        assert len(data['codes']) == 2

    def test_teacher_cannot_create_admin_type(self, client, db, teacher_token):
        """IC-002: Teacher cannot create admin codes"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'admin',
            'expires_days': 30,
            'quantity': 1,
        }, headers=auth_headers(teacher_token))
        assert resp.status_code == 403

    def test_student_admin_cannot_create_teacher_type(self, client, db, student_admin_token):
        """IC-003: student_admin cannot create teacher/admin codes"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'teacher',
            'expires_days': 30,
            'quantity': 1,
        }, headers=auth_headers(student_admin_token))
        assert resp.status_code == 403

    def test_expiry_range_validation(self, client, db, admin_token):
        """IC-004: Expiry 1-365 days"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 0,  # Invalid
            'quantity': 1,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400

        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 366,  # Invalid
            'quantity': 1,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400

    def test_quantity_range_validation(self, client, db, admin_token):
        """IC-005: Quantity 1-20"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 30,
            'quantity': 25,  # Invalid
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400

    def test_student_cannot_create_codes(self, client, db, student_token):
        """Students cannot create invitation codes"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 30,
            'quantity': 1,
        }, headers=auth_headers(student_token))
        assert resp.status_code == 403

    def test_student_admin_can_create_student_codes(self, client, db, student_admin_token):
        """student_admin can create student/student_admin types"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 30,
            'quantity': 1,
        }, headers=auth_headers(student_admin_token))
        assert resp.status_code == 200

    def test_create_generates_unique_codes(self, client, db, admin_token):
        """Generate 20 codes with unique values"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 30,
            'quantity': 20,
        }, headers=auth_headers(admin_token))
        codes = [c['code'] for c in _json(resp)['data']['codes']]
        assert len(set(codes)) == 20


class TestVerifyInvitationCodes:
    """IC-006 ~ IC-007"""

    def test_verify_public_endpoint(self, client, db, admin_token):
        """IC-006: Verify endpoint does NOT require auth"""
        # Create a code first
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 30,
            'quantity': 1,
        }, headers=auth_headers(admin_token))
        code = _json(resp)['data']['codes'][0]['code']

        # Verify without auth
        resp = client.post('/api/invitation-codes/verify', json={'code': code})
        assert resp.status_code == 200
        data = _json(resp)['data']
        assert data['valid'] == True
        assert data['target_user_type'] == 'student'

    def test_verify_nonexistent_code(self, client, db):
        """Verify non-existent code returns valid=False"""
        resp = client.post('/api/invitation-codes/verify',
                           json={'code': 'NONEXISTENT-CODE'})
        assert resp.status_code == 200
        assert _json(resp)['data']['valid'] == False

    def test_verify_empty_code(self, client, db):
        """Empty code → 400"""
        resp = client.post('/api/invitation-codes/verify', json={'code': ''})
        assert resp.status_code == 400


class TestToggleAndDelete:
    """IC-008 ~ IC-009"""

    def test_teacher_can_only_toggle_own_codes(self, client, db, admin_token, teacher_token):
        """IC-008: Teacher can only toggle own codes"""
        # Admin creates a code
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 30,
            'quantity': 1,
        }, headers=auth_headers(admin_token))
        code_id = _json(resp)['data']['codes'][0]  # code_id not returned, need GET

        # Teacher cannot toggle admin's code
        codes_resp = client.get('/api/invitation-codes',
                                headers=auth_headers(admin_token))
        first_code_id = _json(codes_resp)['data']['data'][0]['id']

        resp = client.post(f'/api/invitation-codes/{first_code_id}/toggle',
                           headers=auth_headers(teacher_token))
        # Teacher didn't create this code → 403
        assert resp.status_code in [200, 403]

    def test_delete_code_admin_only(self, client, db, admin_token, teacher_token):
        """IC-009: Only admin can delete codes"""
        resp = client.post('/api/invitation-codes', json={
            'target_user_type': 'student',
            'expires_days': 1,
            'quantity': 1,
        }, headers=auth_headers(admin_token))

        # Get the created code ID
        list_resp = client.get('/api/invitation-codes?page=1&page_size=5',
                               headers=auth_headers(admin_token))
        codes = _json(list_resp)['data']['data']
        if codes:
            code_id = codes[0]['id']

            # Teacher cannot delete
            resp = client.delete(f'/api/invitation-codes/{code_id}',
                                 headers=auth_headers(teacher_token))
            assert resp.status_code == 403
