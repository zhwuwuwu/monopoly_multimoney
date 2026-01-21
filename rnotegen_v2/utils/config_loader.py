"""
Configuration loader utility for V2.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """Handles loading configuration from various sources."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        
        # Load environment variables
        env_file = self.config_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load configurations
        self.writer_config = self._load_yaml_config("writer_config.yaml")
        self.reviewer_config = self._load_yaml_config("reviewer_config.yaml")
        self.env_config = dict(os.environ)
    
    def _load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        config_file = self.config_dir / filename
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_openai_config(self) -> Dict[str, str]:
        """Get OpenAI configuration."""
        return {
            "api_key": self.env_config.get("OPENAI_API_KEY"),
            "base_url": self.env_config.get("OPENAI_BASE_URL"),
            "model": self.env_config.get("OPENAI_MODEL", "GPT-4o"),
            "temperature": float(self.env_config.get("OPENAI_TEMPERATURE", 0.7))
        }
    
    def get_mcp_config(self) -> Dict[str, str]:
        """Get MCP server configuration."""
        return {
            "server_url": self.env_config.get("MCP_SERVER_URL", "http://localhost:5000"),
            "timeout": int(self.env_config.get("MCP_TIMEOUT", 30))
        }
    
    def get_rednote_config(self) -> Dict[str, str]:
        """Get RedNote platform configuration."""
        return {
            "access_token": self.env_config.get("REDNOTE_ACCESS_TOKEN"),
            "app_id": self.env_config.get("REDNOTE_APP_ID"),
            "app_secret": self.env_config.get("REDNOTE_APP_SECRET"),
            "api_base": self.env_config.get("REDNOTE_API_BASE", "https://api.xiaohongshu.com")
        }
    
    def get_content_config(self) -> Dict[str, Any]:
        """Get content generation configuration."""
        return {
            "quality_threshold": float(self.env_config.get("CONTENT_QUALITY_THRESHOLD", 7.0)),
            "max_retry_attempts": int(self.env_config.get("MAX_RETRY_ATTEMPTS", 2)),
            "enable_fact_checking": self.env_config.get("ENABLE_FACT_CHECKING", "true").lower() == "true",
            "enable_internet_research": self.env_config.get("ENABLE_INTERNET_RESEARCH", "true").lower() == "true",
            "max_research_queries": int(self.env_config.get("MAX_RESEARCH_QUERIES", 5))
        }