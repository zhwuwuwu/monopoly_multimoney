"""
Example usage of the Columnist Agent System v2.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import ColumnistAgentCLI


async def example_single_generation():
    """Example of generating a single piece of content."""
    print("🚀 Example 1: Single Content Generation")
    print("-" * 50)
    
    cli = ColumnistAgentCLI()
    
    # Generate content about AI technology
    result = await cli.generate_single_content(
        theme="人工智能在日常生活中的应用",
        requirements="写一篇适合小红书的科普文章，语言轻松有趣，包含实用建议",
        materials=[
            "AI助手可以帮助处理日常任务",
            "智能家居设备越来越普及",
            "AI在医疗、教育、娱乐等领域都有应用"
        ],
        publish=False,  # Don't actually publish
        draft_mode=True
    )
    
    cli.print_content_result(result)


async def example_batch_generation():
    """Example of generating multiple pieces of content."""
    print("\n\n🚀 Example 2: Batch Content Generation")
    print("-" * 50)
    
    cli = ColumnistAgentCLI()
    
    # Generate content for multiple themes
    themes = [
        "Python编程入门技巧",
        "数据科学职业发展建议",
        "机器学习项目实战经验"
    ]
    
    results = await cli.generate_batch_content(
        themes=themes,
        requirements="写技术分享类文章，适合程序员和数据科学爱好者阅读",
        materials=[
            "注重实践和代码示例",
            "分享踩坑经验和解决方案",
            "提供学习资源和职业建议"
        ],
        publish=False,
        draft_mode=True
    )
    
    print(f"\n📊 批量生成完成，共生成 {len(results)} 篇内容:")
    for i, result in enumerate(results, 1):
        print(f"\n--- 第 {i} 篇: {result['theme']} ---")
        cli.print_content_result(result)


async def example_system_status():
    """Example of checking system status."""
    print("\n\n🚀 Example 3: System Status Check")
    print("-" * 50)
    
    cli = ColumnistAgentCLI()
    
    status = await cli.get_system_status()
    
    print("🔧 系统状态:")
    print(f"  整体状态: {status['status']}")
    print(f"  检查时间: {status['timestamp']}")
    print(f"  写手代理: {status.get('writer_agent', 'unknown')}")
    print(f"  评审代理: {status.get('reviewer_agent', 'unknown')}")
    print(f"  MCP服务器: {status.get('mcp_server', 'unknown')}")
    print(f"  质量阈值: {status.get('quality_threshold', 'unknown')}")
    print(f"  最大迭代次数: {status.get('max_iterations', 'unknown')}")
    
    if 'error' in status:
        print(f"  错误信息: {status['error']}")


async def main():
    """Run all examples."""
    print("=" * 80)
    print("🎯 Columnist Agent System v2 - 使用示例")
    print("=" * 80)
    
    try:
        # Example 1: Single content generation
        await example_single_generation()
        
        # Example 2: Batch content generation
        await example_batch_generation()
        
        # Example 3: System status
        await example_system_status()
        
        print("\n" + "=" * 80)
        print("✅ 所有示例执行完成!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())