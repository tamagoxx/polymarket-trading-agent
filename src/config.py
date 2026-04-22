"""
Configuration Settings
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MiniMax API
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "abab6.5s-chat"
    
    # Polymarket API
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    data_api_url: str = "https://data-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"
    polymarket_api_key: str = ""
    
    # Polygon RPC
    polygon_rpc_url: str = "https://polygon-rpc.com"
    polygon_ws_url: str = "wss://polygon-rpc.com/ws"
    
    # News APIs
    news_api_key: str = ""
    news_api_url: str = "https://newsapi.org/v2"
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Trading Config
    max_position_size: float = 100.0
    default_bet_amount: float = 10.0
    min_edge_threshold: float = 0.05
    max_daily_loss: float = 50.0
    max_daily_trades: int = 5

    # Scheduler
    scan_interval_minutes: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
