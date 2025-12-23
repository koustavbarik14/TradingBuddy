import json
from tradingbuddy.api.flask_app import create_app


def test_api_screen_basic():
    app = create_app(db_path=':memory:')
    client = app.test_client()
    # ensure endpoint responds
    r = client.get('/api/screen')
    assert r.status_code == 200
    data = r.get_json()
    assert 'results' in data
    assert isinstance(data['results'], list)
