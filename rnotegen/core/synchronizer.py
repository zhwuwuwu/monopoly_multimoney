"""ContentSynchronizer orchestrates the end-to-end pipeline:

materials (json file) -> writer (function-calling LLM) -> reviewer -> optional publish.

Replaces the previous ColumnistAgent & AgentCoordinator abstractions.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
import json
from pathlib import Path

from utils.logger import get_logger
from utils.config_loader import ConfigLoader
from .models import Material, GeneratedContent
from .writer_agent import WriterAgent
from .reviewer_agent import ReviewerAgent

logger = get_logger(__name__)


async def load_materials_from_file(file_path: str) -> List[Material]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        materials: List[Material] = []
        for item in data:
            materials.append(Material(
                title=item.get('title', ''),
                content=item.get('content', ''),
                source=item.get('source', ''),
                type=item.get('type', 'unknown'),
                reliability_score=item.get('reliability_score', 0.0)
            ))
        logger.info(f"Loaded {len(materials)} materials from {file_path}")
        return materials
    except Exception as e:  # noqa
        logger.error(f"Failed to load materials: {e}")
        return []


class ContentSynchronizer:
    """High-level orchestrator keeping only two agents: writer + reviewer."""

    def __init__(self, config_path: str = "config"):
        self.config_loader = ConfigLoader(config_path)
        self.writer = WriterAgent(config_path)
        self.reviewer = ReviewerAgent(config_path)
        logger.info("ContentSynchronizer initialized")

    async def generate(self, theme: str, materials: List[Material], additional_context: str = "") -> GeneratedContent:
        return await self.writer.generate(theme, materials, additional_context)

    async def review(self, content: GeneratedContent) -> Dict[str, Any]:
        return await self.reviewer.review(content)

    async def run_pipeline(
        self,
        theme: str,
        materials_file: str,
        additional_context: str = "",
        publish: bool = False,
        output: Optional[str] = None,
        platform: str = "xiaohongshu",
        images: Optional[list] = None,
        quality_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """Execute full pipeline and return dict with content, review, publish_response."""
        materials = await load_materials_from_file(materials_file)
        if not materials:
            raise ValueError("No materials loaded")
        content = await self.generate(theme, materials, additional_context)
        review = await self.review(content)
        if review.get('total_score') is not None and review.get('total_score', 0) < quality_threshold:
            logger.warning("Review score below threshold")
        publish_response = None
        if publish:
            publish_response = await self.publish(platform, content, images)
        if output:
            self._save_output(content, review, output)
        return {"content": content, "review": review, "publish_response": publish_response}

    def _save_output(self, content: GeneratedContent, review: Dict[str, Any], path: str):
        data = {
            "title": content.title,
            "content": content.content,
            "hashtags": content.hashtags,
            "summary": content.summary,
            "word_count": content.word_count,
            "sources": content.sources,
            "fact_checked": content.fact_checked,
            "review": review,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved output to {path}")

    async def publish(self, platform: str, content: GeneratedContent, images: Optional[list] = None):
        if platform != 'xiaohongshu':
            logger.error(f"Unsupported platform: {platform}")
            return None
        # Lazy import to avoid dependency if unused
        try:
            from platforms.xiaohongshu import XiaohongshuClient, XiaohongshuPublisher  # noqa
        except Exception as e:  # noqa
            logger.error(f"Failed to import platform client: {e}")
            return None

        access_token = self.config_loader.get_config_value("XIAOHONGSHU_ACCESS_TOKEN")
        app_id = self.config_loader.get_config_value("XIAOHONGSHU_APP_ID")
        app_secret = self.config_loader.get_config_value("XIAOHONGSHU_APP_SECRET")
        api_base = self.config_loader.get_config_value("XIAOHONGSHU_API_BASE", "https://api.xiaohongshu.com")
        if not all([access_token, app_id, app_secret]):
            logger.error("Missing platform credentials")
            return None
        async with XiaohongshuClient(access_token, app_id, app_secret, api_base) as client:
            publisher = XiaohongshuPublisher(client)
            resp = await publisher.publish_article(content, images)
            if resp.success:
                logger.info(f"Published successfully: {resp.url}")
            else:
                logger.error(f"Publish failed: {resp.error_message}")
            return resp

    async def shutdown(self):
        await self.writer.shutdown()
        await self.reviewer.shutdown()
        logger.info("ContentSynchronizer shutdown")
