"""
System Management Tests
Cover: config, backup, update check
"""

from tests.helpers import _json, login_as, register_user, auth_headers


class TestSystemConfig:
    """SYS-001 ~ SYS-003"""

    def test_admin_can_get_config(self, client, db, admin_token):
        """SYS-001: Admin gets config (masks sensitive values)"""
        resp = client.get('/api/system/config',
                          headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = _json(resp)['data']
        assert '_version' in data  # version info included

    def test_admin_can_set_allowed_config(self, client, db, admin_token):
        """SYS-002: Update AI model config"""
        resp = client.put('/api/system/config', json={
            'configs': {
                'ai_model': 'glm-4v-flash',
                'ai_api_key': 'test-key-12345',
            }
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 200
        keys = _json(resp)['data']['updated_keys']
        assert 'ai_model' in keys

    def test_blocked_keys_not_updated(self, client, db, admin_token):
        """SYS-002: Keys outside allowed_keys are silently ignored"""
        resp = client.put('/api/system/config', json={
            'configs': {
                'ai_model': 'glm-4v-flash',
                'malicious_key': 'hack_value',
            }
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 200
        keys = _json(resp)['data']['updated_keys']
        assert 'malicious_key' not in keys

    def test_non_admin_cannot_access_config(self, client, db, student_token):
        """403 for non-admin"""
        resp = client.get('/api/system/config',
                          headers=auth_headers(student_token))
        assert resp.status_code == 403


class TestBackupConfig:
    """SYS-008: Backup schedule configuration"""

    def test_admin_can_get_backup_config(self, client, db, admin_token):
        """Get default backup config"""
        resp = client.get('/api/system/backup/config',
                          headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = _json(resp)['data']
        assert 'enabled' in data
        assert 'frequency' in data
        assert 'time' in data
        assert 'retention_count' in data

    def test_admin_can_update_backup_config_valid(self, client, db, admin_token):
        """Update with valid values"""
        resp = client.put('/api/system/backup/config', json={
            'enabled': True,
            'frequency': 'weekly',
            'time': '02:00',
            'retention_count': 7,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 200

    def test_update_backup_config_invalid_frequency(self, client, db, admin_token):
        """Invalid frequency → 400"""
        resp = client.put('/api/system/backup/config', json={
            'enabled': True,
            'frequency': 'hourly',  # Not allowed
            'time': '03:00',
            'retention_count': 5,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400

    def test_update_backup_config_invalid_time(self, client, db, admin_token):
        """Invalid time format → 400"""
        resp = client.put('/api/system/backup/config', json={
            'enabled': True,
            'frequency': 'daily',
            'time': '25:00',  # Invalid hour
            'retention_count': 5,
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400

    def test_update_backup_config_retention_range(self, client, db, admin_token):
        """Invalid retention → 400"""
        resp = client.put('/api/system/backup/config', json={
            'enabled': True,
            'frequency': 'daily',
            'time': '03:00',
            'retention_count': 0,  # Must be 1-100
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400


class TestBackupOperations:
    """SYS-005: Manual backup"""

    def test_backup_requires_admin(self, client, db, student_token):
        """Non-admin cannot trigger backup"""
        resp = client.post('/api/system/backup',
                           headers=auth_headers(student_token))
        assert resp.status_code == 403

    def test_admin_can_trigger_backup(self, client, db, admin_token):
        """Admin triggers backup → 503 expected (backup service not initialized in test app)"""
        resp = client.post('/api/system/backup',
                           headers=auth_headers(admin_token))
        # Test app doesn't init backup service, so 503 is expected; 200/409 also valid
        assert resp.status_code in [200, 409, 503]

    def test_admin_can_list_backups(self, client, db, admin_token):
        """List backup records"""
        resp = client.get('/api/system/backups',
                          headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = _json(resp)['data']
        assert 'items' in data


class TestSystemUpdate:
    """SYS-004: Version update check"""

    def test_admin_can_check_update(self, client, db, admin_token):
        """Check update endpoint works"""
        resp = client.get('/api/system/check-update',
                          headers=auth_headers(admin_token))
        assert resp.status_code == 200
        data = _json(resp)['data']
        assert 'current_version' in data
        assert 'latest_version' in data
        assert 'has_update' in data


class TestRestore:
    """SYS-006: Restore requires confirm"""

    def test_restore_without_confirm_rejected(self, client, db, admin_token):
        """Restore with confirm=false → 400"""
        resp = client.post('/api/system/backup/restore/1', json={
            'confirm': False
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 400

    def test_restore_nonexistent_backup(self, client, db, admin_token):
        """Restore non-existent backup → 404"""
        resp = client.post('/api/system/backup/restore/99999', json={
            'confirm': True
        }, headers=auth_headers(admin_token))
        assert resp.status_code == 404
