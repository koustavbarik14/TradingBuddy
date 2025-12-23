# 📈 Stock Screener Pro

A professional stock screening dashboard for swing trading, built with React. Automatically analyzes US stocks using technical indicators and scores them based on breakout potential.

## Features

✅ **Automated Technical Analysis**
- EMA (20, 50, 200 day)
- RSI (14-period)
- MACD signals
- Volume analysis
- Support/Resistance detection
- Breakout pattern recognition

✅ **Smart Scoring System**
- Ranks stocks 0-100 based on technical setup quality
- Prioritizes consolidation breakouts and trend strength
- Filters out low-probability setups

✅ **Interactive Dashboard**
- Visual stock cards with key metrics
- Interactive price charts
- Customizable filters
- Watchlist management
- Persistent data caching (24 hours)

✅ **Optimized for Swing Trading**
- Monthly position selection workflow
- Focus on 6-8 high-probability setups
- Risk-managed approach

## Quick Start

### 1. Prerequisites
- Node.js v16+ installed ([Download here](https://nodejs.org/))
- VS Code or any text editor
- Basic command line knowledge

### 2. Installation

```bash
# Navigate to your projects folder
cd ~/projects

# Clone or download the project
# (Or manually create the folder structure from the artifacts)

# Install dependencies
npm install
```

### 3. Get Free API Key

1. Visit [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. Enter your email
3. Get your free API key (instant)
4. Copy the key

### 4. Configure Environment

Create a `.env` file in the root directory:

```bash
REACT_APP_ALPHA_VANTAGE_KEY=YOUR_KEY_HERE
```

Replace `YOUR_KEY_HERE` with your actual API key.

### 5. Run the Application

```bash
npm start
```

The app opens at `http://localhost:3000`

## First Time Setup

**Initial Data Load:**
- Click "Refresh Data" button
- First scan takes 10-15 minutes (API rate limits)
- Progress shown on screen
- Data cached for 24 hours after completion
- Subsequent loads are instant from cache

**Expected behavior:**
- Scans 50 popular US stocks
- Calculates technical indicators
- Generates scores and signals
- Stores in browser cache

## How to Use

### 1. Daily Workflow (5-10 minutes)

**After Market Close:**
1. Open the app (loads cached data instantly)
2. Review top-scored stocks (70+ score)
3. Check signals and charts
4. Add promising setups to watchlist

**Weekly Deep Dive:**
1. Click "Refresh Data" to get latest prices
2. Review all filtered results
3. Select 6-8 positions for the month
4. Monitor watchlist daily

### 2. Understanding the Score

**90-100:** Exceptional setup - strong trend, multiple signals
**75-89:** Strong setup - good entry point
**60-74:** Decent setup - monitor for confirmation
**50-59:** Marginal setup - needs more confirmation
**Below 50:** Weak setup - skip

### 3. Reading the Signals

Each stock shows signals like:
- "Strong uptrend - above all EMAs" → Trend is your friend
- "RSI healthy (55)" → Not overbought or oversold
- "Bullish breakout detected!" → Just broke resistance
- "Consolidating - potential breakout" → Watch closely
- "Near 52-week high" → Momentum play

### 4. Using the Charts

- Green line = Resistance (target/exit)
- Red line = Support (stop loss level)
- Blue line = Price action
- Look for: clean uptrends, consolidations, breakouts

### 5. Building Your Monthly Portfolio

**Goal:** 6-8 positions, 50-60% win rate

**Selection criteria:**
1. Score ≥ 70
2. At least 3 positive signals
3. Clean chart pattern
4. Consolidating or early breakout
5. Above 20 & 50 EMA

**Position sizing with £1000:**
- £125-166 per position
- Stop loss at support level
- Target at resistance level
- Risk 1-2% per trade (£10-20)

## Customization

### Change Stock Universe

Edit `src/services/apiService.js`:

```javascript
export const STOCK_UNIVERSE = [
  'AAPL', 'MSFT', // Add or remove symbols
];
```

### Adjust Scoring Weights

Edit `src/services/technicalAnalysis.js` in the `calculateScore` function:

```javascript
// Example: Give more weight to RSI
if (rsi >= 40 && rsi <= 65) {
  score += 20; // Changed from 15
}
```

### Change Technical Parameters

In `technicalAnalysis.js`:
- RSI period: `calculateRSI(data, 14)` → change 14
- EMA lengths: `calculateEMA(data, 20)` → change 20
- Consolidation threshold: `volatility < 10` → change 10

## Troubleshooting

### "API key invalid" Error
- Check `.env` file exists in root directory
- Ensure key has no spaces: `REACT_APP_ALPHA_VANTAGE_KEY=ABC123`
- Restart dev server: Ctrl+C, then `npm start`

### "Rate limit exceeded"
- Free tier: 25 calls per day
- Wait 24 hours or get another free key
- Use cached data until reset

### Slow Loading
- Normal: First load takes 10-15 minutes
- API allows 5 calls per minute
- 50 stocks = ~10 minutes with delays
- Data cached for 24 hours

### CORS Errors
- Alpha Vantage supports CORS
- If issues persist, try [Finnhub](https://finnhub.io/) instead
- Change API in `apiService.js`

### No Data Showing
- Check browser console (F12) for errors
- Verify API key is correct
- Ensure internet connection
- Try clearing cache: browser dev tools → Application → Clear storage

## API Limits & Costs

**Alpha Vantage Free Tier:**
- 25 API calls per day
- 5 calls per minute
- No credit card required
- Sufficient for daily screening

**Upgrade (optional):**
- $50/month for 75 calls/day
- Only needed if screening >75 stocks

## Project Structure

```
stock-screener/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/
│   │   ├── StockCard.js    # Individual stock display
│   │   ├── StockChart.js   # Price charts with indicators
│   │   ├── Filters.js      # Filter controls
│   │   └── Watchlist.js    # Watchlist component
│   ├── services/
│   │   ├── apiService.js   # API calls & caching
│   │   └── technicalAnalysis.js  # TA calculations
│   ├── styles/
│   │   └── App.css         # All styles
│   ├── App.js              # Main app component
│   └── index.js            # React entry point
├── .env                    # API key (create this)
├── package.json            # Dependencies
└── README.md              # This file
```

## Technology Stack

- **React 18** - UI framework
- **Recharts** - Chart visualization
- **Axios** - HTTP requests
- **date-fns** - Date formatting
- **Alpha Vantage API** - Stock data

## Tips for Success

1. **Be Patient:** First load takes time, but worth it
2. **Trust the System:** High scores = high probability setups
3. **Use Watchlist:** Track your favorites, review daily
4. **Check Trading 212:** Always verify setup on real charts
5. **Set Alerts:** Use Trading 212's alerts for breakouts
6. **Keep Notes:** Track what works, refine over time
7. **Risk Management:** Never skip stop losses
8. **Currency Impact:** Remember FX fees on Trading 212

## Deployment (Optional)

### Vercel (Recommended)

```bash
npm install -g vercel
vercel
```

Follow prompts, add API key as environment variable.

### Netlify

```bash
npm run build
```

Drag `build` folder to [Netlify Drop](https://app.netlify.com/drop)

### GitHub Pages

Follow [React deployment guide](https://create-react-app.dev/docs/deployment/#github-pages)

## Support & Updates

**Need Help?**
- Check browser console for errors
- Review troubleshooting section
- Verify API key configuration

**Want to Contribute?**
- Add more technical indicators
- Implement sector filtering
- Add fundamental data
- Improve scoring algorithm

## Disclaimer

This tool is for educational purposes only. Not financial advice. Always do your own research before trading. Past performance doesn't guarantee future results.

## License

Free to use and modify for personal use.

---

**Happy Trading! 📈**

Remember: Consistency and discipline beat complexity. Use this tool to identify high-probability setups, then execute your plan systematically.