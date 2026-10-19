"""SQLite 全链路冒烟回归：真实走 HTTP 端点，逐条断言。

用法：在 backend 目录执行  .\\venv\\Scripts\\python.exe scripts\\smoke_sqlite.py
退出码 0 表示全部通过；数据库落在临时目录，不会污染 backend/data。
"""
import os
import sys
import tempfile
import traceback

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TEMP_DIR = tempfile.mkdtemp(prefix='easyinvoice_smoke_')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(TEMP_DIR, 'smoke.sqlite').replace('\\', '/')
os.environ.setdefault('SECRET_KEY', 'smoke-secret')
os.environ.setdefault('JWT_SECRET_KEY', 'smoke-jwt-secret')
os.environ['ADMIN_PASSWORD'] = 'admin'

RESULTS = []


def check(name):
    def decorator(func):
        RESULTS.append((name, func))
        return func
    return decorator


@check('管理员登录')
def _login(client, state):
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    assert payload['code'] == 200, payload
    state['token'] = payload['data']['token']
    state['headers'] = {'Authorization': f"Bearer {state['token']}"}


@check('新建赛事')
def _create_event(client, state):
    response = client.post('/api/events', json={
        'event_name': '冒烟赛事',
        'description': 'SQLite 冒烟',
        'event_start_time': '2026-01-01T00:00:00+00:00',
        'event_end_time': '2026-12-31T00:00:00+00:00',
        'total_budget': 10000,
    }, headers=state['headers'])
    assert response.status_code == 201, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    assert payload['code'] == 200, payload
    state['event_id'] = payload['data']['event_id']
    assert state['event_id'], payload


@check('赛事列表含新建赛事')
def _list_events(client, state):
    response = client.get('/api/events', headers=state['headers'], query_string={'page': 1, 'page_size': 10})
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    # 响应体是 JSON，中文被 ensure_ascii 转义，必须解析后再比对
    payload = response.get_json()
    assert payload['code'] == 200, payload
    names = [item['event_name'] for item in payload['data']['data']]
    assert '冒烟赛事' in names, names


@check('操作日志可查询')
def _operation_logs(client, state):
    response = client.get(
        '/api/operation-logs',
        headers=state['headers'],
        query_string={'page': 1, 'per_page': 10},
    )
    assert response.status_code == 200, response.get_data(as_text=True)[:300]


@check('发起手动备份')
def _manual_backup(client, state):
    response = client.post('/api/system/backup', headers=state['headers'])
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    payload = response.get_json()
    assert payload['code'] == 200, payload
    state['backup_id'] = payload['data']['id']
    assert state['backup_id']


@check('备份记录可见')
def _list_backups(client, state):
    response = client.get('/api/system/backups', headers=state['headers'])
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    items = response.get_json()['data']['items']
    assert any(item['id'] == state['backup_id'] for item in items), items


def main():
    from app import create_app

    application = create_app()
    failures = 0

    with application.test_client() as client:
        state = {}
        for name, func in RESULTS:
            try:
                func(client, state)
                print(f'PASS  {name}')
            except Exception as error:
                failures += 1
                print(f'FAIL  {name}: {error}')
                traceback.print_exc()

    print(f'\n共 {len(RESULTS)} 项，失败 {failures} 项')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
