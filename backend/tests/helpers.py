"""
Shared test helper functions.
Import from test files with: from tests.helpers import _json, login_as, ...
"""


def _json(response):
    """Parse JSON from a Flask test response."""
    return response.get_json()


def login_as(client, username='admin', password='admin'):
    """Login and return the JWT token string."""
    resp = client.post('/api/auth/login',
                       json={'username': username, 'password': password})
    data = _json(resp)
    if data and data.get('code') == 200:
        return data['data']['token']
    return None


def register_user(client, username, password, real_name,
                  user_type='student', email=None, code=None):
    """Register a new user and return the Flask response.

    Note: backend auth.py uses data['email'] directly (not .get()),
    so we always include email to prevent KeyError.
    """
    payload = {
        'username': username,
        'password': password,
        'real_name': real_name,
        'user_type': user_type,
        'email': email if email else f'{username}@auto.test',
    }
    if code:
        payload['invitation_code'] = code
    return client.post('/api/auth/register', json=payload)


def auth_headers(token):
    """Return Authorization header dict for a JWT token."""
    return {'Authorization': f'Bearer {token}'}
