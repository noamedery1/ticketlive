"""Smoke test for RUN_SERVER_ONLY.py: python test_server.py"""
import base64
import os

os.environ['ADMIN_PASSWORD'] = 'test-pass'
import RUN_SERVER_ONLY as srv
from fastapi.testclient import TestClient

c = TestClient(srv.app)

# price shapes
assert srv._min_price(5) == 5
assert srv._min_price({'Cat 1': {'min': 120, 'max': 300}, 'Cat 2': {'A': 90, 'B': 0}}) == 90
assert srv._min_price({}) is None

# excel formula injection
assert srv._excel_safe('=HYPERLINK("x")') == '\'=HYPERLINK("x")'
assert srv._excel_safe('cat1 100') == 'cat1 100'

# teams endpoints
teams = c.get('/teams').json()
assert teams and {'key', 'name', 'currency'} <= teams[0].keys()
overview = c.get('/teams/overview').json()
assert isinstance(overview, list)
for row in overview[:20]:
    # overview index must point at the same game in the detail endpoint
    game = c.get(f"/teams/{row['team_key']}/game/{row['index']}").json()['game']
    assert game['url'] == row['url'], row

# offers API is private
assert c.get('/api/tickets/sellers').status_code == 401
bad = base64.b64encode(b'x:wrong').decode()
assert c.get('/api/tickets/sellers', headers={'Authorization': f'Basic {bad}'}).status_code == 401
good = base64.b64encode(b'x:test-pass').decode()
assert c.get('/api/tickets/sellers', headers={'Authorization': f'Basic {good}'}).status_code == 200

# world cup routes are gone; SPA catch-all does not leak files outside dist
assert c.get('/history?match_url=x').status_code in (200, 404)  # served by SPA, not the API
assert 'ADMIN' not in c.get('/..%2F.env').text
assert c.get('/health').headers['x-content-type-options'] == 'nosniff'
print('ok')
