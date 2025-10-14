#!/usr/bin/env python3
"""
Quick start script for Columnist Agent System v2.
"""

import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path


def check_requirements():
    """Check if all requirements are installed."""
    print("🔍 检查系统要求...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ 是必需的")
        return False
    
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check if requirements.txt exists
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ requirements.txt 文件未找到")
        return False
    
    print("✅ requirements.txt 找到")
    
    # Check if .env file exists
    env_file = Path("config/.env")
    if not env_file.exists():
        print("⚠️  config/.env 文件未找到，将使用 .env.example")
        example_file = Path("config/.env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✅ 已复制 .env.example 到 .env")
        else:
            print("❌ config/.env.example 文件也未找到")
            return False
    
    print("✅ 环境配置文件存在")
    return True


def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 安装依赖包...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True, text=True)
        
        print("✅ 依赖包安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False


def start_mcp_server():
    """Start the MCP server in background."""
    print("\n🚀 启动 MCP 服务器...")
    
    try:
        # Start MCP server as background process
        process = subprocess.Popen([
            sys.executable, "-m", "mcp_server.server"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ MCP 服务器启动成功 (PID: {})".format(process.pid))
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ MCP 服务器启动失败")
            print(f"错误: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ 启动 MCP 服务器时出错: {e}")
        return None


async def test_system():
    """Test the system with a simple example."""
    print("\n🧪 测试系统功能...")
    
    try:
        from main import ColumnistAgentCLI
        
        cli = ColumnistAgentCLI()
        
        # Test system status
        status = await cli.get_system_status()
        
        if status["status"] == "healthy":
            print("✅ 系统状态正常")
            print(f"   写手代理: {status.get('writer_agent', 'unknown')}")
            print(f"   评审代理: {status.get('reviewer_agent', 'unknown')}")
            print(f"   MCP服务器: {status.get('mcp_server', 'unknown')}")
            return True
        else:
            print(f"❌ 系统状态异常: {status.get('error', 'unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ 系统测试失败: {e}")
        return False


def show_usage_examples():
    """Show usage examples."""
    print("\n📖 使用示例:")
    print("-" * 50)
    
    print("1. 生成单篇内容:")
    print("   python main.py generate --theme \"AI技术应用\" --requirements \"科普文章\"")
    
    print("\n2. 批量生成内容:")
    print("   python main.py batch --themes \"Python编程\" \"数据分析\" --publish --draft")
    
    print("\n3. 检查系统状态:")
    print("   python main.py status")
    
    print("\n4. 运行完整示例:")
    print("   python examples/example_usage.py")
    
    print("\n📝 配置文件:")
    print("   - config/.env                 # API密钥和环境变量")
    print("   - config/writer_config.yaml   # 写手代理配置")
    print("   - config/reviewer_config.yaml # 评审代理配置")


def main():
    """Main startup function."""
    print("=" * 80)
    print("🎯 Columnist Agent System v2 - 快速启动")
    print("=" * 80)
    
    # Step 1: Check requirements
    if not check_requirements():
        print("\n❌ 系统要求检查失败，请解决上述问题后重试")
        return
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n❌ 依赖包安装失败，请手动运行: pip install -r requirements.txt")
        return
    
    # Step 3: Start MCP server
    mcp_process = start_mcp_server()
    if not mcp_process:
        print("\n❌ MCP 服务器启动失败，请检查端口 5000 是否被占用")
        return
    
    try:
        # Step 4: Test system
        test_result = asyncio.run(test_system())
        
        if test_result:
            print("\n🎉 系统启动成功！")
            show_usage_examples()
        else:
            print("\n⚠️  系统测试未完全通过，但可以尝试使用")
            show_usage_examples()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断启动过程")
    
    finally:
        # Clean up MCP server process
        if mcp_process and mcp_process.poll() is None:
            print(f"\n🛑 关闭 MCP 服务器 (PID: {mcp_process.pid})")
            mcp_process.terminate()
            mcp_process.wait()
    
    print("\n" + "=" * 80)
    print("📋 启动完成")
    print("=" * 80)


if __name__ == "__main__":
    main()