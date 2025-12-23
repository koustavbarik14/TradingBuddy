# Stock Screener (frontend)

This is the React frontend for the Stock Screener prototype. It uses free APIs (Alpha Vantage) to fetch end-of-day data and runs technical calculations in the browser.

Quick start (Windows PowerShell):

```powershell
cd frontend
# install deps once
npm install
# create a .env file (or copy .env.example)
# Windows PowerShell example:
# copy .env.example .env
# then edit .env
npm start
```

Open http://localhost:3000 in your browser.

Notes:
- Set `REACT_APP_ALPHA_VANTAGE_KEY` in `.env` with your Alpha Vantage key.
- The first full scan of many stocks may be rate-limited by Alpha Vantage; this app is designed for end-of-day scanning and caching.
