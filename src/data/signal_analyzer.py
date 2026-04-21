"""
Signal Analyzer
Analisis market data untuk generate trading signals
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from ..config import settings


class Signal:
    """
    Struktur signal trading.
    """
    
    def __init__(self, market_data: Dict[str, Any]):
        self.market_id = market_data.get("id", "")
        self.question = market_data.get("question", "")
        self.outcomes = market_data.get("outcomes", [])
        self.prices = market_data.get("prices", [])
        self.volume = market_data.get("volume", 0)
        self.liquidity = market_data.get("liquidity", 0)
        
        # Calculated signals
        self.edge: Optional[float] = None
        self.signal_type: Optional[str] = None  # BUY, SELL, NEUTRAL
        self.confidence: float = 0.0
        self.reasoning: List[str] = []
        self.recommended_size: float = 0.0
        self.llm_analysis: Optional[str] = None
        
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_id": self.market_id,
            "question": self.question,
            "outcomes": self.outcomes,
            "prices": self.prices,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "edge": self.edge,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_size": self.recommended_size,
            "llm_analysis": self.llm_analysis,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def is_actionable(self) -> bool:
        """Check apakah signal bisa di-action."""
        if not self.edge or not self.signal_type:
            return False
        if self.signal_type == "NEUTRAL":
            return False
        if abs(self.edge) < settings.min_edge_threshold:
            return False
        return True


class SignalAnalyzer:
    """
    Analyzer untuk generate trading signals.
    
    Flow:
    1. Fetch market data
    2. Calculate technical signals (volume, volatility, etc.)
    3. LLM analysis untuk edge detection
    4. Generate actionable signals
    """
    
    def __init__(self, llm_agent):
        self.llm = llm_agent
    
    def _calculate_technical_signals(
        self,
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Hitung technical indicators tanpa LLM.
        """
        prices = market_data.get("prices", [])
        volume = market_data.get("volume", 0)
        liquidity = market_data.get("liquidity", 0)
        
        signals = {
            "volume_score": 0,
            "liquidity_score": 0,
            "price_stability": 0,
            "market_quality": 0,
        }
        
        # Volume scoring (0-100)
        if volume >= 100000:
            signals["volume_score"] = 100
        elif volume >= 50000:
            signals["volume_score"] = 80
        elif volume >= 10000:
            signals["volume_score"] = 60
        elif volume >= 5000:
            signals["volume_score"] = 40
        else:
            signals["volume_score"] = 20
        
        # Liquidity scoring
        if liquidity >= 50000:
            signals["liquidity_score"] = 100
        elif liquidity >= 20000:
            signals["liquidity_score"] = 80
        elif liquidity >= 5000:
            signals["liquidity_score"] = 60
        else:
            signals["liquidity_score"] = 40
        
        # Price stability (jika ada multiple prices)
        if len(prices) >= 2:
            # Likuiditas total sebagai proxy
            signals["market_quality"] = min(
                signals["liquidity_score"],
                signals["volume_score"],
            )
        
        return signals
    
    async def analyze_market(
        self,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict]] = None,
    ) -> Signal:
        """
        Analisis lengkap satu market.
        """
        signal = Signal(market_data)
        
        # 1. Technical analysis
        tech_signals = self._calculate_technical_signals(market_data)
        
        # 2. LLM Analysis
        llm_analysis = await self.llm.analyze_market(
            question=market_data.get("question", ""),
            outcomes=market_data.get("outcomes", []),
            prices=market_data.get("prices", []),
            volume=market_data.get("volume", 0),
            liquidity=market_data.get("liquidity", 0),
            news=news_data or [],
        )
        
        if llm_analysis:
            signal.edge = llm_analysis.get("edge")
            signal.signal_type = llm_analysis.get("signal_type")
            signal.confidence = llm_analysis.get("confidence", 0)
            signal.reasoning = llm_analysis.get("reasoning", [])
            signal.llm_analysis = llm_analysis.get("analysis")
            signal.recommended_size = self._calculate_position_size(
                signal.edge,
                signal.confidence,
                tech_signals["market_quality"],
            )
        
        return signal
    
    async def analyze_markets_batch(
        self,
        markets_data: List[Dict[str, Any]],
        news_data: Optional[Dict[str, List[Dict]]] = None,
    ) -> List[Signal]:
        """
        Analisis multiple markets sekaligus.
        """
        async def analyze_single(market: Dict):
            market_news = news_data.get(market.get("id", "")) if news_data else None
            return await self.analyze_market(market, market_news)
        
        signals = await asyncio.gather(
            *[analyze_single(m) for m in markets_data],
            return_exceptions=True,
        )
        
        return [s for s in signals if not isinstance(s, Exception)]
    
    def filter_actionable_signals(
        self,
        signals: List[Signal],
    ) -> List[Signal]:
        """
        Filter signals yang actionable.
        """
        actionable = []
        
        for signal in signals:
            if signal.is_actionable():
                actionable.append(signal)
        
        # Sort by edge strength
        actionable.sort(key=lambda x: abs(x.edge or 0), reverse=True)
        
        return actionable
    
    def _calculate_position_size(
        self,
        edge: Optional[float],
        confidence: float,
        market_quality: float,
    ) -> float:
        """
        Hitung position size berdasarkan Kelly Criterion simplifikasi.
        """
        if not edge or edge <= 0:
            return 0
        
        # Kelly fraction (simplified)
        kelly_fraction = min(edge * confidence, 0.2)  # Max 20% of capital
        
        # Adjust by market quality
        quality_multiplier = market_quality / 100
        
        # Base position
        base_size = settings.default_bet_amount
        
        # Calculate final size
        size = base_size * kelly_fraction * quality_multiplier
        
        # Cap at max position
        size = min(size, settings.max_position_size)
        
        return round(size, 2)
    
    async def generate_daily_signals(
        self,
        markets_data: List[Dict[str, Any]],
        top_n: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate daily trading report.
        """
        logger.info(f"Generating signals for {len(markets_data)} markets...")
        
        # Analyze all markets
        signals = await self.analyze_markets_batch(markets_data)
        
        # Filter actionable
        actionable = self.filter_actionable_signals(signals)
        
        # Take top N
        top_signals = actionable[:top_n]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_markets_analyzed": len(markets_data),
            "actionable_count": len(actionable),
            "top_signals": [s.to_dict() for s in top_signals],
            "all_signals": [s.to_dict() for s in signals],
        }
