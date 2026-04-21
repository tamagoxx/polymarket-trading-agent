"""
Scheduler for Automated Market Scans
Run scans automatically pada interval yang ditentukan
"""
import asyncio
import signal
from datetime import datetime
from typing import Optional, Callable, Awaitable
from loguru import logger


class MarketScheduler:
    """
    Scheduler untuk automated market scans.
    
    Features:
    - Interval-based scheduling
    - Hourly scans
    - Graceful shutdown
    - Error handling
    """
    
    def __init__(
        self,
        scan_interval: int = 3600,  # Default: 1 hour in seconds
        on_scan: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        """
        Args:
            scan_interval: Interval antar scan (dalam detik)
            on_scan: Async callback function yang dipanggil saat scan
        """
        self.scan_interval = scan_interval
        self.on_scan = on_scan
        
        self.running = False
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, self.stop)
            loop.add_signal_handler(signal.SIGTERM, self.stop)
        except (ValueError, NotImplementedError):
            # Windows doesn't support add_signal_handler
            pass
    
    def start(self):
        """Start the scheduler."""
        logger.info(f"Starting scheduler with {self.scan_interval}s interval")
        self.running = True
        
        try:
            asyncio.run(self._run_loop())
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
        finally:
            self.stop()
    
    async def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                # Calculate next run time
                from datetime import timedelta
                
                if self.last_run:
                    self.next_run = self.last_run + timedelta(seconds=self.scan_interval)
                else:
                    self.next_run = datetime.now()
                
                # Wait for next interval
                await self._wait_for_next_run()
                
                if not self.running:
                    break
                
                # Run scan
                await self._execute_scan()
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self.error_count += 1
                self.running = False
    
    async def _wait_for_next_run(self):
        """Wait until next scheduled run."""
        if not self.last_run:
            return
        
        from datetime import timedelta
        
        wait_seconds = self.scan_interval
        
        if self.next_run:
            remaining = (self.next_run - datetime.now()).total_seconds()
            wait_seconds = max(0, remaining)
        
        if wait_seconds > 0:
            logger.info(f"Next scan in {int(wait_seconds)} seconds...")
            
            # Wait in chunks to allow responsive shutdown
            chunk_size = 10
            while wait_seconds > 0 and self.running:
                await asyncio.sleep(min(wait_seconds, chunk_size))
                wait_seconds -= chunk_size
    
    async def _execute_scan(self):
        """Execute scan callback."""
        logger.info("=" * 50)
        logger.info(f"Starting scheduled scan #{self.run_count + 1}")
        logger.info("=" * 50)
        
        try:
            if self.on_scan:
                await self.on_scan()
            else:
                logger.warning("No scan callback configured")
            
            self.last_run = datetime.now()
            self.run_count += 1
            
            logger.info(f"Scan #{self.run_count} completed successfully")
            
        except Exception as e:
            logger.error(f"Scan execution error: {e}")
            self.error_count += 1
            self.last_run = datetime.now()
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler...")
        self.running = False
    
    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "scan_interval": self.scan_interval,
        }


def create_hourly_scheduler(scan_callback: Callable[[], Awaitable[None]]):
    """
    Create hourly scheduler dengan callback.
    
    Usage:
        async def my_scan():
            bot = TradingBot()
            await bot.run_market_scan()
            await bot.close()
        
        scheduler = create_hourly_scheduler(my_scan)
        scheduler.start()
    """
    return MarketScheduler(
        scan_interval=3600,  # 1 hour
        on_scan=scan_callback,
    )


def create_custom_scheduler(
    scan_callback: Callable[[], Awaitable[None]],
    interval_seconds: int,
):
    """Create custom interval scheduler."""
    return MarketScheduler(
        scan_interval=interval_seconds,
        on_scan=scan_callback,
    )
