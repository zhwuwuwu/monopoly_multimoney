"""
Configuration loader utility.
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
    
    def load_writer_config(self) -> Dict[str, Any]:
        """Load writer configuration from YAML file."""
        config_file = self.config_dir / "writer_config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Writer config not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_column_config(self) -> Dict[str, Any]:
        """Load column configuration from YAML file."""
        config_file = self.config_dir / "column_config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Column config not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_env_config(self) -> Dict[str, str]:
        """Load environment configuration."""
        return dict(os.environ)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value from environment or default."""
        return os.getenv(key, default)