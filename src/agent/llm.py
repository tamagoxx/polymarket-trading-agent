"""
LLM Agent - MiniMax Integration
Using OpenAI-compatible API
"""
import json
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from loguru import logger
from ..config import settings


class MiniMaxAgent:
    """
    MiniMax 2.7 LLM Agent untuk analysis.
    
    Compatible dengan OpenAI SDK via custom base_url.
    """
    
    SYSTEM_PROMPT = """You are a prediction market analyst expert specializing in Polymarket markets.

Your task is to analyze prediction markets and determine if there is a trading edge.

For each market, you need to:
1. Understand the question and outcomes
2. Evaluate the current probabilities vs your assessment
3. Identify any market inefficiencies or mispricings
4. Assess news/events that could affect the outcome
5. Provide a clear trading signal with reasoning

Output format (JSON):
{
    "signal_type": "BUY" | "SELL" | "NEUTRAL",
    "edge": float (percentage 0-1, positive means value on YES side),
    "confidence": float (0-1),
    "reasoning": [list of key reasons],
    "analysis": "detailed paragraph explanation"
}

Rules:
- Only provide BUY/SELL if edge > 5%
- Confidence should reflect how sure you are (consider volume, liquidity, your knowledge)
- Be conservative - it's better to say NEUTRAL than to force a trade
- Consider: Is the question clear? Is there enough volume? Are outcomes well-defined?
- Think about recent news and events that could be priced in or missing
"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.minimax_api_key
        self.base_url = settings.minimax_base_url
        self.model = settings.minimax_model
        
        if not self.api_key:
            logger.warning("MiniMax API key not configured")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    async def analyze_market(
        self,
        question: str,
        outcomes: List[str],
        prices: List[float],
        volume: float,
        liquidity: float,
        news: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analisis satu market menggunakan MiniMax.
        
        Args:
            question: Pertanyaan market
            outcomes: List outcome names
            prices: List probabilitas saat ini
            volume: Volume trading
            liquidity: Likuiditas pool
            news: Optional news data
            
        Returns:
            Dict dengan signal analysis
        """
        if not self.api_key:
            logger.error("MiniMax API key required for analysis")
            return self._default_signal()
        
        # Format news section
        news_section = ""
        if news:
            news_items = []
            for n in news[:5]:  # Max 5 news
                news_items.append(f"- {n.get('title', '')}: {n.get('summary', '')[:200]}")
            news_section = "\n\nRecent News:\n" + "\n".join(news_items)
        
        # Format prompt
        prompt = f"""Analyze this Polymarket prediction market:

QUESTION: {question}

OUTCOMES: {', '.join(outcomes)}

CURRENT PROBABILITIES: {', '.join([f'{o}={p:.1%}' for o, p in zip(outcomes, prices)] if prices else ['N/A'])}

MARKET STATS:
- Volume: ${volume:,.0f}
- Liquidity: ${liquidity:,.0f}
{news_section}

Provide your analysis in JSON format."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temp for more consistent analysis
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            analysis = json.loads(content)
            return self._normalize_signal(analysis)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._default_signal()
            
        except Exception as e:
            logger.error(f"MiniMax API error: {e}")
            return self._default_signal()
    
    async def batch_analyze(
        self,
        markets: List[Dict[str, Any]],
        news: Dict[str, List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analisis multiple markets sekaligus.
        
        Args:
            markets: List of market data dicts
            news: Optional dict mapping market_id to news list
            
        Returns:
            List of analysis results
        """
        results = []
        
        for market in markets:
            market_news = news.get(market.get("id", "")) if news else None
            
            analysis = await self.analyze_market(
                question=market.get("question", ""),
                outcomes=market.get("outcomes", []),
                prices=market.get("prices", []),
                volume=market.get("volume", 0),
                liquidity=market.get("liquidity", 0),
                news=market_news,
            )
            
            results.append({
                "market_id": market.get("id", ""),
                "question": market.get("question", ""),
                **analysis,
            })
        
        return results
    
    async def generate_market_summary(
        self,
        question: str,
        outcomes: List[str],
        prices: List[float],
    ) -> str:
        """
        Generate short summary untuk satu market.
        """
        if not self.api_key:
            return f"{question} - Current: {prices[0]:.1%}" if prices else question
        
        prompt = f"""Give a brief summary of this prediction market in 2-3 sentences:

Question: {question}
Outcomes: {', '.join(outcomes)}
Probabilities: {', '.join([f'{o}={p:.1%}' for o, p in zip(outcomes, prices)] if prices else ['N/A'])}

Summary:"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a concise market analyst."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=200,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return question
    
    def _normalize_signal(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize signal format.
        """
        signal_type = analysis.get("signal_type", "NEUTRAL")
        edge = analysis.get("edge", 0)
        
        # Ensure edge is positive for BUY, negative for SELL
        if signal_type == "SELL":
            edge = -abs(edge)
        elif signal_type == "BUY":
            edge = abs(edge)
        
        return {
            "signal_type": signal_type,
            "edge": edge,
            "confidence": analysis.get("confidence", 0),
            "reasoning": analysis.get("reasoning", []),
            "analysis": analysis.get("analysis", ""),
        }
    
    def _default_signal(self) -> Dict[str, Any]:
        """
        Default signal when analysis fails.
        """
        return {
            "signal_type": "NEUTRAL",
            "edge": 0,
            "confidence": 0,
            "reasoning": ["Analysis unavailable"],
            "analysis": "Could not complete analysis.",
        }
