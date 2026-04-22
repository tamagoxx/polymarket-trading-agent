# Polymarket Trading Agent

from .config import settings
from .data.fetcher import PolymarketFetcher
from .data.signal_analyzer import SignalAnalyzer
from .agent.llm import MiniMaxAgent
from .utils.logger import setup_logger

__version__ = "0.2.0"

__all__ = [
    "settings",
    "PolymarketFetcher",
    "SignalAnalyzer",
    "MiniMaxAgent",
    "setup_logger",
]
