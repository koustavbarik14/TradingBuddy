from tradingbuddy.api.flask_app import create_app
app = create_app()
client = app.test_client()
# Try adding watchlist
resp = client.post('/api/watchlist', json={'symbol':'AAPL'})
print('POST /api/watchlist', resp.status_code, resp.get_data(as_text=True))
# Get watchlist
resp = client.get('/api/watchlist')
print('GET /api/watchlist', resp.status_code, resp.get_data(as_text=True))
# Try screen
resp = client.get('/api/screen?limit=5')
print('/api/screen', resp.status_code, resp.get_data(as_text=True)[:800])
# Try ohlc for AAPL
resp = client.get('/api/ohlc?symbol=AAPL&days=30')
print('/api/ohlc', resp.status_code)
if resp.status_code==200:
    data = resp.get_json()
    print('rows', len(data.get('rows',[])))
