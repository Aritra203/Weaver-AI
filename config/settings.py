"""
Configuration management for Weaver AI
Handles environment variables and application settings
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # API Keys
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # GitHub Settings
    GITHUB_REPO: Optional[str] = os.getenv("GITHUB_REPO")
    
    # Slack Settings
    SLACK_CHANNELS: List[str] = [
        channel.strip() for channel in os.getenv("SLACK_CHANNELS", "").split(",")
        if channel.strip()
    ]
    
    # Vector Database Settings
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Data Paths
    RAW_DATA_PATH: str = "./data/raw"
    PROCESSED_DATA_PATH: str = "./data/processed"
    
    # OpenAI Settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHAT_MODEL: str = "gpt-4"
    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.1
    
    def validate_api_keys(self) -> List[str]:
        """Validate that required API keys are present"""
        missing_keys = []
        
        if not self.GITHUB_TOKEN:
            missing_keys.append("GITHUB_TOKEN")
        if not self.SLACK_BOT_TOKEN:
            missing_keys.append("SLACK_BOT_TOKEN") 
        if not self.OPENAI_API_KEY:
            missing_keys.append("OPENAI_API_KEY")
            
        return missing_keys
    
    def __str__(self) -> str:
        """String representation (without sensitive data)"""
        return f"""
Weaver AI Configuration:
- GitHub Repo: {self.GITHUB_REPO or 'Not configured'}
- Slack Channels: {len(self.SLACK_CHANNELS)} configured
- Vector DB Path: {self.VECTOR_DB_PATH}
- Chunk Size: {self.CHUNK_SIZE}
- API Host: {self.API_HOST}:{self.API_PORT}
        """.strip()

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings
