#!/usr/bin/env python3
"""
Setup script for the columnist agent system.
"""

import os
import shutil
from pathlib import Path


def setup_environment():
    """Setup the development environment."""
    print("Setting up columnist agent environment...")
    
    # Create .env file from example
    env_example = Path("config/.env.example")
    env_file = Path("config/.env")
    
    if env_example.exists() and not env_file.exists():
        shutil.copy(env_example, env_file)
        print(f"Created {env_file} from example")
        print("Please edit config/.env with your actual API keys and settings")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    print(f"Created {logs_dir} directory")
    
    # Create examples directory if it doesn't exist
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    print(f"Ensured {examples_dir} directory exists")
    
    print("\nSetup completed!")
    print("\nNext steps:")
    print("1. Edit config/.env with your API keys")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Test with: python main.py --interactive")
    print("4. For MCP testing, run: python mcp/mock_server.py")


if __name__ == "__main__":
    setup_environment()