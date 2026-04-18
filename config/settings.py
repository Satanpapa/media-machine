"""
Configuration management for the Media Machine system.
Loads environment variables and provides typed access to settings.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """Central configuration manager for the entire system."""
    
    def __init__(self, env_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env_path: Path to .env file. If None, uses default location.
        """
        if env_path is None:
            # Try multiple locations
            possible_paths = [
                Path(__file__).parent / ".env",
                Path.cwd() / ".env",
                Path.home() / ".media_machine" / ".env",
            ]
            for p in possible_paths:
                if p.exists():
                    env_path = str(p)
                    break
        
        if env_path and Path(env_path).exists():
            load_dotenv(env_path)
        else:
            # Try loading from current directory anyway
            load_dotenv()
        
        # LLM Configuration
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        
        # Telegram Configuration
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "")
        self.telegram_api_id: str = os.getenv("TELEGRAM_API_ID", "")
        self.telegram_api_hash: str = os.getenv("TELEGRAM_API_HASH", "")
        
        # Trend Sources
        self.reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.google_trends_enabled: bool = os.getenv("GOOGLE_TRENDS_ENABLED", "false").lower() == "true"
        
        # Competitor Analysis
        self.competitor_channels: List[str] = self._parse_comma_list(
            os.getenv("COMPETITOR_CHANNELS", "")
        )
        
        # RSS Feeds
        self.rss_feeds: List[str] = self._parse_comma_list(
            os.getenv("RSS_FEEDS", "https://feeds.bbci.co.uk/news/rss.xml")
        )
        
        # Database
        self.database_path: str = os.getenv(
            "DATABASE_PATH", "./data/media_machine.db"
        )
        
        # Scheduling (in minutes)
        self.trend_check_interval: int = int(os.getenv("TREND_CHECK_INTERVAL", "20"))
        self.analyst_interval: int = int(os.getenv("ANALYST_INTERVAL", "360"))
        
        # Monetization
        self.partner_links: dict = {
            "ai": os.getenv("PARTNER_LINKS_AI", ""),
            "crypto": os.getenv("PARTNER_LINKS_CRYPTO", ""),
            "tools": os.getenv("PARTNER_LINKS_TOOLS", ""),
        }
        self.monetization_ratio: int = int(os.getenv("MONETIZATION_RATIO", "5"))
        
        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_file: str = os.getenv("LOG_FILE", "./logs/media_machine.log")
        
        # Validate required settings
        self._validate()
    
    def _parse_comma_list(self, value: str) -> List[str]:
        """Parse comma-separated string into list."""
        if not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    
    def _validate(self):
        """Validate critical configuration values."""
        warnings = []
        
        if not self.telegram_bot_token or self.telegram_bot_token == "your_bot_token_here":
            warnings.append("TELEGRAM_BOT_TOKEN not configured")
        
        if not self.openai_api_key and self.llm_provider == "openai":
            warnings.append("OPENAI_API_KEY not configured but OpenAI selected as provider")
        
        if not self.groq_api_key and self.llm_provider == "groq":
            warnings.append("GROQ_API_KEY not configured but Groq selected as provider")
        
        if not self.anthropic_api_key and self.llm_provider == "anthropic":
            warnings.append("ANTHROPIC_API_KEY not configured but Anthropic selected as provider")
        
        if warnings:
            print("⚠️  Configuration Warnings:")
            for w in warnings:
                print(f"   - {w}")
            print("   Some features may not work correctly.\n")
    
    @property
    def is_llm_configured(self) -> bool:
        """Check if any LLM provider is properly configured."""
        if self.llm_provider == "openai" and self.openai_api_key:
            return True
        if self.llm_provider == "groq" and self.groq_api_key:
            return True
        if self.llm_provider == "anthropic" and self.anthropic_api_key:
            return True
        return False
    
    @property
    def is_telegram_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.telegram_bot_token and self.telegram_channel_id)
    
    def get_partner_link(self, topic: str) -> Optional[str]:
        """Get partner link for a given topic category."""
        topic_lower = topic.lower()
        if "ai" in topic_lower or "ml" in topic_lower or "llm" in topic_lower:
            return self.partner_links.get("ai")
        if "crypto" in topic_lower or "blockchain" in topic_lower or "bitcoin" in topic_lower:
            return self.partner_links.get("crypto")
        if "tool" in topic_lower or "software" in topic_lower or "app" in topic_lower:
            return self.partner_links.get("tools")
        return None


# Global config instance
config = Config()
