# AI-Enhanced Alpaca Trading Bot

An incremental, paper-only US-equities trading-system project. The detailed
roadmap is in `AI_Enhanced_Alpaca_Trading_Bot_Development_Plan_For_Coding_AI.md`.

## Current progress

Phases 0–7 are implemented: centralized paper-only Alpaca access, validated
market data, SQLite persistence, technical features, and a deterministic
strategy that produces auditable signals. Phase 8, backtesting, is next.

The project does not submit orders. `Signal` objects are recommendations only;
risk, portfolio, and order execution are later phases.

## Local setup on Windows

Use Python 3.12 or another Python version supported by both Windows and the
Raspberry Pi environment. Each machine needs its own virtual environment.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -v
```

Copy `.env.example` to `.env` and enter only Alpaca Paper Trading credentials.
Keep `ALPACA_PAPER=true`. `.env`, SQLite files, downloaded data, and virtual
environments are excluded from Git.

## Project layout

- `app/broker/`: paper-only Alpaca client
- `app/data/`: normalized market data, exchange-calendar validation, SQLite
- `app/ai/`: technical feature calculations
- `app/strategy/`: strategy contract and `trend_following_v1`
- `tests/`: unit tests with no broker calls

## Cross-platform operation

Develop and test on Windows, commit the reviewed repository, and pull it onto
the Raspberry Pi. Install dependencies and configure a separate `.env` on the
Pi. Do not copy the Windows `.venv` or local database to the Pi.

The automated tests have been run on Windows. Run the same test command on the
Pi before deployment; Pi validation has not yet been performed.
