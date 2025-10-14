"""
RedNote (Xiaohongshu) Publisher for content publishing.
"""

import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp

from ..agents.writer_agent import Article
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PublishConfig:
    """Publishing configuration."""
    platform: str = "rednote"
    schedule_time: Optional[datetime] = None
    auto_hashtags: bool = True
    max_hashtags: int = 10
    image_required: bool = True
    draft_mode: bool = False


@dataclass
class PublishResult:
    """Publishing result."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None
    platform_response: Optional[Dict[str, Any]] = None


class RedNotePublisher:
    """RedNote/Xiaohongshu content publisher."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize RedNote publisher with configuration."""
        self.config = config
        self.api_config = config.get("rednote", {})
        self.base_url = self.api_config.get("base_url", "https://api.xiaohongshu.com")
        self.app_id = self.api_config.get("app_id")
        self.app_secret = self.api_config.get("app_secret")
        self.access_token = self.api_config.get("access_token")
        
        # Publishing constraints
        self.max_title_length = 20
        self.max_content_length = 1000
        self.max_hashtags = 10
        
        logger.info("RedNote Publisher initialized")
    
    async def publish_article(self, article: Article, config: PublishConfig = None) -> PublishResult:
        """Publish article to RedNote platform."""
        if config is None:
            config = PublishConfig()
        
        logger.info(f"Publishing article to RedNote: {article.title}")
        
        try:
            # Validate article for platform
            validation_result = self._validate_article(article)
            if not validation_result["valid"]:
                return PublishResult(
                    success=False,
                    error_message=f"Article validation failed: {validation_result['errors']}"
                )
            
            # Format content for RedNote
            formatted_content = self._format_for_rednote(article, config)
            
            # If in draft mode, return success without actual publishing
            if config.draft_mode:
                logger.info("Draft mode enabled, skipping actual publishing")
                return PublishResult(
                    success=True,
                    post_id=f"draft_{int(time.time())}",
                    published_at=datetime.now(),
                    platform_response={"mode": "draft", "formatted_content": formatted_content}
                )
            
            # Publish to RedNote API
            result = await self._publish_to_api(formatted_content, config)
            
            if result["success"]:
                logger.info(f"Successfully published to RedNote: {result.get('post_id')}")
                return PublishResult(
                    success=True,
                    post_id=result.get("post_id"),
                    post_url=result.get("post_url"),
                    published_at=datetime.now(),
                    platform_response=result
                )
            else:
                logger.error(f"Failed to publish to RedNote: {result.get('error')}")
                return PublishResult(
                    success=False,
                    error_message=result.get("error", "Unknown error"),
                    platform_response=result
                )
                
        except Exception as e:
            logger.error(f"Error publishing to RedNote: {e}")
            return PublishResult(
                success=False,
                error_message=str(e)
            )
    
    def _validate_article(self, article: Article) -> Dict[str, Any]:
        """Validate article for RedNote platform requirements."""
        errors = []
        
        # Check title length
        if len(article.title) > self.max_title_length:
            errors.append(f"Title too long: {len(article.title)} > {self.max_title_length}")
        
        # Check content length
        if len(article.content) > self.max_content_length:
            errors.append(f"Content too long: {len(article.content)} > {self.max_content_length}")
        
        # Check hashtags count
        if len(article.hashtags) > self.max_hashtags:
            errors.append(f"Too many hashtags: {len(article.hashtags)} > {self.max_hashtags}")
        
        # Check for required content
        if not article.title.strip():
            errors.append("Title is required")
        
        if not article.content.strip():
            errors.append("Content is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _format_for_rednote(self, article: Article, config: PublishConfig) -> Dict[str, Any]:
        """Format article content for RedNote platform."""
        # Truncate title if too long
        title = article.title[:self.max_title_length] if len(article.title) > self.max_title_length else article.title
        
        # Truncate content if too long
        content = article.content
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length-3] + "..."
        
        # Process hashtags
        hashtags = article.hashtags[:self.max_hashtags] if len(article.hashtags) > self.max_hashtags else article.hashtags
        
        # Add automatic hashtags if enabled
        if config.auto_hashtags:
            auto_tags = self._generate_auto_hashtags(article)
            hashtags.extend(auto_tags)
            hashtags = list(set(hashtags))[:self.max_hashtags]  # Remove duplicates and limit
        
        # Format hashtags for RedNote
        hashtag_text = " ".join([f"#{tag}" for tag in hashtags])
        
        # Combine content with hashtags
        full_content = f"{content}\n\n{hashtag_text}"
        
        return {
            "title": title,
            "content": full_content,
            "hashtags": hashtags,
            "summary": article.summary,
            "word_count": len(full_content),
            "original_word_count": article.word_count
        }
    
    def _generate_auto_hashtags(self, article: Article) -> List[str]:
        """Generate automatic hashtags based on content."""
        auto_tags = []
        
        # Content-based tags
        content_lower = article.content.lower()
        
        # Technology tags
        tech_keywords = {
            "ai": "AI", "人工智能": "人工智能", "机器学习": "机器学习", "深度学习": "深度学习",
            "python": "Python", "编程": "编程", "代码": "编程",
            "数据": "数据分析", "算法": "算法", "技术": "技术分享"
        }
        
        for keyword, tag in tech_keywords.items():
            if keyword in content_lower and tag not in article.hashtags:
                auto_tags.append(tag)
        
        # General engagement tags
        engagement_tags = ["干货分享", "学习笔记", "经验分享", "知识科普"]
        
        # Add 1-2 engagement tags if space available
        remaining_slots = self.max_hashtags - len(article.hashtags) - len(auto_tags)
        if remaining_slots > 0:
            auto_tags.extend(engagement_tags[:min(remaining_slots, 2)])
        
        return auto_tags
    
    async def _publish_to_api(self, formatted_content: Dict[str, Any], config: PublishConfig) -> Dict[str, Any]:
        """Publish content to RedNote API (mock implementation)."""
        # This is a mock implementation since we don't have real RedNote API credentials
        # In a real implementation, this would make actual API calls
        
        logger.info("Publishing to RedNote API (mock implementation)")
        
        # Simulate API delay
        await asyncio.sleep(1)
        
        # Mock API response
        if self.app_id and self.app_secret:
            # Simulate successful API call
            post_id = self._generate_post_id(formatted_content)
            return {
                "success": True,
                "post_id": post_id,
                "post_url": f"https://www.xiaohongshu.com/explore/{post_id}",
                "message": "Content published successfully",
                "platform": "rednote",
                "published_content": formatted_content
            }
        else:
            # Simulate API configuration error
            return {
                "success": False,
                "error": "Missing API credentials (app_id or app_secret)",
                "message": "Please configure RedNote API credentials"
            }
    
    def _generate_post_id(self, content: Dict[str, Any]) -> str:
        """Generate a mock post ID based on content."""
        content_hash = hashlib.md5(
            json.dumps(content, sort_keys=True, ensure_ascii=False).encode('utf-8')
        ).hexdigest()[:12]
        timestamp = int(time.time())
        return f"rn_{timestamp}_{content_hash}"
    
    async def get_publish_status(self, post_id: str) -> Dict[str, Any]:
        """Get publishing status for a post."""
        # Mock implementation
        logger.info(f"Checking publish status for post: {post_id}")
        
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        return {
            "post_id": post_id,
            "status": "published",
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "published_at": datetime.now().isoformat()
        }
    
    async def batch_publish(self, articles: List[Article], config: PublishConfig = None) -> List[PublishResult]:
        """Publish multiple articles in batch."""
        logger.info(f"Batch publishing {len(articles)} articles to RedNote")
        
        results = []
        for i, article in enumerate(articles, 1):
            logger.info(f"Publishing article {i}/{len(articles)}: {article.title}")
            try:
                result = await self.publish_article(article, config)
                results.append(result)
                
                # Add delay between publications to avoid rate limiting
                if i < len(articles):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"Failed to publish article {i}: {e}")
                results.append(PublishResult(
                    success=False,
                    error_message=str(e)
                ))
        
        successful_count = sum(1 for r in results if r.success)
        logger.info(f"Batch publishing completed: {successful_count}/{len(articles)} successful")
        
        return results


# Import asyncio for async operations
import asyncio