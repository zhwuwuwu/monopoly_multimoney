#!/usr/bin/env python3
"""
Configuration checker for the columnist agent system.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_loader import ConfigLoader


def check_configuration():
    """Check if all required configuration is properly set."""
    print("=== Configuration Checker ===\n")
    
    config_dir = Path("config")
    success = True
    
    # Check if config directory exists
    if not config_dir.exists():
        print("❌ Config directory not found")
        return False
    
    # Check .env file
    env_file = config_dir / ".env"
    env_template = config_dir / ".env.template"
    
    if not env_file.exists():
        print("❌ .env file not found")
        if env_template.exists():
            print("💡 Copy .env.template to .env and configure your settings:")
            print(f"   cp {env_template} {env_file}")
        success = False
    else:
        print("✅ .env file found")
        
        # Load and check environment variables
        config_loader = ConfigLoader("config")
        
        # Check OpenAI configuration
        api_key = config_loader.get_config_value("OPENAI_API_KEY")
        base_url = config_loader.get_config_value("OPENAI_BASE_URL")
        
        if not api_key:
            print("❌ OPENAI_API_KEY not configured")
            success = False
        else:
            masked_key = '*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'
            print(f"✅ OPENAI_API_KEY: {masked_key}")
        
        if base_url:
            print(f"✅ OPENAI_BASE_URL: {base_url}")
        else:
            print("ℹ️  OPENAI_BASE_URL: Using default OpenAI endpoint")
    
    # Check YAML config files
    required_configs = [
        "writer_config.yaml",
        "column_config.yaml"
    ]
    
    for config_file in required_configs:
        config_path = config_dir / config_file
        if config_path.exists():
            print(f"✅ {config_file} found")
        else:
            print(f"❌ {config_file} not found")
            success = False
    
    # Check logs directory
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print("ℹ️  Creating logs directory...")
        logs_dir.mkdir(exist_ok=True)
        print("✅ Logs directory created")
    else:
        print("✅ Logs directory exists")
    
    print("\n" + "="*50)
    if success:
        print("🎉 Configuration check passed! You're ready to run the agent.")
        print("\nNext steps:")
        print("1. Run the test: python test.py")
        print("2. Run the agent: python main.py")
    else:
        print("❌ Configuration check failed. Please fix the issues above.")
        print("\nSetup guide:")
        print("1. Copy config/.env.template to config/.env")
        print("2. Edit config/.env with your API keys")
        print("3. Run this checker again: python check_config.py")
    
    return success


if __name__ == "__main__":
    check_configuration()