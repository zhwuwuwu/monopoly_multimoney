"""
Main entry point for the columnist agent system.
"""

import asyncio
import argparse
import json
from pathlib import Path
from typing import List

from core.agent import ColumnistAgent, Material, GeneratedContent
from platforms.xiaohongshu import XiaohongshuClient, XiaohongshuPublisher
from utils.logger import get_logger, setup_logging
from utils.config_loader import ConfigLoader

logger = get_logger(__name__)


async def load_materials_from_file(file_path: str) -> List[Material]:
    """Load materials from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            materials_data = json.load(f)
        
        materials = []
        for item in materials_data:
            material = Material(
                title=item.get("title", ""),
                content=item.get("content", ""),
                source=item.get("source", ""),
                type=item.get("type", "unknown"),
                reliability_score=item.get("reliability_score", 0.0)
            )
            materials.append(material)
        
        logger.info(f"Loaded {len(materials)} materials from {file_path}")
        return materials
        
    except Exception as e:
        logger.error(f"Failed to load materials from {file_path}: {e}")
        return []


async def generate_article(
    agent: ColumnistAgent,
    theme: str,
    materials: List[Material],
    additional_context: str = ""
) -> GeneratedContent:
    """Generate an article using the columnist agent."""
    logger.info(f"Starting article generation for theme: {theme}")
    
    try:
        # Generate content
        content = await agent.generate_content(theme, materials, additional_context)
        
        # Review content quality
        review = await agent.review_content(content)
        logger.info(f"Content review score: {review.get('total_score', 'N/A')}")
        
        if review.get("total_score", 0) < 7:
            logger.warning("Content quality below threshold, consider regeneration")
        
        return content
        
    except Exception as e:
        logger.error(f"Failed to generate article: {e}")
        raise


async def publish_to_xiaohongshu(
    content: GeneratedContent,
    config_loader: ConfigLoader,
    images: List[str] = None
):
    """Publish content to Xiaohongshu platform."""
    logger.info("Publishing to Xiaohongshu")
    
    try:
        # Get Xiaohongshu configuration
        access_token = config_loader.get_config_value("XIAOHONGSHU_ACCESS_TOKEN")
        app_id = config_loader.get_config_value("XIAOHONGSHU_APP_ID")
        app_secret = config_loader.get_config_value("XIAOHONGSHU_APP_SECRET")
        api_base = config_loader.get_config_value("XIAOHONGSHU_API_BASE", "https://api.xiaohongshu.com")
        
        if not all([access_token, app_id, app_secret]):
            logger.error("Missing Xiaohongshu configuration")
            return None
        
        # Create client and publisher
        async with XiaohongshuClient(access_token, app_id, app_secret, api_base) as client:
            publisher = XiaohongshuPublisher(client)
            
            # Publish the article
            response = await publisher.publish_article(content, images)
            
            if response.success:
                logger.info(f"Successfully published to Xiaohongshu: {response.url}")
                return response
            else:
                logger.error(f"Failed to publish: {response.error_message}")
                return None
                
    except Exception as e:
        logger.error(f"Error publishing to Xiaohongshu: {e}")
        return None


async def interactive_mode(agent: ColumnistAgent, config_loader: ConfigLoader):
    """Run the agent in interactive mode."""
    print("=== 专栏作家智能助手 ===")
    print("输入 'help' 查看可用命令")
    print("输入 'quit' 退出程序")
    print()
    
    while True:
        try:
            command = input(">>> ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                break
            elif command.lower() == 'help':
                print("""
可用命令：
- generate <theme> <materials_file> [context] - 生成文章
- themes - 显示可用主题
- config - 显示当前配置
- help - 显示帮助
- quit - 退出程序
                """)
                continue
            elif command.lower() == 'themes':
                themes = agent.column_config["columns"]["default_column"]["themes"]
                print("可用主题：")
                for theme_key, theme_info in themes.items():
                    print(f"- {theme_key}: {theme_info['name']} - {theme_info['description']}")
                continue
            elif command.lower() == 'config':
                writer = agent.writer_config["writer"]
                print(f"作家身份: {writer['name']} - {writer['persona']}")
                print(f"核心价值观: {', '.join(writer['stance']['core_values'])}")
                continue
            elif command.startswith('generate'):
                parts = command.split(' ', 3)
                if len(parts) < 3:
                    print("用法: generate <theme> <materials_file> [context]")
                    continue
                
                theme = parts[1]
                materials_file = parts[2]
                context = parts[3] if len(parts) > 3 else ""
                
                # Load materials
                materials = await load_materials_from_file(materials_file)
                if not materials:
                    print(f"无法加载素材文件: {materials_file}")
                    continue
                
                # Generate article
                print(f"正在生成关于 '{theme}' 的文章...")
                try:
                    content = await generate_article(agent, theme, materials, context)
                    
                    print(f"\n=== 生成的文章 ===")
                    print(f"标题: {content.title}")
                    print(f"字数: {content.word_count}")
                    print(f"标签: {', '.join(content.hashtags)}")
                    print(f"\n内容:\n{content.content}")
                    print(f"\n摘要: {content.summary}")
                    
                    # Ask if user wants to publish
                    publish = input("\n是否发布到小红书？(y/n): ").strip().lower()
                    if publish == 'y':
                        await publish_to_xiaohongshu(content, config_loader)
                    
                except Exception as e:
                    print(f"生成文章失败: {e}")
            else:
                print("未知命令，输入 'help' 查看可用命令")
                
        except KeyboardInterrupt:
            print("\n程序被中断")
            break
        except Exception as e:
            print(f"错误: {e}")
    
    print("再见！")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="专栏作家智能助手")
    parser.add_argument("--config", default="config", help="配置目录路径")
    parser.add_argument("--theme", help="文章主题")
    parser.add_argument("--materials", help="素材文件路径")
    parser.add_argument("--context", help="额外上下文", default="")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--publish", action="store_true", help="发布到小红书")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    # Initialize logging
    config_loader = ConfigLoader(args.config)
    setup_logging(
        level=config_loader.get_config_value("LOG_LEVEL", "INFO"),
        log_file=config_loader.get_config_value("LOG_FILE")
    )
    
    logger.info("Starting columnist agent system")
    
    try:
        # Initialize agent
        agent = ColumnistAgent(args.config)
        
        if args.interactive:
            # Run in interactive mode
            await interactive_mode(agent, config_loader)
        elif args.theme and args.materials:
            # Generate article from command line
            materials = await load_materials_from_file(args.materials)
            if not materials:
                logger.error(f"Failed to load materials from {args.materials}")
                return
            
            content = await generate_article(agent, args.theme, materials, args.context)
            
            # Save to file if specified
            if args.output:
                output_data = {
                    "title": content.title,
                    "content": content.content,
                    "hashtags": content.hashtags,
                    "summary": content.summary,
                    "word_count": content.word_count,
                    "sources": content.sources,
                    "fact_checked": content.fact_checked
                }
                
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Article saved to {args.output}")
            
            # Publish if requested
            if args.publish:
                await publish_to_xiaohongshu(content, config_loader)
            
            # Print results
            print(f"标题: {content.title}")
            print(f"字数: {content.word_count}")
            print(f"标签: {', '.join(content.hashtags)}")
            print(f"\n{content.content}")
        
        else:
            print("请指定主题和素材文件，或使用 --interactive 进入交互模式")
            print("使用 --help 查看完整参数说明")
    
    except Exception as e:
        logger.error(f"系统错误: {e}")
        raise
    
    finally:
        # Cleanup
        if 'agent' in locals():
            await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())