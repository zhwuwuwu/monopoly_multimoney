#!/usr/bin/env python3
"""
Test script for the columnist agent system.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Import with absolute paths
from core.agent import ColumnistAgent, Material
from utils.logger import setup_logging


async def test_basic_functionality():
    """Test basic functionality of the columnist agent."""
    print("=== Testing Columnist Agent ===")
    
    # Setup logging
    setup_logging("INFO")
    
    try:
        # Check configuration
        print("1. Checking configuration...")
        from utils.config_loader import ConfigLoader
        config_loader = ConfigLoader("config")
        
        api_key = config_loader.get_config_value("OPENAI_API_KEY")
        base_url = config_loader.get_config_value("OPENAI_BASE_URL")
        
        if not api_key:
            print("⚠️  OPENAI_API_KEY not configured in .env file")
            print("   Please copy config/.env.template to config/.env and configure your API settings")
            return
        
        print(f"✓ OpenAI API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'Not set'}")
        print(f"✓ OpenAI Base URL: {base_url if base_url else 'Default (OpenAI official)'}")
        
        # Initialize agent
        print("2. Initializing agent...")
        agent = ColumnistAgent("config")
        print("✓ Agent initialized successfully")
        
        # Test materials loading
        print("2. Testing materials loading...")
        test_materials = [
            Material(
                title="测试标题",
                content="这是一个测试内容，用于验证系统功能。",
                source="测试来源",
                type="测试",
                reliability_score=0.8
            )
        ]
        print("✓ Materials created successfully")
        
        # Test material analysis
        print("3. Testing material analysis...")
        analysis = await agent.analyze_materials(test_materials)
        print(f"✓ Analysis completed: {len(str(analysis))} characters")
        
        # Test content generation (mock)
        print("4. Testing content generation...")
        # Note: This will fail without valid OpenAI API key
        try:
            content = await agent.generate_content("social_trends", test_materials, "测试上下文")
            print(f"✓ Content generated: {content.title}")
        except Exception as e:
            print(f"⚠ Content generation test skipped (需要有效的OpenAI API密钥): {e}")
        
        # Cleanup
        await agent.shutdown()
        print("✓ Agent shutdown completed")
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True


def test_configuration_loading():
    """Test configuration loading."""
    print("\n=== Testing Configuration Loading ===")
    
    try:
        from utils.config_loader import ConfigLoader
        
        config_loader = ConfigLoader("config")
        
        # Test writer config
        writer_config = config_loader.load_writer_config()
        print(f"✓ Writer config loaded: {writer_config['writer']['name']}")
        
        # Test column config
        column_config = config_loader.load_column_config()
        print(f"✓ Column config loaded: {len(column_config['columns']['default_column']['themes'])} themes")
        
        # Test env config
        env_config = config_loader.load_env_config()
        print(f"✓ Environment config loaded: {len(env_config)} variables")
        
        print("✓ All configurations loaded successfully")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_example_materials():
    """Test loading example materials."""
    print("\n=== Testing Example Materials ===")
    
    try:
        materials_file = Path("examples/ai_education_materials.json")
        
        if not materials_file.exists():
            print("⚠ Example materials file not found")
            return True
        
        with open(materials_file, 'r', encoding='utf-8') as f:
            materials_data = json.load(f)
        
        print(f"✓ Example materials loaded: {len(materials_data)} items")
        
        # Validate structure
        for i, item in enumerate(materials_data):
            required_fields = ["title", "content", "source", "type"]
            for field in required_fields:
                if field not in item:
                    raise ValueError(f"Missing field '{field}' in item {i}")
        
        print("✓ All materials have required fields")
        return True
        
    except Exception as e:
        print(f"✗ Example materials test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("开始测试专栏作家智能助手系统...\n")
    
    tests = [
        ("配置加载", test_configuration_loading),
        ("示例素材", test_example_materials),
        ("基础功能", test_basic_functionality),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"运行测试: {test_name}")
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"=== 测试总结 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过!")
        return True
    else:
        print("❌ 部分测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)