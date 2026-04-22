"""
Main Entry Point - Polymarket Trading Agent
Data Fetching & Signal Generation with Dashboard & CSV Export
"""
import asyncio
from datetime import datetime
from pathlib import Path
from loguru import logger

# Local imports
from src.config import settings
from src.data.fetcher import PolymarketFetcher
from src.data.news import NewsFetcher
from src.data.signal_analyzer import SignalAnalyzer
from src.agent.llm import MiniMaxAgent
from src.utils.logger import setup_logger
from src.utils.csv_export import CSVExporter
from src.utils.dashboard import DashboardGenerator
from src.utils.scheduler import create_hourly_scheduler


class TradingBot:
    """
    Main trading bot class.
    
    Responsibilities:
    1. Fetch market data
    2. Fetch related news
    3. Generate signals via LLM
    4. Export to CSV
    5. Generate dashboard
    """
    
    def __init__(self):
        self.fetcher = PolymarketFetcher()
        self.news_fetcher = NewsFetcher()
        self.llm = MiniMaxAgent()
        self.analyzer = SignalAnalyzer(self.llm)
        self.csv_exporter = CSVExporter()
        self.dashboard_generator = DashboardGenerator()
        
        # State
        self.last_run = None
        self.signal_history = []
    
    async def close(self):
        """Cleanup resources."""
        await self.fetcher.close()
        await self.news_fetcher.close()
    
    async def run_market_scan(self, dry_run: bool = False) -> dict:
        """
        Jalankan full market scan dan generate signals.
        
        Args:
            dry_run: If True, skip all file writes (CSV, JSON, dashboard)
        """
        logger.info("Starting market scan...")
        
        try:
            # 1. Fetch high-quality markets
            logger.info("Fetching markets...")
            markets = await self.fetcher.get_high_liquidity_markets(
                min_liquidity=5000,
                limit=100,
            )
            
            if not markets:
                logger.warning("No markets found")
                return {"status": "error", "message": "No markets found"}
            
            # Convert to dict
            market_dicts = [m.to_signal_dict() for m in markets]
            
            # Export markets to CSV (skip if dry run)
            if not dry_run:
                logger.info("Exporting market data to CSV...")
                for m in market_dicts:
                    self.csv_exporter.export_market(m)
            else:
                logger.info("[DRY RUN] Skipping CSV export for market data...")
            
            # Fetch news for market questions
            logger.info("Fetching related news...")
            questions = [m.question for m in markets]
            news_map = await self.news_fetcher.get_batch_news(questions)
            
            # 3. Generate signals
            logger.info("Generating signals via LLM...")
            result = await self.analyzer.generate_daily_signals(
                markets_data=market_dicts,
                top_n=10,
            )
            
            # 4. Export signals to CSV (skip if dry run)
            if not dry_run:
                logger.info("Exporting signals to CSV...")
                all_signals = result.get("all_signals", [])
                self.csv_exporter.export_signals_batch(all_signals)
            else:
                logger.info("[DRY RUN] Skipping CSV export for signals...")
            
            # 5. Generate Dashboard (skip if dry run)
            if not dry_run:
                logger.info("Generating HTML dashboard...")
                top_signals = result.get("top_signals", [])
                self.dashboard_generator.generate_dashboard(top_signals)
            else:
                logger.info("[DRY RUN] Skipping dashboard generation...")
            
            # Update state
            self.last_run = datetime.now()
            self.signal_history.append(result)
            
            # Keep only last 100 runs
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]
            
            logger.info(f"Scan complete. Found {result['actionable_count']} actionable signals.")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in market scan: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_single_market_analysis(self, question: str) -> dict:
        """
        Analisis satu market tertentu.
        """
        logger.info(f"Analyzing market: {question}")
        
        try:
            # 1. Get market data
            market = await self.fetcher.get_market_by_question(question)
            
            if not market:
                return {"status": "error", "message": f"Market not found: {question}"}
            
            # 2. Get news
            news = await self.news_fetcher.get_market_related_news(question, limit=10)
            
            # 3. Generate signal
            signal = await self.analyzer.analyze_market(
                market.to_signal_dict(),
                news,
            )
            
            return {
                "status": "success",
                "market": market.to_signal_dict(),
                "news": news,
                "signal": signal,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_recent_signals(self, limit: int = 10) -> list:
        """Get recent signals."""
        recent = []
        for run in reversed(self.signal_history[-limit:]):
            recent.extend(run.get("top_signals", []))
        return recent[:limit]
    
    def get_performance_metrics(self) -> dict:
        """Get performance metrics for backtesting."""
        return self.csv_exporter.calculate_performance_metrics()


# =====================
# SCHEDULED SCAN
# =====================

async def scheduled_scan():
    """Callback untuk scheduled scan."""
    bot = TradingBot()
    try:
        await bot.run_market_scan()
    finally:
        await bot.close()


# =====================
# MAIN ENTRY POINT
# =====================

async def main():
    """Main entry point."""
    # Setup logging
    setup_logger(
        log_level=settings.log_level,
        log_file="logs/trading_bot.log",
    )
    
    logger.info("=" * 60)
    logger.info("Polymarket Trading Agent Starting...")
    logger.info(f"LLM: {settings.minimax_model}")
    logger.info("Features: Data Fetching + Signal + CSV + Dashboard")
    logger.info("=" * 60)
    
    # Initialize bot
    bot = TradingBot()
    
    try:
        # Run once on startup
        logger.info("\n--- Running Market Scan ---\n")
        result = await bot.run_market_scan()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SIGNAL SUMMARY")
        print("=" * 60)
        
        top_signals = result.get("top_signals", [])
        
        if top_signals:
            print(f"\nFound {len(top_signals)} actionable signals:\n")
            
            for i, signal in enumerate(top_signals, 1):
                question = signal.get('question', '')[:50]
                print(f"{i}. {question}...")
                print(f"   Signal: {signal['signal_type']} | Edge: {signal['edge']:.1%} | Conf: {signal['confidence']:.0%}")
                if signal.get('reasoning'):
                    reason = signal['reasoning'][0][:70]
                    print(f"   → {reason}")
                print()
        else:
            print("\nNo actionable signals found.")
        
        print("=" * 60)
        print("📁 OUTPUT FILES")
        print("=" * 60)
        print(f"  • Dashboard: output/dashboard.html")
        print(f"  • Signals CSV: output/signals.csv")
        print(f"  • Markets CSV: output/markets.csv")
        print(f"  • Logs: logs/trading_bot.log")
        print("=" * 60)
        
        # Save JSON copy
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"signals_{timestamp}.json"
        
        import json
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        logger.info(f"JSON results saved to {output_file}")
        
    finally:
        await bot.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dry-run":
            # Run once without writing any files
            asyncio.run(dry_run_main())
        elif sys.argv[1] == "--once":
            # Run once and exit
            asyncio.run(main())
        elif sys.argv[1] == "--hourly":
            # Run scheduled scans
            logger.info("Starting in HOURLY scheduled mode...")
            scheduler = create_hourly_scheduler(scheduled_scan)
            scheduler.start()
        elif sys.argv[1] == "--serve":
            # Run with dashboard server
            logger.info("Starting with dashboard server...")
            from aiohttp import web
            from src.utils.dashboard import dashboard_generator

            async def serve_dashboard():
                async def handler(request):
                    from pathlib import Path
                    dashboard_path = Path("output/dashboard.html")
                    if dashboard_path.exists():
                        content = dashboard_path.read_text()
                    else:
                        content = "<html><body><h1>No dashboard yet. Run --once first.</h1></body></html>"
                    return web.Response(text=content, content_type='text/html')

                app = web.Application()
                app.router.add_get('/', handler)
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, 'localhost', 8080)
                await site.start()
                logger.info("Dashboard server running at http://localhost:8080")
                # Keep server running
                import asyncio
                await asyncio.Event().wait()

            asyncio.run(serve_dashboard())
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--once|--hourly|--serve]")
    else:
        # Default: run once
        print("Running single scan...")
        print("Usage: python main.py [--once|--hourly|--serve|--dry-run]")
        asyncio.run(main())
