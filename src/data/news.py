"""
News Fetcher - News scraping dan RSS feeds
"""
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from ..config import settings


class NewsFetcher:
    """
    Fetcher untuk news dan informasi external.
    
    Sources:
    - News API (configurable)
    - RSS feeds
    - Web scraping
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # RSS Feed URLs (polymarket related)
        self.rss_feeds = [
            "https://news.google.com/rss/search?q=polymarket&hl=en-US&gl=US&ceid=US:en",
            "https://predictwise.com/feed",
        ]
    
    async def close(self):
        await self.client.aclose()
    
    async def search_news(
        self,
        query: str,
        days: int = 7,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search news berdasarkan query.
        
        Args:
            query: Search query
            days: Days back to search
            limit: Max results
            
        Returns:
            List of news articles
        """
        if not settings.news_api_key:
            logger.warning("News API key not configured")
            return await self._search_google_rss(query, limit)
        
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            response = await self.client.get(
                f"{settings.news_api_url}/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "pageSize": limit,
                    "apiKey": settings.news_api_key,
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_at": article.get("publishedAt", ""),
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"News API error: {e}")
            return []
    
    async def _search_google_rss(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fallback search via Google RSS.
        """
        try:
            import feedparser
            
            url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
            
            feed = feedparser.parse(url)
            
            articles = []
            for entry in feed.entries[:limit]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("description", "")[:500],
                    "url": entry.get("link", ""),
                    "source": entry.get("source", {}).get("title", "Google News"),
                    "published_at": entry.get("published", ""),
                })
            
            return articles
            
        except ImportError:
            logger.warning("feedparser not installed, skipping RSS search")
            return []
        except Exception as e:
            logger.error(f"RSS fetch error: {e}")
            return []
    
    async def get_polymarket_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get Polymarket-specific news.
        """
        return await self.search_news("Polymarket prediction market", days=7, limit=limit)
    
    async def get_market_related_news(
        self,
        market_question: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get news related to specific market question.
        """
        # Extract keywords from question
        keywords = self._extract_keywords(market_question)
        
        if not keywords:
            return []
        
        query = " ".join(keywords[:3])
        return await self.search_news(query, days=14, limit=limit)
    
    async def get_batch_news(
        self,
        market_questions: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get news for multiple market questions.
        """
        async def fetch_for_market(question: str) -> tuple:
            news = await self.get_market_related_news(question, limit=5)
            return (question, news)
        
        tasks = [fetch_for_market(q) for q in market_questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        news_dict = {}
        for question, news in results:
            if not isinstance((question, news), tuple):
                if not isinstance(question, Exception) and not isinstance(news, Exception):
                    news_dict[question] = news
        
        return news_dict
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords dari text untuk search.
        """
        # Common stopwords
        stopwords = {
            "will", "would", "could", "should", "may", "might", "must",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "that", "this", "these", "those", "it", "its", "what", "which",
            "who", "whom", "whose", "where", "when", "why", "how",
            "yes", "no", "not", "do", "does", "did", "have", "has", "had",
        }
        
        # Simple tokenization
        words = text.lower().split()
        
        # Filter and get meaningful words
        keywords = [
            w.strip(".,!?;:()[]{}")
            for w in words
            if len(w) > 3 and w not in stopwords
        ]
        
        return keywords[:10]
    
    async def get_trending_topics(self) -> List[str]:
        """
        Get trending topics yang mungkin affect markets.
        """
        try:
            # Get Polymarket news
            news = await self.get_polymarket_news(limit=50)
            
            # Extract topics
            topics = []
            for article in news:
                keywords = self._extract_keywords(article.get("title", ""))
                topics.extend(keywords)
            
            # Count frequency
            from collections import Counter
            counter = Counter(topics)
            
            # Return top topics
            return [topic for topic, _ in counter.most_common(20)]
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []


# Singleton
news_fetcher = NewsFetcher()
