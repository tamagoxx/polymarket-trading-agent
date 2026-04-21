"""
CSV Export for Backtesting
Export signals dan historical data ke CSV format
"""
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger


class CSVExporter:
    """
    Exporter untuk generate CSV files untuk backtesting.
    
    CSV Types:
    - signals.csv: All generated signals
    - markets.csv: Market data history
    - trades.csv: Simulated/executed trades
    - performance.csv: Daily performance metrics
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # CSV file paths
        self.signals_file = self.output_dir / "signals.csv"
        self.markets_file = self.output_dir / "markets.csv"
        self.trades_file = self.output_dir / "trades.csv"
        self.performance_file = self.output_dir / "performance.csv"
        
        # Initialize headers
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Initialize CSV files with headers if not exist."""
        
        # Signals CSV
        if not self.signals_file.exists():
            self._write_header(
                self.signals_file,
                [
                    "timestamp",
                    "market_id",
                    "question",
                    "outcomes",
                    "prices",
                    "volume",
                    "liquidity",
                    "signal_type",
                    "edge",
                    "confidence",
                    "recommended_size",
                    "reasoning",
                    "llm_analysis",
                ]
            )
        
        # Markets CSV
        if not self.markets_file.exists():
            self._write_header(
                self.markets_file,
                [
                    "fetched_at",
                    "market_id",
                    "question",
                    "outcomes",
                    "outcome_prices",
                    "volume",
                    "liquidity",
                    "active",
                    "closed",
                ]
            )
        
        # Trades CSV
        if not self.trades_file.exists():
            self._write_header(
                self.trades_file,
                [
                    "trade_id",
                    "timestamp",
                    "market_id",
                    "question",
                    "outcome",
                    "direction",
                    "size_usd",
                    "price",
                    "signal_edge",
                    "signal_confidence",
                    "status",
                    "pnl",
                    "notes",
                ]
            )
        
        # Performance CSV
        if not self.performance_file.exists():
            self._write_header(
                self.performance_file,
                [
                    "date",
                    "total_trades",
                    "winning_trades",
                    "losing_trades",
                    "win_rate",
                    "total_pnl",
                    "roi_percent",
                    "avg_edge",
                    "avg_confidence",
                    "max_drawdown",
                    "notes",
                ]
            )
    
    def _write_header(self, filepath: Path, headers: List[str]):
        """Write CSV header row."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    def export_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Export satu signal ke CSV.
        """
        try:
            row = [
                signal.get("timestamp", datetime.now().isoformat()),
                signal.get("market_id", ""),
                signal.get("question", ""),
                "|".join(signal.get("outcomes", [])),
                "|".join([str(p) for p in signal.get("prices", [])]),
                signal.get("volume", 0),
                signal.get("liquidity", 0),
                signal.get("signal_type", ""),
                signal.get("edge", 0),
                signal.get("confidence", 0),
                signal.get("recommended_size", 0),
                "|".join(signal.get("reasoning", [])),
                signal.get("llm_analysis", "")[:500],  # Truncate long analysis
            ]
            
            with open(self.signals_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting signal: {e}")
            return False
    
    def export_signals_batch(self, signals: List[Dict[str, Any]]) -> int:
        """
        Export multiple signals.
        
        Returns count of exported signals.
        """
        count = 0
        for signal in signals:
            if self.export_signal(signal):
                count += 1
        return count
    
    def export_market(self, market: Dict[str, Any]) -> bool:
        """
        Export market data snapshot.
        """
        try:
            row = [
                datetime.now().isoformat(),
                market.get("id", ""),
                market.get("question", ""),
                "|".join(market.get("outcomes", [])),
                "|".join([str(p) for p in market.get("prices", [])]),
                market.get("volume", 0),
                market.get("liquidity", 0),
                market.get("active", True),
                market.get("closed", False),
            ]
            
            with open(self.markets_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting market: {e}")
            return False
    
    def export_trade(self, trade: Dict[str, Any]) -> str:
        """
        Export trade record.
        
        Returns trade_id.
        """
        try:
            trade_id = trade.get("trade_id", f"TRADE_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            row = [
                trade_id,
                trade.get("timestamp", datetime.now().isoformat()),
                trade.get("market_id", ""),
                trade.get("question", ""),
                trade.get("outcome", ""),
                trade.get("direction", ""),
                trade.get("size_usd", 0),
                trade.get("price", 0),
                trade.get("signal_edge", 0),
                trade.get("signal_confidence", 0),
                trade.get("status", "pending"),
                trade.get("pnl", 0),
                trade.get("notes", ""),
            ]
            
            with open(self.trades_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            return trade_id
            
        except Exception as e:
            logger.error(f"Error exporting trade: {e}")
            return ""
    
    def update_trade_pnl(self, trade_id: str, pnl: float, status: str = "closed") -> bool:
        """
        Update trade P&L after market resolves.
        """
        try:
            # Read all rows
            with open(self.trades_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Update matching trade
            updated = False
            for row in rows:
                if row["trade_id"] == trade_id:
                    row["pnl"] = pnl
                    row["status"] = status
                    updated = True
                    break
            
            if updated:
                # Rewrite file
                with open(self.trades_file, "w", newline="", encoding="utf-8") as f:
                    fieldnames = rows[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            
            return updated
            
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            return False
    
    def export_performance(self, perf: Dict[str, Any]) -> bool:
        """
        Export daily performance metrics.
        """
        try:
            row = [
                perf.get("date", datetime.now().strftime("%Y-%m-%d")),
                perf.get("total_trades", 0),
                perf.get("winning_trades", 0),
                perf.get("losing_trades", 0),
                perf.get("win_rate", 0),
                perf.get("total_pnl", 0),
                perf.get("roi_percent", 0),
                perf.get("avg_edge", 0),
                perf.get("avg_confidence", 0),
                perf.get("max_drawdown", 0),
                perf.get("notes", ""),
            ]
            
            with open(self.performance_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting performance: {e}")
            return False
    
    def get_trades_for_backtest(
        self,
        min_edge: float = 0.05,
        min_confidence: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Get trades dari CSV untuk backtesting analysis.
        """
        try:
            trades = []
            
            with open(self.trades_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    edge = float(row.get("signal_edge", 0))
                    confidence = float(row.get("signal_confidence", 0))
                    
                    if abs(edge) >= min_edge and confidence >= min_confidence:
                        trades.append({
                            "trade_id": row["trade_id"],
                            "timestamp": row["timestamp"],
                            "market_id": row["market_id"],
                            "question": row["question"],
                            "outcome": row["outcome"],
                            "direction": row["direction"],
                            "size_usd": float(row["size_usd"]),
                            "price": float(row["price"]),
                            "signal_edge": edge,
                            "signal_confidence": confidence,
                            "pnl": float(row["pnl"]) if row["pnl"] else 0,
                            "status": row["status"],
                        })
            
            return trades
            
        except Exception as e:
            logger.error(f"Error reading trades: {e}")
            return []
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics dari trades.
        """
        trades = self.get_trades_for_backtest()
        closed_trades = [t for t in trades if t["status"] == "closed"]
        
        if not closed_trades:
            return {"error": "No closed trades found"}
        
        total = len(closed_trades)
        winners = [t for t in closed_trades if t["pnl"] > 0]
        losers = [t for t in closed_trades if t["pnl"] < 0]
        
        total_pnl = sum(t["pnl"] for t in closed_trades)
        total_invested = sum(t["size_usd"] for t in closed_trades)
        
        return {
            "total_trades": total,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": len(winners) / total if total > 0 else 0,
            "total_pnl": total_pnl,
            "roi_percent": (total_pnl / total_invested * 100) if total_invested > 0 else 0,
            "avg_edge": sum(t["signal_edge"] for t in closed_trades) / total,
            "avg_confidence": sum(t["signal_confidence"] for t in closed_trades) / total,
            "brier_score": self._calculate_brier_score(closed_trades),
        }
    
    def _calculate_brier_score(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate Brier score untuk calibration analysis.
        
        Brier Score = (1/N) * Σ (probability - outcome)²
        Lower is better (0 = perfect, 0.25 = random)
        """
        if not trades:
            return 0
        
        total_score = 0
        for trade in trades:
            # Probability (edge converted to 0-1 scale)
            prob = (trade["signal_edge"] + 1) / 2  # -1 to 1 → 0 to 1
            
            # Outcome (1 if won, 0 if lost)
            outcome = 1 if trade["pnl"] > 0 else 0
            
            # Squared error
            total_score += (prob - outcome) ** 2
        
        return total_score / len(trades)
    
    def export_all_signals(self, signals: List[Dict[str, Any]]) -> int:
        """
        Convenience method untuk export semua signals dari scan.
        """
        return self.export_signals_batch(signals)


# Singleton
csv_exporter = CSVExporter()
