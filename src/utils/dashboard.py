"""
HTML Dashboard Generator
Generate simple HTML dashboard untuk visualisasi signals
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger


class DashboardGenerator:
    """
    Generator untuk HTML dashboard.
    
    Features:
    - Real-time signals display
    - Market stats summary
    - Performance metrics
    - Charts (ASCII/simple SVG)
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_file = self.output_dir / "dashboard.html"
    
    def generate_dashboard(
        self,
        signals: List[Dict[str, Any]],
        performance: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate HTML dashboard.
        
        Args:
            signals: List of trading signals
            performance: Optional performance metrics
            stats: Optional dashboard stats
            
        Returns:
            Path ke generated HTML file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Categorize signals
        buy_signals = [s for s in signals if s.get("signal_type") == "BUY"]
        sell_signals = [s for s in signals if s.get("signal_type") == "SELL"]
        neutral_signals = [s for s in signals if s.get("signal_type") == "NEUTRAL"]
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Trading Agent Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }}
        
        h1 {{
            color: #00d4ff;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            color: #888;
            font-size: 14px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #888;
            font-size: 14px;
            text-transform: uppercase;
        }}
        
        .buy-value {{ color: #00ff88; }}
        .sell-value {{ color: #ff4757; }}
        .neutral-value {{ color: #ffd93d; }}
        
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        
        .section h2 {{
            color: #00d4ff;
            margin-bottom: 20px;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 10px;
        }}
        
        .signal-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .signal-table th,
        .signal-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .signal-table th {{
            background: rgba(0,212,255,0.2);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            color: #aaa;
        }}
        
        .signal-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .signal-type {{
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
        }}
        
        .type-buy {{
            background: rgba(0,255,136,0.2);
            color: #00ff88;
        }}
        
        .type-sell {{
            background: rgba(255,71,87,0.2);
            color: #ff4757;
        }}
        
        .type-neutral {{
            background: rgba(255,217,61,0.2);
            color: #ffd93d;
        }}
        
        .edge-positive {{
            color: #00ff88;
        }}
        
        .edge-negative {{
            color: #ff4757;
        }}
        
        .btn {{
            padding: 8px 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }}
        
        .btn-primary {{
            background: #00d4ff;
            color: #1a1a2e;
        }}
        
        .btn-primary:hover {{
            background: #00b8e6;
        }}
        
        .refresh-info {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 12px;
        }}
        
        .question-text {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        
        .confidence-high {{ background: #00ff88; }}
        .confidence-medium {{ background: #ffd93d; }}
        .confidence-low {{ background: #ff4757; }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Polymarket Trading Agent</h1>
            <p class="timestamp">Last Updated: {timestamp}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(signals)}</div>
                <div class="stat-label">Total Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value buy-value">{len(buy_signals)}</div>
                <div class="stat-label">Buy Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value sell-value">{len(sell_signals)}</div>
                <div class="stat-label">Sell Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value neutral-value">{len(neutral_signals)}</div>
                <div class="stat-label">Neutral</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Actionable Signals</h2>
            {self._generate_signal_table(buy_signals + sell_signals)}
        </div>
        
        <div class="section">
            <h2>📊 Performance Summary</h2>
            {self._generate_performance_table(performance)}
        </div>
        
        <div class="section">
            <h2>📋 Recent Signals (All)</h2>
            {self._generate_full_signal_table(signals)}
        </div>
        
        <div class="refresh-info">
            <p>Auto-refresh every 5 minutes | Data source: Polymarket API</p>
            <button class="btn btn-primary" onclick="location.reload()">🔄 Refresh Now</button>
        </div>
        
        <div class="footer">
            <p>Polymarket Trading Agent v0.1 | MiniMax 2.7 powered</p>
        </div>
    </div>
    
    <script>
        // Auto refresh every 5 minutes
        setTimeout(() => location.reload(), 5 * 60 * 1000);
    </script>
</body>
</html>
"""
        
        # Write to file
        with open(self.dashboard_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        logger.info(f"Dashboard generated: {self.dashboard_file}")
        return str(self.dashboard_file)
    
    def _generate_signal_table(self, signals: List[Dict]) -> str:
        """Generate HTML table untuk actionable signals."""
        if not signals:
            return "<p style='color:#888;text-align:center;'>No actionable signals found.</p>"
        
        rows = []
        for signal in signals[:10]:  # Top 10
            signal_type = signal.get("signal_type", "NEUTRAL")
            edge = signal.get("edge", 0)
            confidence = signal.get("confidence", 0)
            
            # Confidence bar
            conf_class = "confidence-high" if confidence >= 0.7 else "confidence-medium" if confidence >= 0.5 else "confidence-low"
            conf_bar = f"""
            <div class="progress-bar">
                <div class="progress-fill {conf_class}" style="width: {confidence*100}%"></div>
            </div>
            <small>{confidence:.0%}</small>
            """
            
            rows.append(f"""
            <tr>
                <td class="question-text" title="{signal.get('question', '')}">{signal.get('question', '')[:50]}...</td>
                <td><span class="signal-type type-{signal_type.lower()}">{signal_type}</span></td>
                <td class="{'edge-positive' if edge > 0 else 'edge-negative'}">{edge:+.1%}</td>
                <td>{conf_bar}</td>
                <td>${signal.get('recommended_size', 0):.2f}</td>
            </tr>
            """)
        
        return f"""
        <table class="signal-table">
            <thead>
                <tr>
                    <th>Question</th>
                    <th>Signal</th>
                    <th>Edge</th>
                    <th>Confidence</th>
                    <th>Size</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """
    
    def _generate_full_signal_table(self, signals: List[Dict]) -> str:
        """Generate HTML table untuk all signals."""
        if not signals:
            return "<p style='color:#888;text-align:center;'>No signals available.</p>"
        
        rows = []
        for signal in signals[:20]:
            signal_type = signal.get("signal_type", "NEUTRAL")
            edge = signal.get("edge", 0)
            
            rows.append(f"""
            <tr>
                <td class="question-text" title="{signal.get('question', '')}">{signal.get('question', '')[:50]}...</td>
                <td>{signal.get('outcomes', [])}</td>
                <td>{signal.get('prices', [])}</td>
                <td><span class="signal-type type-{signal_type.lower()}">{signal_type}</span></td>
                <td class="{'edge-positive' if edge > 0 else 'edge-negative'}">{edge:+.1%}</td>
                <td>{signal.get('confidence', 0):.0%}</td>
                <td>${signal.get('volume', 0):,.0f}</td>
            </tr>
            """)
        
        return f"""
        <table class="signal-table">
            <thead>
                <tr>
                    <th>Question</th>
                    <th>Outcomes</th>
                    <th>Prices</th>
                    <th>Signal</th>
                    <th>Edge</th>
                    <th>Conf</th>
                    <th>Volume</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """
    
    def _generate_performance_table(self, performance: Optional[Dict]) -> str:
        """Generate performance metrics table."""
        if not performance:
            return "<p style='color:#888;text-align:center;'>No performance data yet. Start trading to see metrics.</p>"
        
        win_rate = performance.get("win_rate", 0)
        pnl = performance.get("total_pnl", 0)
        roi = performance.get("roi_percent", 0)
        brier = performance.get("brier_score", 0)
        
        return f"""
        <table class="signal-table">
            <tbody>
                <tr>
                    <td><strong>Total Trades</strong></td>
                    <td>{performance.get('total_trades', 0)}</td>
                    <td><strong>Win Rate</strong></td>
                    <td class="{'edge-positive' if win_rate > 0.5 else 'edge-negative'}">{win_rate:.1%}</td>
                </tr>
                <tr>
                    <td><strong>Winners</strong></td>
                    <td class="edge-positive">{performance.get('winning_trades', 0)}</td>
                    <td><strong>Losers</strong></td>
                    <td class="edge-negative">{performance.get('losing_trades', 0)}</td>
                </tr>
                <tr>
                    <td><strong>Total P&L</strong></td>
                    <td class="{'edge-positive' if pnl > 0 else 'edge-negative'}">${pnl:+.2f}</td>
                    <td><strong>ROI</strong></td>
                    <td class="{'edge-positive' if roi > 0 else 'edge-negative'}">{roi:+.2f}%</td>
                </tr>
                <tr>
                    <td><strong>Brier Score</strong></td>
                    <td>{brier:.4f}</td>
                    <td><strong>Avg Edge</strong></td>
                    <td>{performance.get('avg_edge', 0):.1%}</td>
                </tr>
            </tbody>
        </table>
        """
    
    def update_realtime(self, signals: List[Dict]) -> str:
        """
        Update dashboard dengan signals terbaru.
        Load existing data, merge, and regenerate.
        """
        return self.generate_dashboard(signals)


# Singleton
dashboard_generator = DashboardGenerator()
