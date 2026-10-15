"""Smoke test for RUN_SERVER_ONLY.py: python test_server.py"""
import RUN_SERVER_ONLY as srv
from fastapi.testclient import TestClient

c = TestClient(srv.app)

# price shapes
assert srv._min_price(5) == 5
assert srv._min_price({'Cat 1': {'min': 120, 'max': 300}, 'Cat 2': {'A': 90, 'B': 0}}) == 90
assert srv._min_price({}) is None

# both date formats FTN sends
assert srv.parse_game_date('17/03/2026').year == 2026
assert srv.parse_game_date('27/12/25').year == 2025

# teams endpoints
teams = c.get('/teams').json()
assert isinstance(teams, list)  # empty until the scraper's first run
assert all({'key', 'name', 'currency'} <= t.keys() for t in teams)
overview = c.get('/teams/overview').json()
assert isinstance(overview, list)
for row in overview[:20]:
    # overview index must point at the same game in the detail endpoint
    game = c.get(f"/teams/{row['team_key']}/game/{row['index']}").json()['game']
    assert game['url'] == row['url'], row

# SPA catch-all does not serve files outside dist
assert 'uvicorn' not in c.get('/..%2FRUN_SERVER_ONLY.py').text
assert c.get('/health').headers['x-content-type-options'] == 'nosniff'
print('ok')
