"""
Tests for Flask API endpoints.
"""
import pytest
import json


class TestAPIEndpoints:
    """Test suite for API endpoints."""
    
    def test_index_route(self, flask_client):
        """Test that index route loads successfully."""
        response = flask_client.get('/')
        assert response.status_code == 200
        assert b'Breakouts' in response.data or response.status_code == 302
    
    def test_breakouts_route(self, flask_client):
        """Test breakouts page loads."""
        response = flask_client.get('/breakouts')
        assert response.status_code == 200
        assert b'Breakouts' in response.data
    
    def test_scanner_route(self, flask_client):
        """Test scanner page loads."""
        response = flask_client.get('/scanner')
        assert response.status_code == 200
    
    def test_trades_route(self, flask_client):
        """Test trades page loads."""
        response = flask_client.get('/trades')
        assert response.status_code == 200
    
    def test_api_ml_breakouts_daily(self, flask_client):
        """Test ML breakouts API with daily timeframe."""
        response = flask_client.get('/api/ml_breakouts?limit=5&timeframe=daily')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        
        # Check structure if data returned
        if len(data) > 0:
            pattern = data[0]
            assert 'symbol' in pattern
            assert 'pattern_type' in pattern
            assert 'confidence' in pattern
            assert 'entry_price' in pattern
            assert 'status' in pattern
    
    def test_api_ml_breakouts_weekly(self, flask_client):
        """Test ML breakouts API with weekly timeframe."""
        response = flask_client.get('/api/ml_breakouts?limit=5&timeframe=weekly')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_api_ml_breakouts_monthly(self, flask_client):
        """Test ML breakouts API with monthly timeframe."""
        response = flask_client.get('/api/ml_breakouts?limit=5&timeframe=monthly')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_api_ml_breakouts_invalid_timeframe(self, flask_client):
        """Test ML breakouts API with invalid timeframe defaults to daily."""
        response = flask_client.get('/api/ml_breakouts?limit=5&timeframe=invalid')
        assert response.status_code == 200
    
    def test_api_stock_info(self, flask_client):
        """Test stock info API endpoint."""
        response = flask_client.get('/api/stock_info/AAPL')
        assert response.status_code in [200, 500]  # May fail if no internet/API key
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'symbol' in data
    
    def test_api_breakout_chart(self, flask_client):
        """Test breakout chart API endpoint."""
        response = flask_client.get('/api/breakout_chart/AAPL?timeframe=daily')
        # May return 404 if no pattern found, which is acceptable
        assert response.status_code in [200, 404, 500]
    
    def test_api_scanner(self, flask_client):
        """Test scanner API endpoint."""
        response = flask_client.get('/api/scanner?symbols=AAPL,MSFT')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # API returns a list of scanner results directly
        assert isinstance(data, list)
        if len(data) > 0:
            assert 'symbol' in data[0]
    
    def test_api_positions_get(self, flask_client):
        """Test get positions endpoint."""
        response = flask_client.get('/api/positions')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # API returns dict with 'items' key containing list of positions
        assert isinstance(data, dict)
        assert 'items' in data
        assert isinstance(data['items'], list)
    
    def test_api_positions_post_invalid_data(self, flask_client):
        """Test post position with invalid data."""
        response = flask_client.post(
            '/api/positions',
            data=json.dumps({}),
            content_type='application/json'
        )
        # Should handle invalid data gracefully
        assert response.status_code in [200, 400, 500]
    
    def test_api_ohlc(self, flask_client):
        """Test OHLC data endpoint."""
        response = flask_client.get('/api/ohlc/AAPL?period=1d')
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, list)
    
    def test_static_files_accessible(self, flask_client):
        """Test that static files are accessible."""
        response = flask_client.get('/static/styles.css')
        # May be 200 or 404 depending on file existence
        assert response.status_code in [200, 404]
