"""Market resolution tracker — check if signals' markets have resolved."""
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from src.data.fetcher import PolymarketFetcher


class ResolutionTracker:
    """Track market resolution status and calculate P&L for signals."""

    def __init__(self, signals_csv: str = "output/signals.csv"):
        self.signals_csv = Path(signals_csv)
        self.fetcher = PolymarketFetcher()

    async def close(self):
        await self.fetcher.close()

    def _parse_signal_price(self, prices_str: str) -> Tuple[float, float]:
        """Parse outcomePrices string like '["0.53","0.47"]' into (yes_price, no_price)."""
        import json
        try:
            parsed = json.loads(prices_str)
            return float(parsed[0]), float(parsed[1])
        except (json.JSONDecodeError, TypeError, IndexError):
            return 0.5, 0.5

    def _determine_outcome(self, prices_str: str) -> Optional[str]:
        """
        Determine winning outcome from outcomePrices string.
        Returns: "YES", "NO", "VOID", or None (unknown)
        """
        import json
        try:
            parsed = json.loads(prices_str)
            p0, p1 = float(parsed[0]), float(parsed[1])
        except (json.JSONDecodeError, TypeError, IndexError):
            return None

        # Void: both 0 (no winner)
        if p0 == 0 and p1 == 0:
            return "VOID"

        # Resolved: one is 1.0, other is 0.0
        if (p0 == 1.0 and p1 == 0.0) or (p0 == 0.0 and p1 == 1.0):
            # outcome[0] = YES, outcome[1] = NO (standard Polymarket)
            return "YES" if p0 == 1.0 else "NO"

        return None  # Not resolved yet

    async def check_market_resolution(self, market_id: str) -> Dict:
        """Check if a specific market has resolved and return outcome info."""
        markets = await self.fetcher.get_markets(limit=200)
        for m in markets:
            if m.id == market_id:
                return {
                    "market_id": market_id,
                    "question": m.question,
                    "closed": m.closed,
                    "outcome_prices": m.prices,
                    "outcome": self._determine_outcome(m.prices),
                    "resolved": m.closed and self._determine_outcome(m.prices) in ("YES", "NO", "VOID"),
                }
        return {"market_id": market_id, "resolved": False, "error": "Market not found"}

    async def check_bulk_resolutions(self, market_ids: List[str]) -> Dict[str, Dict]:
        """Check resolution for multiple markets at once (single API call)."""
        # Fetch all markets once
        markets = await self.fetcher.get_markets(limit=500, closed=True)
        markets += await self.fetcher.get_markets(limit=500, closed=False)

        # Build lookup dict
        market_map = {m.id: m for m in markets}

        results = {}
        for mid in market_ids:
            m = market_map.get(mid)
            if m:
                results[mid] = {
                    "market_id": mid,
                    "question": m.question,
                    "closed": m.closed,
                    "outcome_prices": m.prices,
                    "outcome": self._determine_outcome(m.prices),
                    "resolved": m.closed and self._determine_outcome(m.prices) in ("YES", "NO", "VOID"),
                }
            else:
                results[mid] = {"market_id": mid, "resolved": False, "error": "Not found"}

        return results

    def load_pending_signals(self, min_edge: float = 0.05) -> List[Dict]:
        """Load signals from CSV that haven't been tracked as trades yet."""
        if not self.signals_csv.exists():
            return []

        # Load existing trade IDs
        trades_file = self.signals_csv.parent / "trades.csv"
        tracked_ids = set()
        if trades_file.exists():
            with open(trades_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    market_id = row.get("market_id", "")
                    signal_ts = row.get("timestamp", "")
                    if market_id:
                        tracked_ids.add((market_id, signal_ts[:19]))

        # Load pending signals
        pending = []
        with open(self.signals_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                edge = abs(float(row.get("edge", 0)))
                if edge < min_edge:
                    continue

                sig_id = (row.get("market_id", ""), row.get("timestamp", "")[:19])
                if sig_id in tracked_ids:
                    continue

                signal_type = row.get("signal_type", "")
                if signal_type not in ("BUY", "SELL"):
                    continue

                pending.append(row)

        return pending

    def record_trade_from_signal(self, signal: Dict, outcome: str, pnl: float) -> str:
        """Record a resolved trade with outcome and P&L."""
        import hashlib

        trade_id = f"TRADE_{hashlib.md5((signal.get('market_id','') + signal.get('timestamp','')).encode()).hexdigest()[:8].upper()}"
        trade = {
            "trade_id": trade_id,
            "timestamp": signal.get("timestamp", ""),
            "market_id": signal.get("market_id", ""),
            "question": signal.get("question", ""),
            "outcome": outcome,
            "direction": signal.get("signal_type", ""),
            "size_usd": signal.get("recommended_size", 10),
            "price": signal.get("prices", ""),
            "signal_edge": signal.get("edge", 0),
            "signal_confidence": signal.get("confidence", 0),
            "status": "closed",
            "pnl": pnl,
            "notes": "",
        }

        # Append to trades CSV
        trades_file = self.signals_csv.parent / "trades.csv"
        if not trades_file.exists():
            headers = [
                "trade_id", "timestamp", "market_id", "question", "outcome",
                "direction", "size_usd", "price", "signal_edge", "signal_confidence",
                "status", "pnl", "notes",
            ]
            with open(trades_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

        with open(trades_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(trade.keys()))
            writer.writerow(trade)

        return trade_id

    def calculate_signal_pnl(
        self,
        signal: Dict,
        outcome: str,
        yes_entry_price: float,
        no_entry_price: float,
        bet_size: float = 10.0,
    ) -> float:
        """
        Calculate P&L for a signal given the resolution outcome.

        BUY signal → betting YES outcome
        SELL signal → betting NO outcome

        Polymarket: if you buy YES at price P and YES wins, P&L = size * (1-P)
        If NO wins, P&L = -size * P
        """
        direction = signal.get("signal_type", "")
        if direction == "BUY":
            # Bought YES
            if outcome == "YES":
                pnl = bet_size * (1 - yes_entry_price)  # won
            elif outcome == "NO":
                pnl = -bet_size * yes_entry_price  # lost
            else:  # VOID
                pnl = 0
        elif direction == "SELL":
            # Bought NO (sold YES)
            if outcome == "NO":
                pnl = bet_size * (1 - no_entry_price)  # won
            elif outcome == "YES":
                pnl = -bet_size * no_entry_price  # lost
            else:
                pnl = 0
        else:
            pnl = 0

        return round(pnl, 4)
