from fastapi import FastAPI, BackgroundTasks
from tradingbuddy.core import DataIngestion, PatternDetection
from tradingbuddy.features.technical import add_indicators
import uvicorn
import threading

app = FastAPI(title="TradingBuddy API")

# Initialize singletons (in-memory for this starter)
DI = DataIngestion()
PD = PatternDetection()

# Simple in-memory list of tracked symbols
TRACKED = set()

@app.post("/track/{symbol}")
async def track_symbol(symbol: str):
    symbol = symbol.upper()
    TRACKED.add(symbol)
    return {"tracked": list(TRACKED)}

@app.get("/screen/{symbol}")
async def screen_symbol(symbol: str):
    symbol = symbol.upper()
    # ensure we have data
    df = DI.get_price_data(symbol, days=365)
    if df.empty:
        # try a quick update
        DI.update_stock(symbol)
        df = DI.get_price_data(symbol, days=365)
        if df.empty:
            return {"error": "no data"}
    # normalize and compute indicators
    df.columns = [c.lower() for c in df.columns]
    df = add_indicators(df)
    analysis = PD.analyze_stock(df)
    return {"symbol": symbol, "analysis": analysis}

@app.post("/update_all")
async def update_all(background_tasks: BackgroundTasks):
    # Schedule update in background
    background_tasks.add_task(DI.update_multiple_stocks, list(TRACKED))
    return {"scheduled": len(TRACKED)}

# Very small helper to run a periodic updater in a separate thread (starter only)
def _periodic_updater(interval_seconds: int = 3600):
    import time
    while True:
        symbols = list(TRACKED)
        if symbols:
            DI.update_multiple_stocks(symbols)
        time.sleep(interval_seconds)

@app.post("/start_scheduler")
async def start_scheduler(interval_seconds: int = 3600):
    thread = threading.Thread(target=_periodic_updater, args=(interval_seconds,), daemon=True)
    thread.start()
    return {"started": True, "interval_seconds": interval_seconds}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
