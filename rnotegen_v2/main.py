"""
Main entry point for the Columnist Agent System v2.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from synchronizer import ContentSynchronizer, ContentRequest
from publisher.rednote import RedNotePublisher, PublishConfig
from utils.config_loader import ConfigLoader
from utils.logger import get_logger

logger = get_logger(__name__)


class ColumnistAgentCLI:
    """Command Line Interface for the Columnist Agent System."""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.synchronizer = None
        self.publisher = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the system components."""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing Columnist Agent System v2...")
            
            # Load configurations
            writer_config = self.config_loader.load_writer_config()
            reviewer_config = self.config_loader.load_reviewer_config()
            openai_config = self.config_loader.load_openai_config()
            publisher_config = self.config_loader.load_publisher_config()
            
            # Initialize synchronizer
            self.synchronizer = ContentSynchronizer(
                writer_config=writer_config,
                reviewer_config=reviewer_config,
                openai_config=openai_config,
                mcp_server_url="http://localhost:5000"
            )
            
            # Initialize publisher
            self.publisher = RedNotePublisher(publisher_config)
            
            self._initialized = True
            logger.info("System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    async def generate_single_content(self, theme: str, requirements: str = "", 
                                    materials: List[str] = None, publish: bool = False,
                                    draft_mode: bool = True) -> Dict[str, Any]:
        """Generate a single piece of content."""
        await self.initialize()
        
        if materials is None:
            materials = []
        
        # Create content request
        request = ContentRequest(
            theme=theme,
            requirements=requirements,
            materials=materials,
            target_audience="小红书用户",
            content_type="article",
            min_word_count=300,
            max_iterations=3
        )
        
        # Generate content
        logger.info(f"Generating content for theme: {theme}")
        result = await self.synchronizer.generate_content(request)
        
        # Prepare response
        response = {
            "status": result.status,
            "article": {
                "title": result.article.title,
                "content": result.article.content,
                "summary": result.article.summary,
                "hashtags": result.article.hashtags,
                "word_count": result.article.word_count
            },
            "review": {
                "score": result.review_result.score,
                "assessment": result.review_result.overall_assessment,
                "feedback": result.review_result.feedback,
                "suggestions": result.review_result.suggestions
            },
            "metadata": {
                "iterations": result.iterations,
                "generation_time": result.generation_time,
                "final_score": result.final_score
            }
        }
        
        # Publish if requested
        if publish and result.status == "success":
            publish_config = PublishConfig(draft_mode=draft_mode)
            publish_result = await self.publisher.publish_article(result.article, publish_config)
            
            response["publish"] = {
                "success": publish_result.success,
                "post_id": publish_result.post_id,
                "post_url": publish_result.post_url,
                "error": publish_result.error_message
            }
        
        return response
    
    async def generate_batch_content(self, themes: List[str], requirements: str = "",
                                   materials: List[str] = None, publish: bool = False,
                                   draft_mode: bool = True) -> List[Dict[str, Any]]:
        """Generate multiple pieces of content."""
        await self.initialize()
        
        if materials is None:
            materials = []
        
        # Create content requests
        requests = []
        for theme in themes:
            request = ContentRequest(
                theme=theme,
                requirements=requirements,
                materials=materials,
                target_audience="小红书用户",
                content_type="article",
                min_word_count=300,
                max_iterations=3
            )
            requests.append(request)
        
        # Generate content batch
        logger.info(f"Generating {len(themes)} pieces of content")
        results = await self.synchronizer.batch_generate(requests)
        
        # Process results
        responses = []
        successful_articles = []
        
        for i, result in enumerate(results):
            response = {
                "theme": themes[i],
                "status": result.status,
                "article": {
                    "title": result.article.title,
                    "content": result.article.content,
                    "summary": result.article.summary,
                    "hashtags": result.article.hashtags,
                    "word_count": result.article.word_count
                },
                "review": {
                    "score": result.review_result.score,
                    "assessment": result.review_result.overall_assessment,
                    "feedback": result.review_result.feedback
                },
                "metadata": {
                    "iterations": result.iterations,
                    "generation_time": result.generation_time,
                    "final_score": result.final_score
                }
            }
            responses.append(response)
            
            if result.status == "success":
                successful_articles.append(result.article)
        
        # Batch publish if requested
        if publish and successful_articles:
            publish_config = PublishConfig(draft_mode=draft_mode)
            publish_results = await self.publisher.batch_publish(successful_articles, publish_config)
            
            # Add publish results to responses
            publish_index = 0
            for response in responses:
                if response["status"] == "success":
                    publish_result = publish_results[publish_index]
                    response["publish"] = {
                        "success": publish_result.success,
                        "post_id": publish_result.post_id,
                        "post_url": publish_result.post_url,
                        "error": publish_result.error_message
                    }
                    publish_index += 1
        
        return responses
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status."""
        await self.initialize()
        return await self.synchronizer.get_system_status()
    
    def print_content_result(self, result: Dict[str, Any]):
        """Pretty print content generation result."""
        print("\n" + "="*80)
        print(f"📝 内容生成结果 - {result['status'].upper()}")
        print("="*80)
        
        article = result['article']
        print(f"📋 标题: {article['title']}")
        print(f"📊 字数: {article['word_count']}")
        print(f"🏷️  标签: {', '.join(article['hashtags'])}")
        print(f"📈 评分: {result['review']['score']:.2f} ({result['review']['assessment']})")
        print(f"🔄 迭代次数: {result['metadata']['iterations']}")
        print(f"⏱️  生成时间: {result['metadata']['generation_time']:.2f}秒")
        
        print(f"\n📄 摘要:\n{article['summary']}")
        
        print(f"\n📝 正文内容:")
        print("-" * 40)
        print(article['content'])
        print("-" * 40)
        
        if result['review']['feedback']:
            print(f"\n💭 评审反馈:\n{result['review']['feedback']}")
        
        if result['review']['suggestions']:
            print(f"\n💡 改进建议:")
            for i, suggestion in enumerate(result['review']['suggestions'], 1):
                print(f"  {i}. {suggestion}")
        
        if 'publish' in result:
            publish = result['publish']
            if publish['success']:
                print(f"\n✅ 发布成功!")
                print(f"   文章ID: {publish['post_id']}")
                if publish['post_url']:
                    print(f"   链接: {publish['post_url']}")
            else:
                print(f"\n❌ 发布失败: {publish['error']}")
        
        print("="*80)


def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Columnist Agent System v2")
    parser.add_argument("command", choices=["generate", "batch", "status"], 
                       help="Command to execute")
    
    # Generate command arguments
    parser.add_argument("--theme", type=str, help="Content theme")
    parser.add_argument("--themes", type=str, nargs="+", help="Multiple themes for batch generation")
    parser.add_argument("--requirements", type=str, default="", help="Content requirements")
    parser.add_argument("--materials", type=str, nargs="*", default=[], help="Reference materials")
    parser.add_argument("--publish", action="store_true", help="Publish generated content")
    parser.add_argument("--draft", action="store_true", default=True, help="Publish as draft")
    
    args = parser.parse_args()
    
    cli = ColumnistAgentCLI()
    
    async def run_command():
        try:
            if args.command == "generate":
                if not args.theme:
                    print("❌ Error: --theme is required for generate command")
                    return
                
                result = await cli.generate_single_content(
                    theme=args.theme,
                    requirements=args.requirements,
                    materials=args.materials,
                    publish=args.publish,
                    draft_mode=args.draft
                )
                cli.print_content_result(result)
            
            elif args.command == "batch":
                if not args.themes:
                    print("❌ Error: --themes is required for batch command")
                    return
                
                results = await cli.generate_batch_content(
                    themes=args.themes,
                    requirements=args.requirements,
                    materials=args.materials,
                    publish=args.publish,
                    draft_mode=args.draft
                )
                
                print(f"\n📊 批量生成完成 - 共 {len(results)} 篇内容")
                for i, result in enumerate(results, 1):
                    print(f"\n--- 第 {i} 篇 ---")
                    cli.print_content_result(result)
            
            elif args.command == "status":
                status = await cli.get_system_status()
                print("\n🔧 系统状态:")
                print(f"  状态: {status['status']}")
                print(f"  时间: {status['timestamp']}")
                print(f"  写手代理: {status.get('writer_agent', 'unknown')}")
                print(f"  评审代理: {status.get('reviewer_agent', 'unknown')}")
                print(f"  MCP服务器: {status.get('mcp_server', 'unknown')}")
                print(f"  质量阈值: {status.get('quality_threshold', 'unknown')}")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断操作")
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            logger.error(f"Command execution failed: {e}")
    
    # Run the async command
    asyncio.run(run_command())


if __name__ == "__main__":
    main()