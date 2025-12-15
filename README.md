# TradingBuddy — Techno-Fundamental Starter

TradingBuddy is a starter scaffold for a techno-fundamental analysis tool that combines
technical indicators, pattern detection, fundamentals, and a Streamlit dashboard.

Project layout (important files/directories):

- `tradingbuddy/` — Python package containing core modules (`core.py`) and package exports
- `data/` — ingestion helpers
- `features/` — technical indicator and pattern detection helpers
- `models/` — forecasting integrations (placeholder for TimeGPT/Nixtla)
- `visualization/` — Streamlit dashboard
- `api/` — FastAPI app and scheduler
- `tests/` — pytest unit tests
- `requirements.txt` — project dependencies

Setup & run (bash)

1) Create a virtual environment in the project root

```bash
python -m venv .venv
```

2) Install dependencies into the venv

```bash
.venv/Scripts/python.exe -m pip install --upgrade pip
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

3) Run the Streamlit dashboard (optional)

```bash
.venv/Scripts/python.exe -m streamlit run visualization/dashboard.py
```

4) Run the Flask web service (main production-like entry)

Run in development mode:

```bash
.venv/Scripts/python.exe -m tradingbuddy.api.flask_app
```


```bash
.venv/Scripts/python.exe -m waitress.cli --call "tradingbuddy.api.flask_app:create_app"
```

Run in development mode:

```bash
		.venv\Scripts\Activate.ps1; python -m flask --app tradingbuddy.api.flask_app run --reload

Run in production with waitress (call the factory). This will invoke the
	create_app() factory exported by `tradingbuddy.api.flask_app`:

		.venv\Scripts\Activate.ps1; .venv\Scripts\waitress-serve.exe --call "tradingbuddy.api.flask_app:create_app" --listen=0.0.0.0:8080

	The `--call` form tells waitress to call the factory function and use the returned WSGI app.

5) Run tests

```bash
.venv/Scripts/python.exe -m pytest -q
```

Notes

- The package is wired as `tradingbuddy` (import core classes via `from tradingbuddy import DataIngestion`).
- Pattern detectors are heuristic starters — validate their results visually before using them in production.
- `models/timegpt_integration.py` is a placeholder for Nixtla/TimeGPT integration.

This README is a concise setup guide and project overview.