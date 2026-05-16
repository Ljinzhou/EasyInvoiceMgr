"""
Avatar functionality tests - upload, get, delete, and serve avatar files.
"""
import io
import hashlib

from .conftest import _json, login_as, register_user, auth_headers


def _create_test_image(width=100, height=100, fmt='png'):
    """Generate a minimal valid image bytes in the requested format."""
    # Minimal 1x1 PNG (smallest valid PNG)
    if fmt == 'png':
        # Minimal valid PNG: 1x1 pixel
        return (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR'  # IHDR chunk, 13 bytes data
            b'\x00\x00\x00\x01'    # width=1
            b'\x00\x00\x00\x01'    # height=1
            b'\x08\x02'            # bit depth=8, color type=2 (RGB)
            b'\x00\x00\x00'        # compression, filter, interlace
            b'\x90wS\xde'          # CRC
            b'\x00\x00\x00\x0cIDAT'  # IDAT chunk
            b'\x08\xd7c\xf8\x0f\x00\x01\x01\x00\x05\x0e\x0e'
            b'\x00\x00\x00\x00IEND'  # IEND chunk
            b'\xaeB`\x82'          # CRC
        )
    elif fmt in ('jpg', 'jpeg'):
        # Minimal JPEG: 1x1 pixel
        return (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n'
            b'\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d'
            b'\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
            b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
            b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04'
            b'\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142'
            b'\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19'
            b'\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
            b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a'
            b'\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9'
            b'\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8'
            b'\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5'
            b'\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2\xcd'
            b'\xff\xd9'
        )
    elif fmt == 'webp':
        # Minimal valid WebP: 1x1 pixel (VP8)
        return (
            b'RIFF\x1a\x00\x00\x00WEBPVP8 '
            b'\x0a\x00\x00\x00\x10\x00\x00\x00\x01\x00'
            b'\x01\x00\x01\x00\x00\x00\x00\x01\x00\x00'
        )
    return b''


class TestAvatarGet:
    """GET /api/auth/avatar"""

    def test_get_avatar_no_auth(self, client):
        resp = client.get('/api/auth/avatar')
        assert resp.status_code == 401

    def test_get_avatar_no_avatar_set(self, client, student_token):
        resp = client.get('/api/auth/avatar',
                          headers=auth_headers(student_token))
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['data']['avatar_url'] is None

    def test_get_avatar_after_upload(self, client, admin_token):
        img = _create_test_image(fmt='png')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        assert resp.status_code == 200
        avatar_url = _json(resp)['data']['avatar_url']

        # Now GET avatar should return the URL
        resp = client.get('/api/auth/avatar',
                          headers=auth_headers(admin_token))
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['data']['avatar_url'] == avatar_url


class TestAvatarUpload:
    """POST /api/auth/avatar/upload"""

    def test_upload_no_auth(self, client):
        img = _create_test_image()
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'test.png')},
            content_type='multipart/form-data'
        )
        assert resp.status_code == 401

    def test_upload_no_file(self, client, admin_token):
        resp = client.post(
            '/api/auth/avatar/upload',
            data={},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 400
        assert data['code'] == 400

    def test_upload_empty_filename(self, client, admin_token):
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(b'test'), '', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 400
        assert data['code'] == 400

    def test_upload_no_extension(self, client, admin_token):
        img = _create_test_image()
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'noextension')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 400
        assert data['code'] == 400

    def test_upload_wrong_extension(self, client, admin_token):
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(b'test'), 'avatar.gif', 'image/gif')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 400
        assert data['code'] == 400

    def test_upload_too_large(self, client, admin_token):
        # Create fake file that exceeds 5MB
        large_data = b'x' * (5 * 1024 * 1024 + 1)
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(large_data), 'large.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 400
        assert data['code'] == 400

    def test_upload_success_png(self, client, admin_token):
        img = _create_test_image(fmt='png')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['data']['avatar_url'].startswith('/uploads/')
        assert data['data']['file_md5'] == hashlib.md5(img).hexdigest()

    def test_upload_success_jpg(self, client, admin_token):
        img = _create_test_image(fmt='jpg')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.jpg', 'image/jpeg')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['data']['avatar_url'].startswith('/uploads/')

    def test_upload_success_webp(self, client, admin_token):
        img = _create_test_image(fmt='webp')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.webp', 'image/webp')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['data']['avatar_url'].startswith('/uploads/')

    def test_upload_replaces_old_avatar(self, client, admin_token):
        img1 = _create_test_image(fmt='png')
        img2 = _create_test_image(fmt='jpg')

        # Upload first avatar
        resp1 = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img1), 'avatar1.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        url1 = _json(resp1)['data']['avatar_url']

        # Upload second avatar (should replace first)
        resp2 = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img2), 'avatar2.jpg', 'image/jpeg')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        url2 = _json(resp2)['data']['avatar_url']

        assert url1 != url2
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_upload_via_register_then_upload(self, client, admin_token):
        """Integration: register user, then upload avatar, verify via admin user list."""
        register_user(client, 'avatartest', 'pass123', 'Avatar User',
                      user_type='student', email='avatar@test.com')
        token = login_as(client, 'avatartest', 'pass123')

        img = _create_test_image(fmt='png')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'photo.png', 'image/png')},
            headers=auth_headers(token),
            content_type='multipart/form-data'
        )
        assert resp.status_code == 200

        # Use admin token to query user list (student cannot access user list)
        users_resp = client.get('/api/auth/users',
                                headers=auth_headers(admin_token))
        users = _json(users_resp)['data']['data']
        test_user = next(u for u in users if u['username'] == 'avatartest')
        assert test_user['avatar_url'] is not None
        assert test_user['avatar_url'].startswith('/uploads/')


class TestAvatarDelete:
    """DELETE /api/auth/avatar"""

    def test_delete_no_auth(self, client):
        resp = client.delete('/api/auth/avatar')
        assert resp.status_code == 401

    def test_delete_no_avatar(self, client, student_token):
        resp = client.delete('/api/auth/avatar',
                             headers=auth_headers(student_token))
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['message'] == '头像已删除'

    def test_delete_uploaded_avatar(self, client, admin_token):
        img = _create_test_image(fmt='png')
        # Upload
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        avatar_url = _json(resp)['data']['avatar_url']

        # Delete
        resp = client.delete('/api/auth/avatar',
                             headers=auth_headers(admin_token))
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert data['message'] == '头像已删除'

        # Verify avatar_url is now None
        resp = client.get('/api/auth/avatar',
                          headers=auth_headers(admin_token))
        data = _json(resp)
        assert data['data']['avatar_url'] is None

    def test_delete_then_reupload(self, client, admin_token):
        img = _create_test_image(fmt='png')
        # Upload
        client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        # Delete
        client.delete('/api/auth/avatar',
                      headers=auth_headers(admin_token))
        # Re-upload
        img2 = _create_test_image(fmt='jpg')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img2), 'new_avatar.jpg', 'image/jpeg')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        assert resp.status_code == 200
        assert _json(resp)['data']['avatar_url'].startswith('/uploads/')


class TestAvatarServe:
    """Serve uploaded avatar files via /uploads/<path>"""

    def test_serve_nonexistent_file(self, client):
        resp = client.get('/uploads/nonexistent.png')
        assert resp.status_code == 404

    def test_serve_path_traversal_attack(self, client):
        resp = client.get('/uploads/../../../etc/passwd')
        assert resp.status_code == 400

    def test_serve_uploaded_avatar(self, client, admin_token):
        img = _create_test_image(fmt='png')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        avatar_url = _json(resp)['data']['avatar_url']

        # Fetch the uploaded avatar
        resp = client.get(avatar_url)
        assert resp.status_code == 200
        # The served content should be the same image
        assert resp.data == img

    def test_serve_avatar_correct_mime_type(self, client, admin_token):
        img = _create_test_image(fmt='png')
        resp = client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )
        avatar_url = _json(resp)['data']['avatar_url']

        resp = client.get(avatar_url)
        assert resp.status_code == 200
        assert resp.content_type in ('image/png', 'image/jpeg', 'image/webp')


class TestAvatarInUserEndpoints:
    """Avatar URL should appear in user-related API responses."""

    def test_login_returns_avatar_url(self, client, admin_token):
        # Admin token fixture already creates admin with no avatar
        # Let's upload an avatar first
        img = _create_test_image(fmt='png')
        client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(admin_token),
            content_type='multipart/form-data'
        )

        # Login and check avatar_url is in response
        resp = client.post('/api/auth/login',
                           json={'username': 'admin', 'password': 'admin'})
        data = _json(resp)
        assert resp.status_code == 200
        assert data['data']['user']['avatar_url'] is not None
        assert data['data']['user']['avatar_url'].startswith('/uploads/')

    def test_user_list_contains_avatar_url(self, client, admin_token):
        register_user(client, 'user_with_avatar', 'pass', 'Avatar User',
                      user_type='student', email='uwa@test.com')
        user_token = login_as(client, 'user_with_avatar', 'pass')

        img = _create_test_image(fmt='png')
        client.post(
            '/api/auth/avatar/upload',
            data={'file': (io.BytesIO(img), 'avatar.png', 'image/png')},
            headers=auth_headers(user_token),
            content_type='multipart/form-data'
        )

        # Admin lists users; response structure: data.data.data (paginated)
        resp = client.get('/api/auth/users',
                          headers=auth_headers(admin_token))
        data = _json(resp)
        assert resp.status_code == 200
        users = data['data']['data']
        target = next(u for u in users if u['username'] == 'user_with_avatar')
        assert target['avatar_url'] is not None
        assert target['avatar_url'].startswith('/uploads/')

    def test_user_detail_contains_avatar_url(self, client, admin_token):
        # GET /api/auth/users/<id> is self-only — so we get the current
        # user's id from the login response instead of guessing.
        login_resp = client.post('/api/auth/login',
                                 json={'username': 'admin', 'password': 'admin'})
        login_data = _json(login_resp)
        uid = login_data['data']['user']['user_id']

        resp = client.get(f'/api/auth/users/{uid}',
                          headers=auth_headers(admin_token))
        data = _json(resp)
        assert resp.status_code == 200
        assert data['code'] == 200
        assert 'avatar_url' in data['data']
