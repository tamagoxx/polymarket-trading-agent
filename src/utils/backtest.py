"""Backtest engine — analyze historical signal performance."""
import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from loguru import logger


class BacktestAnalyzer:
    """Analyze signal and trade history to compute performance metrics."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.trades_file = self.output_dir / "trades.csv"
        self.signals_file = self.output_dir / "signals.csv"

    def load_trades(self, status: Optional[str] = None) -> List[Dict]:
        """Load trades from CSV. Filter by status if provided."""
        if not self.trades_file.exists():
            return []

        trades = []
        with open(self.trades_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if status and row.get("status") != status:
                    continue
                trades.append({
                    "trade_id": row["trade_id"],
                    "timestamp": row["timestamp"],
                    "market_id": row["market_id"],
                    "question": row["question"],
                    "outcome": row["outcome"],
                    "direction": row["direction"],
                    "size_usd": float(row["size_usd"]) if row["size_usd"] else 0,
                    "price": row["price"],
                    "signal_edge": float(row["signal_edge"]) if row["signal_edge"] else 0,
                    "signal_confidence": float(row["signal_confidence"]) if row["signal_confidence"] else 0,
                    "status": row["status"],
                    "pnl": float(row["pnl"]) if row["pnl"] else 0,
                    "notes": row.get("notes", ""),
                })
        return trades

    def load_signals(self) -> List[Dict]:
        """Load all signals from CSV."""
        if not self.signals_file.exists():
            return []

        signals = []
        with open(self.signals_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                signals.append({
                    "timestamp": row["timestamp"],
                    "market_id": row["market_id"],
                    "question": row["question"],
                    "outcomes": row.get("outcomes", ""),
                    "prices": row.get("prices", ""),
                    "volume": float(row["volume"]) if row["volume"] else 0,
                    "liquidity": float(row["liquidity"]) if row["liquidity"] else 0,
                    "signal_type": row["signal_type"],
                    "edge": float(row["edge"]) if row["edge"] else 0,
                    "confidence": float(row["confidence"]) if row["confidence"] else 0,
                    "recommended_size": float(row["recommended_size"]) if row["recommended_size"] else 0,
                    "reasoning": row.get("reasoning", ""),
                })
        return signals

    def compute_metrics(self, trades: List[Dict]) -> Dict[str, Any]:
        """Compute comprehensive performance metrics from trades."""
        if not trades:
            return {
                "error": "No closed trades found for analysis",
                "total_trades": 0,
            }

        closed = [t for t in trades if t["status"] == "closed"]
        if not closed:
            return {"error": "No closed trades", "total_trades": 0}

        total = len(closed)
        winners = [t for t in closed if t["pnl"] > 0]
        losers = [t for t in closed if t["pnl"] < 0]
        voids = [t for t in closed if t.get("outcome") == "VOID"]

        total_pnl = sum(t["pnl"] for t in closed)
        total_invested = sum(t["size_usd"] for t in closed)
        win_rate = len(winners) / total if total > 0 else 0

        # Avg metrics
        avg_edge = sum(t["signal_edge"] for t in closed) / total
        avg_conf = sum(t["signal_confidence"] for t in closed) / total
        avg_pnl = total_pnl / total if total > 0 else 0

        # ROI
        roi = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        # Max drawdown
        cumulative = []
        running = 0
        for t in sorted(closed, key=lambda x: x["timestamp"]):
            running += t["pnl"]
            cumulative.append(running)

        max_dd = 0
        peak = 0
        for c in cumulative:
            if c > peak:
                peak = c
            dd = peak - c
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (assuming 0.5% daily rf, annualized)
        if len(closed) >= 2:
            pnls = [t["pnl"] for t in sorted(closed, key=lambda x: x["timestamp"])]
            mean_pnl = sum(pnls) / len(pnls)
            variance = sum((p - mean_pnl) ** 2 for p in pnls) / len(pnls)
            std_pnl = math.sqrt(variance) if variance > 0 else 0
            sharpe = (mean_pnl / std_pnl * math.sqrt(252)) if std_pnl > 0 else 0
        else:
            sharpe = 0

        # Brier score
        brier = self._brier_score(closed)

        # Win/loss ratio
        avg_win = sum(t["pnl"] for t in winners) / len(winners) if winners else 0
        avg_loss = abs(sum(t["pnl"] for t in losers) / len(losers)) if losers else 0
        wl_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        return {
            "total_trades": total,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "void_trades": len(voids),
            "win_rate": round(win_rate, 4),
            "total_pnl": round(total_pnl, 4),
            "roi_percent": round(roi, 2),
            "avg_edge": round(avg_edge, 4),
            "avg_confidence": round(avg_conf, 4),
            "avg_pnl_per_trade": round(avg_pnl, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe_ratio": round(sharpe, 2),
            "brier_score": round(brier, 4),
            "win_loss_ratio": round(wl_ratio, 2),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "total_invested": round(total_invested, 2),
        }

    def _brier_score(self, trades: List[Dict]) -> float:
        """Brier score: lower is better. 0=perfect, 0.25=random."""
        if not trades:
            return 0
        total = 0
        for t in trades:
            # Predicted probability = (edge + 1) / 2 → 0 to 1
            prob = (t["signal_edge"] + 1) / 2
            # Outcome: 1 if won, 0 if lost
            outcome = 1 if t["pnl"] > 0 else 0
            total += (prob - outcome) ** 2
        return total / len(trades)

    def edge_bucket_analysis(self, trades: List[Dict]) -> Dict[str, Any]:
        """Break down performance by edge bucket."""
        buckets = {
            "5-10%": [],
            "10-15%": [],
            "15-20%": [],
            "20%+": [],
        }

        for t in trades:
            edge = abs(t["signal_edge"])
            if edge >= 0.20:
                buckets["20%+"].append(t)
            elif edge >= 0.15:
                buckets["15-20%"].append(t)
            elif edge >= 0.10:
                buckets["10-15%"].append(t)
            elif edge >= 0.05:
                buckets["5-10%"].append(t)

        result = {}
        for bucket, bucket_trades in buckets.items():
            if not bucket_trades:
                result[bucket] = {"count": 0, "win_rate": 0, "avg_pnl": 0, "pnl": 0}
            else:
                winners = sum(1 for t in bucket_trades if t["pnl"] > 0)
                pnl = sum(t["pnl"] for t in bucket_trades)
                result[bucket] = {
                    "count": len(bucket_trades),
                    "win_rate": round(winners / len(bucket_trades), 3),
                    "avg_pnl": round(pnl / len(bucket_trades), 3),
                    "pnl": round(pnl, 3),
                }
        return result

    def confidence_bucket_analysis(self, trades: List[Dict]) -> Dict[str, Any]:
        """Break down performance by confidence bucket."""
        buckets = {
            "50-60%": [],
            "60-70%": [],
            "70-80%": [],
            "80%+": [],
        }

        for t in trades:
            conf = t["signal_confidence"]
            if conf >= 0.80:
                buckets["80%+"].append(t)
            elif conf >= 0.70:
                buckets["70-80%"].append(t)
            elif conf >= 0.60:
                buckets["60-70%"].append(t)
            elif conf >= 0.50:
                buckets["50-60%"].append(t)

        result = {}
        for bucket, bucket_trades in buckets.items():
            if not bucket_trades:
                result[bucket] = {"count": 0, "win_rate": 0, "avg_pnl": 0, "pnl": 0}
            else:
                winners = sum(1 for t in bucket_trades if t["pnl"] > 0)
                pnl = sum(t["pnl"] for t in bucket_trades)
                result[bucket] = {
                    "count": len(bucket_trades),
                    "win_rate": round(winners / len(bucket_trades), 3),
                    "avg_pnl": round(pnl / len(bucket_trades), 3),
                    "pnl": round(pnl, 3),
                }
        return result

    def print_report(self, metrics: Dict) -> str:
        """Format metrics as readable string."""
        if "error" in metrics:
            return f"⚠️ {metrics['error']}"

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 BACKTEST PERFORMANCE REPORT",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  Total Trades:     {metrics['total_trades']}",
            f"  Win Rate:         {metrics['win_rate']:.1%}",
            f"  Winners:          {metrics['winning_trades']} | Losers: {metrics['losing_trades']} | Voids: {metrics.get('void_trades', 0)}",
            f"  Total P&L:        ${metrics['total_pnl']:+.2f}",
            f"  ROI:              {metrics['roi_percent']:+.2f}%",
            f"  Total Invested:   ${metrics['total_invested']:.2f}",
            f"  Avg P&L/Trade:    ${metrics['avg_pnl_per_trade']:+.4f}",
            f"  Avg Edge:         {metrics['avg_edge']:+.2%}",
            f"  Avg Confidence:   {metrics['avg_confidence']:.0%}",
            f"  Win/Loss Ratio:  {metrics['win_loss_ratio']:.2f}",
            f"  Avg Win:         ${metrics['avg_win']:+.4f} | Avg Loss: ${metrics['avg_loss']:+.4f}",
            f"  Max Drawdown:    ${metrics['max_drawdown']:+.2f}",
            f"  Sharpe Ratio:    {metrics['sharpe_ratio']:.2f}",
            f"  Brier Score:     {metrics['brier_score']:.4f} (lower=better, 0=perfect)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        return "\n".join(lines)


def run_backtest_report(output_dir: str = "output"):
    """CLI-style backtest report generator."""
    analyzer = BacktestAnalyzer(output_dir)
    trades = analyzer.load_trades(status="closed")
    metrics = analyzer.compute_metrics(trades)
    print(analyzer.print_report(metrics))

    if "error" not in metrics and trades:
        print("\n📐 Edge Bucket Analysis:")
        for bucket, data in analyzer.edge_bucket_analysis(trades).items():
            print(f"  {bucket}: {data['count']} trades | {data['win_rate']:.1%} win rate | ${data['pnl']:+.3f} total")

        print("\n🎯 Confidence Bucket Analysis:")
        for bucket, data in analyzer.confidence_bucket_analysis(trades).items():
            print(f"  {bucket}: {data['count']} trades | {data['win_rate']:.1%} win rate | ${data['pnl']:+.3f} total")
