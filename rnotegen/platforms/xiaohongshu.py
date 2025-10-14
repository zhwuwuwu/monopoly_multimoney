"""
Xiaohongshu platform integration.
"""

import aiohttp
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from core.agent import GeneratedContent
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class XiaohongshuPost:
    """Represents a Xiaohongshu post."""
    title: str
    content: str
    hashtags: List[str]
    images: List[str] = None
    privacy: str = "public"  # public, friends, private
    location: str = None


@dataclass
class PostResponse:
    """Response from posting to Xiaohongshu."""
    success: bool
    post_id: str = None
    error_message: str = None
    url: str = None


class XiaohongshuClient:
    """Client for interacting with Xiaohongshu API."""
    
    def __init__(self, access_token: str, app_id: str, app_secret: str, api_base: str = "https://api.xiaohongshu.com"):
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.api_base = api_base.rstrip("/")
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "ColumnistAgent/1.0.0"
        }
    
    async def create_post(self, post: XiaohongshuPost) -> PostResponse:
        """Create a new post on Xiaohongshu."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Format content with hashtags
        formatted_content = self._format_content(post.content, post.hashtags)
        
        post_data = {
            "title": post.title,
            "content": formatted_content,
            "privacy": post.privacy,
            "location": post.location
        }
        
        # Add images if provided
        if post.images:
            post_data["images"] = post.images
        
        try:
            async with self.session.post(
                f"{self.api_base}/api/v1/notes",
                headers=self._get_headers(),
                json=post_data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Post created successfully: {result.get('note_id')}")
                    
                    return PostResponse(
                        success=True,
                        post_id=result.get("note_id"),
                        url=result.get("url")
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create post: {response.status} - {error_text}")
                    
                    return PostResponse(
                        success=False,
                        error_message=f"HTTP {response.status}: {error_text}"
                    )
        
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return PostResponse(
                success=False,
                error_message=str(e)
            )
    
    async def upload_image(self, image_path: str) -> Optional[str]:
        """Upload an image and return the image URL."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            with open(image_path, 'rb') as image_file:
                data = aiohttp.FormData()
                data.add_field('image', image_file, filename=image_path.split('/')[-1])
                
                async with self.session.post(
                    f"{self.api_base}/api/v1/upload/image",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    data=data
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Image uploaded successfully: {result.get('url')}")
                        return result.get("url")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to upload image: {response.status} - {error_text}")
                        return None
        
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return None
    
    async def get_post_stats(self, post_id: str) -> Dict[str, Any]:
        """Get statistics for a post."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(
                f"{self.api_base}/api/v1/notes/{post_id}/stats",
                headers=self._get_headers()
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get post stats: {response.status}")
                    return {}
        
        except Exception as e:
            logger.error(f"Error getting post stats: {e}")
            return {}
    
    def _format_content(self, content: str, hashtags: List[str]) -> str:
        """Format content with hashtags for Xiaohongshu."""
        formatted_hashtags = " ".join([f"#{tag}" for tag in hashtags])
        
        # Add hashtags at the end if not already present
        if not any(f"#{tag}" in content for tag in hashtags):
            content = f"{content}\n\n{formatted_hashtags}"
        
        return content
    
    def convert_generated_content(self, content: GeneratedContent) -> XiaohongshuPost:
        """Convert GeneratedContent to XiaohongshuPost format."""
        return XiaohongshuPost(
            title=content.title,
            content=content.content,
            hashtags=content.hashtags
        )


class XiaohongshuPublisher:
    """High-level publisher for Xiaohongshu content."""
    
    def __init__(self, client: XiaohongshuClient):
        self.client = client
    
    async def publish_article(self, content: GeneratedContent, images: List[str] = None) -> PostResponse:
        """Publish an article to Xiaohongshu."""
        logger.info(f"Publishing article: {content.title}")
        
        # Convert to Xiaohongshu post format
        post = self.client.convert_generated_content(content)
        
        # Add images if provided
        if images:
            uploaded_images = []
            for image_path in images:
                image_url = await self.client.upload_image(image_path)
                if image_url:
                    uploaded_images.append(image_url)
            
            post.images = uploaded_images
        
        # Create the post
        response = await self.client.create_post(post)
        
        if response.success:
            logger.info(f"Article published successfully: {response.post_id}")
        else:
            logger.error(f"Failed to publish article: {response.error_message}")
        
        return response
    
    async def schedule_post(self, content: GeneratedContent, publish_time: str) -> Dict[str, Any]:
        """Schedule a post for later publication (if supported by API)."""
        # This is a placeholder - actual implementation would depend on Xiaohongshu API capabilities
        logger.info(f"Scheduling post for {publish_time}: {content.title}")
        
        return {
            "scheduled": True,
            "publish_time": publish_time,
            "content_id": content.title  # Placeholder
        }