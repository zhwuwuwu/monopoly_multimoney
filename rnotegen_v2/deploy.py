#!/usr/bin/env python3
"""
Deployment script for Columnist Agent System v2.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


class Deployer:
    """Deployment helper for the columnist agent system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.deployment_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log deployment messages."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.deployment_log.append(log_entry)
        print(log_entry)
    
    def check_environment(self):
        """Check deployment environment."""
        self.log("Checking deployment environment...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.log(f"Python 3.8+ required, found {sys.version}", "ERROR")
            return False
        
        self.log(f"Python version: {sys.version.split()[0]}")
        
        # Check required files
        required_files = [
            "requirements.txt",
            "config/.env.example",
            "config/writer_config.yaml",
            "config/reviewer_config.yaml",
            "main.py",
            "synchronizer.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.log(f"Missing required files: {missing_files}", "ERROR")
            return False
        
        self.log("All required files present")
        return True
    
    def setup_virtual_environment(self):
        """Set up Python virtual environment."""
        self.log("Setting up virtual environment...")
        
        venv_path = self.project_root / "venv"
        
        if venv_path.exists():
            self.log("Virtual environment already exists")
            return True
        
        try:
            # Create virtual environment
            subprocess.run([
                sys.executable, "-m", "venv", str(venv_path)
            ], check=True)
            
            self.log("Virtual environment created successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to create virtual environment: {e}", "ERROR")
            return False
    
    def install_dependencies(self):
        """Install Python dependencies."""
        self.log("Installing dependencies...")
        
        venv_python = self.project_root / "venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = self.project_root / "venv" / "bin" / "python"
        
        if not venv_python.exists():
            self.log("Virtual environment Python not found", "ERROR")
            return False
        
        try:
            subprocess.run([
                str(venv_python), "-m", "pip", "install", "--upgrade", "pip"
            ], check=True)
            
            subprocess.run([
                str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"
            ], check=True)
            
            self.log("Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install dependencies: {e}", "ERROR")
            return False
    
    def setup_configuration(self):
        """Set up configuration files."""
        self.log("Setting up configuration...")
        
        env_file = self.project_root / "config" / ".env"
        env_example = self.project_root / "config" / ".env.example"
        
        if not env_file.exists() and env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            self.log("Copied .env.example to .env")
            self.log("Please edit config/.env with your API keys", "WARNING")
        
        # Create logs directory
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        self.log("Created logs directory")
        
        return True
    
    def create_service_scripts(self):
        """Create service management scripts."""
        self.log("Creating service scripts...")
        
        # Create start script
        self.create_start_script()
        
        # Create stop script
        self.create_stop_script()
        
        # Create systemd service file (Linux only)
        if sys.platform.startswith('linux'):
            self.create_systemd_service()
        
        return True
    
    def create_start_script(self):
        """Create production start script."""
        start_script = self.project_root / "start_production.sh"
        
        script_content = f"""#!/bin/bash
# Production start script for Columnist Agent System v2

set -e

PROJECT_ROOT="{self.project_root}"
VENV_PATH="$PROJECT_ROOT/venv"
LOG_FILE="$PROJECT_ROOT/logs/production.log"

echo "Starting Columnist Agent System v2..."

# Activate virtual environment
source "$VENV_PATH/bin/activate" 2>/dev/null || source "$VENV_PATH/Scripts/activate"

# Start MCP server in background
echo "Starting MCP server..."
cd "$PROJECT_ROOT"
nohup python -m mcp_server.server >> "$LOG_FILE" 2>&1 &
MCP_PID=$!
echo $MCP_PID > "$PROJECT_ROOT/mcp_server.pid"

echo "MCP server started with PID: $MCP_PID"
echo "System is ready for use"
echo "Log file: $LOG_FILE"
"""
        
        with open(start_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(start_script, 0o755)
        self.log("Created start_production.sh")
    
    def create_stop_script(self):
        """Create production stop script."""
        stop_script = self.project_root / "stop_production.sh"
        
        script_content = f"""#!/bin/bash
# Production stop script for Columnist Agent System v2

PROJECT_ROOT="{self.project_root}"
PID_FILE="$PROJECT_ROOT/mcp_server.pid"

echo "Stopping Columnist Agent System v2..."

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping MCP server (PID: $PID)..."
        kill "$PID"
        rm "$PID_FILE"
        echo "MCP server stopped"
    else
        echo "MCP server not running"
        rm -f "$PID_FILE"
    fi
else
    echo "PID file not found, attempting to find and stop process..."
    pkill -f "mcp_server.server" || echo "No MCP server process found"
fi

echo "System stopped"
"""
        
        with open(stop_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(stop_script, 0o755)
        self.log("Created stop_production.sh")
    
    def create_systemd_service(self):
        """Create systemd service file for Linux."""
        service_content = f"""[Unit]
Description=Columnist Agent System v2 MCP Server
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'columnist')}
WorkingDirectory={self.project_root}
Environment=PATH={self.project_root}/venv/bin
ExecStart={self.project_root}/venv/bin/python -m mcp_server.server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        service_file = self.project_root / "columnist-agent.service"
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(service_content)
        
        self.log("Created columnist-agent.service")
        self.log("To install service: sudo cp columnist-agent.service /etc/systemd/system/", "INFO")
        self.log("Then run: sudo systemctl enable columnist-agent && sudo systemctl start columnist-agent", "INFO")
    
    def save_deployment_log(self):
        """Save deployment log to file."""
        log_file = self.project_root / "deployment.log"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.deployment_log))
        
        self.log(f"Deployment log saved to {log_file}")
    
    def deploy(self):
        """Run full deployment."""
        self.log("Starting deployment of Columnist Agent System v2")
        
        steps = [
            ("Environment Check", self.check_environment),
            ("Virtual Environment", self.setup_virtual_environment),
            ("Dependencies", self.install_dependencies),
            ("Configuration", self.setup_configuration),
            ("Service Scripts", self.create_service_scripts),
        ]
        
        for step_name, step_func in steps:
            self.log(f"=== {step_name} ===")
            if not step_func():
                self.log(f"Deployment failed at step: {step_name}", "ERROR")
                self.save_deployment_log()
                return False
        
        self.log("=== Deployment Complete ===")
        self.log("Deployment completed successfully!")
        
        # Show next steps
        self.log("\n=== Next Steps ===")
        self.log("1. Edit config/.env with your API keys")
        self.log("2. Test the system: python start.py")
        self.log("3. Start production: ./start_production.sh")
        
        self.save_deployment_log()
        return True


def main():
    """Main deployment function."""
    print("=" * 80)
    print("🚀 Columnist Agent System v2 - Deployment")
    print("=" * 80)
    
    deployer = Deployer()
    
    try:
        success = deployer.deploy()
        
        if success:
            print("\n🎉 Deployment completed successfully!")
        else:
            print("\n❌ Deployment failed. Check deployment.log for details.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        deployer.save_deployment_log()
    
    except Exception as e:
        deployer.log(f"Unexpected error during deployment: {e}", "ERROR")
        deployer.save_deployment_log()
        raise


if __name__ == "__main__":
    main()