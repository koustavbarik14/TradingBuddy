# TradingBuddy 📈

**Advanced Stock Technical Analysis & Breakout Detection Platform**

TradingBuddy is a comprehensive trading analysis system that combines machine learning-powered breakout detection with traditional technical analysis across multiple timeframes (daily, weekly, monthly).

## Features

- **ML-Powered Breakout Detection** - Automated pattern recognition for multiple breakout types (Darvas Box, Volume Surge, Consolidation, Flag, Cup & Handle)
- **Multi-Timeframe Analysis** - Scan and analyze stocks across daily, weekly, and monthly charts
- **Interactive Charts** - Dynamic visualization with TradingView-style and Plotly charts
- **Technical Scanner** - RSI, MACD, Bollinger Bands, and volume analysis
- **Trade Management** - Track and manage positions with entry/exit prices
- **Real-Time Data** - Integration with Yahoo Finance for current market data

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd TradingBuddy

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate.ps1  # Windows PowerShell
# OR: source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the Flask backend
python -m tradingbuddy.api.flask_app

# OR use PowerShell script
.\run_app.ps1
```

The application will be available at `http://localhost:5000`

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=tradingbuddy --cov-report=html

# Run specific test file
pytest tests/test_ml_breakouts.py -v
```

## Usage

### Breakout Detection

```python
from tradingbuddy.features.ml_breakouts import MLBreakoutDetector

# Initialize detector for weekly timeframe
detector = MLBreakoutDetector(timeframe='weekly')

# Detect patterns for a symbol
patterns = detector.detect_all_patterns('AAPL')

for pattern in patterns:
    print(f"{pattern.symbol}: {pattern.pattern_type} - {pattern.confidence:.2f}")
```

### Technical Scanner

```python
from tradingbuddy.features.scanner import TechnicalScanner

scanner = TechnicalScanner()
signals = scanner.scan_universe(['AAPL', 'MSFT', 'GOOGL'])
```

### Chart Generation

```python
from tradingbuddy.visualization.plotly_charts import create_pattern_chart

# Generate chart for a detected pattern
chart_html = create_pattern_chart(pattern_data, 'AAPL')
```

## Architecture

### Project Structure

```
TradingBuddy/
├── tradingbuddy/
│   ├── api/              # Flask API and web interface
│   ├── features/         # Core trading features
│   │   ├── ml_breakouts.py    # ML pattern detection
│   │   ├── scanner.py         # Technical indicator scanner
│   │   ├── patterns.py        # Pattern definitions
│   │   └── stock_info.py      # Stock data retrieval
│   ├── visualization/    # Chart generation modules
│   └── data/            # Data storage
├── tests/               # Comprehensive test suite
└── requirements.txt
```

### Core Components

**MLBreakoutDetector** - Machine learning-based pattern detection engine supporting:
- Darvas Box breakouts
- Volume surge breakouts
- Consolidation breakouts
- Flag patterns
- Cup & Handle formations

**TechnicalScanner** - Technical indicator analysis:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Volume analysis

**Data Management** - SQLite-based storage for historical price data with automatic caching

## API Endpoints

### Breakout Detection
- `GET /api/ml_breakouts?timeframe=daily&limit=20` - Get detected breakouts
- `GET /api/breakout_chart/<symbol>?timeframe=weekly` - Generate pattern chart

### Stock Information
- `GET /api/stock_info/<symbol>` - Get current stock information

### Scanner
- `POST /api/scanner` - Run technical scanner on universe
- `GET /api/scanner_results` - Get latest scanner results

### Trade Management
- `GET /api/positions` - Get all positions
- `POST /api/positions` - Add new position
- `PUT /api/positions/<id>` - Update position
- `DELETE /api/positions/<id>` - Remove position

## Configuration

### Pattern Detection Settings

Edit pattern thresholds in `tradingbuddy/features/ml_breakouts.py`:

```python
# Adjust minimum candle requirements per timeframe
MIN_CANDLES = {
    'daily': 100,
    'weekly': 50,
    'monthly': 30
}
```

### Stock Universe

Configure the stock universe in `tradingbuddy/api/flask_app.py`:

```python
STOCK_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
    # Add your symbols here
]
```

## Testing

The project includes comprehensive test coverage:

- **test_ml_breakouts.py** - ML detector initialization and pattern detection
- **test_api.py** - API endpoint testing
- **test_data_ingestion.py** - Data storage and retrieval
- **test_scanner.py** - Technical indicator calculations
- **test_visualization.py** - Chart generation
- **test_integration.py** - End-to-end workflows

Run tests with pytest:
```bash
pytest tests/ -v --cov=tradingbuddy
```

## Dependencies

- **Flask** - Web framework
- **pandas** - Data manipulation
- **numpy** - Numerical computations
- **yfinance** - Market data retrieval
- **plotly** - Interactive charts
- **scikit-learn** - Machine learning utilities
- **pytest** - Testing framework

See `requirements.txt` for complete list.

## Troubleshooting

### Charts Not Displaying
- Ensure proper timeframe parameter is passed to chart endpoints
- Check browser console for JavaScript errors
- Verify data exists for the selected symbol and timeframe

### No Patterns Detected
- Verify stock universe has sufficient historical data
- Check pattern thresholds in ml_breakouts.py
- Ensure timeframe has enough candles (daily: 100, weekly: 50, monthly: 30)

### API Errors
- Check Flask app is running on port 5000
- Verify all dependencies are installed
- Review Flask logs for error messages

### Test Failures
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Network-dependent tests will skip if offline
- Run individual test files to isolate issues

## Performance

- **Breakout Detection**: ~2-5 seconds for 20 stocks
- **Chart Generation**: ~0.5-1 second per chart
- **Data Caching**: SQLite-based, automatic refresh every 24 hours

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is provided as-is for educational and personal use.

---

**Note**: This is a trading analysis tool for educational purposes. Always conduct your own research and never risk more than you can afford to lose.