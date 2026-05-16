"""
Voucher Management Tests
"""

import io

from tests.helpers import _json, register_user, login_as, auth_headers


class TestVoucherUpload:
    """VCH-001 ~ VCH-003"""

    def test_create_voucher_requires_item_name(self, client, db, admin_token, event_ongoing):
        """VCH-002: item_name is required"""
        event_id = event_ongoing['data']['event_id']

        resp = client.post('/api/vouchers', data={
            'event_id': str(event_id),
            'amount': '200.00',
            # missing item_name
        }, content_type='multipart/form-data', headers=auth_headers(admin_token))
        assert resp.status_code in [400]

    def test_create_voucher_requires_file(self, client, db, admin_token, event_ongoing):
        """VCH-001: File required"""
        event_id = event_ongoing['data']['event_id']

        resp = client.post('/api/vouchers', data={
            'event_id': str(event_id),
            'item_name': 'Test Item',
            'amount': '200.00',
            # no file
        }, content_type='multipart/form-data', headers=auth_headers(admin_token))
        assert resp.status_code == 400
        assert '文件' in _json(resp)['message']


class TestVoucherDelete:
    """VCH-003"""

    def test_uploader_can_delete_own_voucher(self, client, db, admin_token, event_ongoing):
        """Uploader or admin/teacher can delete"""
        event_id = event_ongoing['data']['event_id']

        # Create voucher via admin
        resp = client.post('/api/vouchers', data={
            'event_id': str(event_id),
            'item_name': 'Deletable',
            'amount': '100.00',
            'purchase_date': '2026-06-01',
            'file': (io.BytesIO(b'%PDF-1.4 fake'), 'voucher.pdf'),
        }, content_type='multipart/form-data', headers=auth_headers(admin_token))
        assert resp.status_code == 200
        voucher_id = _json(resp)['data']['voucher_id']

        resp = client.delete(f'/api/vouchers/{voucher_id}',
                             headers=auth_headers(admin_token))
        assert resp.status_code == 200


class TestMD5Check:
    """VCH-007: MD5 duplicate checking"""

    def test_check_file_md5_no_match(self, client, db, admin_token):
        """No duplicate found"""
        resp = client.get('/api/check-file-md5?md5=abcdef1234567890',
                          headers=auth_headers(admin_token))
        assert resp.status_code == 200
        assert _json(resp)['data']['exists'] == False

    def test_check_file_md5_missing_param(self, client, db, admin_token):
        """Missing md5 param → 400"""
        resp = client.get('/api/check-file-md5', headers=auth_headers(admin_token))
        assert resp.status_code == 400
