"""
Polymarket Data Fetcher
Mengambil data markets, harga, likuiditas dari Polymarket API
"""
import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from ..config import settings


class MarketData:
    """Struktur data market Polymarket."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.question = data.get("question", "")
        self.categorization = data.get("categorization", "")
        self.description = data.get("description", "")
        
        # Outcomes & prices
        outcomes = data.get("outcomes", [])
        prices = data.get("outcomePrices", [])
        
        self.outcomes: List[str] = outcomes if isinstance(outcomes, list) else [outcomes]
        self.prices: List[float] = [float(p) for p in prices] if prices else []
        
        # Volume & liquidity
        self.volume = float(data.get("volume", 0) or 0)
        self.liquidity = float(data.get("liquidity", 0) or 0)
        
        # Status
        self.active = data.get("active", True)
        self.closed = data.get("closed", False)
        
        # Timestamps
        self.created_at = data.get("creationDate", "")
        self.updated_at = data.get("lastUpdated", "")
        
        # Contract address
        self.condition_id = data.get("conditionId", "")
        
    def get_probability(self, outcome_index: int = 0) -> Optional[float]:
        """Dapatkan probabilitas berdasarkan outcome index."""
        if outcome_index < len(self.prices):
            return self.prices[outcome_index]
        return None
    
    def implied_probability(self, outcome: str) -> Optional[float]:
        """Dapatkan probabilitas berdasarkan nama outcome."""
        if outcome in self.outcomes:
            idx = self.outcomes.index(outcome)
            return self.get_probability(idx)
        return None
    
    def to_signal_dict(self) -> Dict[str, Any]:
        """Konversi ke dictionary untuk signal analysis."""
        return {
            "id": self.id,
            "question": self.question,
            "outcomes": self.outcomes,
            "prices": self.prices,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "active": self.active,
            "closed": self.closed,
        }


class PolymarketFetcher:
    """
    Fetcher untuk Polymarket data.
    Sources:
    - CLOB API (harga & orderbook)
    - GraphQL API (markets list)
    - Direct contract read (on-chain)
    """
    
    GAMMA_URL = "https://gamma-api.polymarket.com"
    DATA_API_URL = "https://data-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"
    GRAPHQL_URL = "https://data-api.polymarket.com/graphql"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    # =====================
    # MARKET DATA
    # =====================
    
    async def get_markets(
        self,
        limit: int = 100,
        closed: bool = False,
        actives_only: bool = True,
    ) -> List[MarketData]:
        """
        Ambil list markets dari Polymarket.
        """
        query = """
        query GetMarkets($limit: Int!, $closed: Boolean) {
            markets(
                limit: $limit
                closed: $closed
            ) {
                id
                question
                description
                outcomes
                outcomePrices
                volume
                liquidity
                conditionId
                active
                closed
                creationDate
                lastUpdated
            }
        }
        """
        
        variables = {
            "limit": limit,
            "closed": closed,
        }
        
        if actives_only:
            variables["closed"] = False
        
        try:
            response = await self.client.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            data = response.json()
            
            markets = data.get("data", {}).get("markets", [])
            return [MarketData(m) for m in markets]
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    async def get_market_by_question(self, question: str) -> Optional[MarketData]:
        """Cari market berdasarkan question text."""
        query = """
        query GetMarket($question: String!) {
            markets(question: $question) {
                id
                question
                description
                outcomes
                outcomePrices
                volume
                liquidity
                conditionId
                active
                closed
            }
        }
        """
        
        try:
            response = await self.client.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": {"question": question}}
            )
            response.raise_for_status()
            data = response.json()
            
            markets = data.get("data", {}).get("markets", [])
            if markets:
                return MarketData(markets[0])
            return None
            
        except Exception as e:
            logger.error(f"Error fetching market: {e}")
            return None
    
    # =====================
    # ORDERBOOK & PRICE
    # =====================
    
    async def get_orderbook(self, condition_id: str) -> Dict[str, Any]:
        """
        Ambil orderbook untuk market tertentu.
        """
        try:
            url = f"{self.CLOB_URL}/orderbook/{condition_id}"
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {}
    
    async def get_price(self, condition_id: str) -> Dict[str, float]:
        """
        Ambil harga terbaik (best bid/ask) untuk market.
        """
        orderbook = await self.get_orderbook(condition_id)
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        best_bid = float(bids[0]["price"]) if bids else None
        best_ask = float(asks[0]["price"]) if asks else None
        
        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": (best_bid + best_ask) / 2 if best_bid and best_ask else None,
            "spread": best_ask - best_bid if best_bid and best_ask else None,
        }
    
    # =====================
    # TRENDING & FILTERING
    # =====================
    
    async def get_trending_markets(self, limit: int = 20) -> List[MarketData]:
        """Ambil markets dengan volume tertinggi."""
        markets = await self.get_markets(limit=limit * 2, closed=False)
        
        # Sort by volume, take top N
        active_markets = [m for m in markets if m.active and not m.closed]
        sorted_markets = sorted(active_markets, key=lambda x: x.volume, reverse=True)
        
        return sorted_markets[:limit]
    
    async def get_high_liquidity_markets(
        self, 
        min_liquidity: float = 1000,
        limit: int = 50,
    ) -> List[MarketData]:
        """Ambil markets dengan likuiditas tinggi."""
        markets = await self.get_markets(limit=limit * 2, closed=False)
        
        filtered = [
            m for m in markets 
            if m.active and not m.closed and m.liquidity >= min_liquidity
        ]
        
        return filtered[:limit]
    
    async def get_recent_markets(self, days: int = 7, limit: int = 50) -> List[MarketData]:
        """Ambil markets terbaru."""
        markets = await self.get_markets(limit=limit, closed=False)
        
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = []
        for m in markets:
            if m.created_at:
                try:
                    created = datetime.fromisoformat(m.created_at.replace("Z", "+00:00"))
                    if created > cutoff:
                        recent.append(m)
                except:
                    continue
        
        return recent
    
    # =====================
    # BATCH FETCHING
    # =====================
    
    async def fetch_market_data_batch(
        self, 
        market_ids: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch data untuk multiple markets sekaligus.
        """
        async def fetch_single(market_id: str) -> tuple:
            market = await self.get_market_by_question(market_id)
            return (market_id, market.to_signal_dict() if market else None)
        
        tasks = [fetch_single(mid) for mid in market_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            mid: data for mid, data in results 
            if not isinstance(data, Exception)
        }
    
    # =====================
    # SCREENER
    # =====================
    
    async def screen_markets(
        self,
        min_volume: float = 10000,
        min_liquidity: float = 5000,
        min_price: float = 0.05,
        max_price: float = 0.95,
        keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Screen markets berdasarkan criteria.
        """
        markets = await self.get_high_liquidity_markets(
            min_liquidity=min_liquidity,
            limit=200,
        )
        
        screened = []
        
        for m in markets:
            # Filter by volume
            if m.volume < min_volume:
                continue
            
            # Filter by price range
            if not m.prices:
                continue
            
            # Check all outcomes
            valid_price = False
            for price in m.prices:
                if min_price <= price <= max_price:
                    valid_price = True
                    break
            
            if not valid_price:
                continue
            
            # Filter by keywords
            if keywords:
                question_lower = m.question.lower()
                if not any(kw.lower() in question_lower for kw in keywords):
                    continue
            
            screened.append(m.to_signal_dict())
        
        return screened


# NOTE: Do NOT create module-level singletons.
# Instantiate via TradingBot or pass as dependency to allow proper cleanup.
# Usage: fetcher = PolymarketFetcher()
