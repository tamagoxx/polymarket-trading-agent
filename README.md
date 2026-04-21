# Polymarket Trading Agent

Python trading bot untuk Polymarket prediction markets. Fokus: **Data Fetching + Signal Analysis** menggunakan MiniMax 2.7.

## Features

- ✅ **Data Fetching** - Polymarket GraphQL API, CLOB API, orderbook
- ✅ **News Integration** - News API, RSS feeds, keyword extraction  
- ✅ **LLM Analysis** - MiniMax 2.7 for edge detection
- ✅ **CSV Export** - Signals, markets, trades for backtesting
- ✅ **HTML Dashboard** - Visual dashboard dengan stats & signals
- ✅ **Hourly Scheduler** - Auto-run scans on VPS

## Tech Stack

- **Python 3.10+**
- **MiniMax 2.7** (via OpenAI-compatible API)
- **httpx** - Async HTTP client
- **loguru** - Logging
- **pydantic** - Settings management

## Setup

```bash
# Clone / create project
cd D:/polymarket_trading_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env dengan API keys Anda
```

## Setup .env

```env
# MiniMax API (wajib)
MINIMAX_API_KEY=your_api_key_here

# News API (optional, untuk better analysis)
NEWS_API_KEY=your_newsapi_key
```

## Usage

### Run once (test)
```bash
python main.py --once
```

### Run hourly scheduler (VPS)
```bash
python main.py --hourly
```

## Output Files

| File | Description |
|------|-------------|
| `output/dashboard.html` | Visual dashboard |
| `output/signals.csv` | All signals untuk backtesting |
| `output/markets.csv` | Market data history |
| `output/trades.csv` | Trade records |
| `logs/trading_bot.log` | Application logs |

## Project Structure

```
polymarket_trading_agent/
├── src/
│   ├── config.py              # Settings & environment
│   ├── data/
│   │   ├── fetcher.py         # Polymarket API client
│   │   ├── news.py            # News fetcher
│   │   └── signal_analyzer.py # Signal generation
│   ├── agent/
│   │   └── llm.py             # MiniMax integration
│   ├── utils/
│   │   ├── logger.py          # Logging setup
│   │   ├── csv_export.py      # CSV export for backtesting
│   │   ├── dashboard.py       # HTML dashboard generator
│   │   └── scheduler.py       # Hourly scheduler
│   └── __init__.py
├── main.py                    # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Next Steps

1. ✅ Data fetching + signal + CSV + Dashboard (done)
2. 🔜 Strategy & risk management
3. 🔜 Order execution (CLOB API)
4. 🔜 Telegram alerts

## License

MIT
