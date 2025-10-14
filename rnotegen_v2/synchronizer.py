"""
Content Synchronizer - Main controller for the columnist agent system.
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .writer_agent import WriterAgent, Article
from .reviewer_agent import ReviewerAgent, ReviewResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContentRequest:
    """Content generation request structure."""
    theme: str
    requirements: str
    materials: List[str]
    deadline: Optional[datetime] = None
    target_audience: Optional[str] = None
    content_type: str = "article"
    min_word_count: int = 800
    max_iterations: int = 3


@dataclass
class ContentOutput:
    """Final content output structure."""
    article: Article
    review_result: ReviewResult
    iterations: int
    generation_time: float
    final_score: float
    status: str  # "success", "failed", "timeout"


class ContentSynchronizer:
    """Main controller for content generation and review workflow."""
    
    def __init__(self, writer_config: Dict[str, Any], reviewer_config: Dict[str, Any], 
                 openai_config: Dict[str, str], mcp_server_url: str = "http://localhost:5000"):
        """Initialize the synchronizer with agent configurations."""
        self.writer_config = writer_config
        self.reviewer_config = reviewer_config
        self.openai_config = openai_config
        self.mcp_server_url = mcp_server_url
        
        # Initialize agents
        self.writer_agent = WriterAgent(writer_config, openai_config, mcp_server_url)
        self.reviewer_agent = ReviewerAgent(reviewer_config, openai_config)
        
        # Configuration parameters
        self.max_iterations = 3
        self.quality_threshold = reviewer_config["reviewer"]["quality_threshold"]
        
        logger.info("Content Synchronizer initialized successfully")
    
    async def generate_content(self, request: ContentRequest) -> ContentOutput:
        """Main content generation workflow."""
        logger.info(f"Starting content generation for theme: {request.theme}")
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Initialize tracking variables
            iterations = 0
            max_iterations = min(request.max_iterations, self.max_iterations)
            best_article = None
            best_review = None
            best_score = 0.0
            
            while iterations < max_iterations:
                iterations += 1
                logger.info(f"Content generation iteration {iterations}/{max_iterations}")
                
                try:
                    # Generate content using writer agent
                    article = await self.writer_agent.generate_content(
                        theme=request.theme,
                        requirements=request.requirements,
                        materials=request.materials,
                        target_audience=request.target_audience,
                        content_type=request.content_type,
                        min_word_count=request.min_word_count
                    )
                    
                    # Review content using reviewer agent
                    review_result = await self.reviewer_agent.review_content(article)
                    
                    logger.info(f"Iteration {iterations} score: {review_result.score:.2f}")
                    
                    # Track best result
                    if review_result.score > best_score:
                        best_article = article
                        best_review = review_result
                        best_score = review_result.score
                    
                    # Check if quality threshold is met
                    if self.reviewer_agent.is_quality_acceptable(review_result):
                        logger.info(f"Quality threshold met at iteration {iterations}")
                        break
                    
                    # If not last iteration, provide feedback for improvement
                    if iterations < max_iterations:
                        await self._provide_improvement_feedback(review_result)
                        
                except Exception as e:
                    logger.error(f"Error in iteration {iterations}: {e}")
                    continue
            
            # Calculate generation time
            generation_time = asyncio.get_event_loop().time() - start_time
            
            # Determine final status
            if best_article is None:
                status = "failed"
                # Create minimal fallback content
                best_article = Article(
                    title="内容生成失败",
                    content="抱歉，暂时无法生成高质量内容，请稍后重试。",
                    summary="内容生成过程中遇到技术问题",
                    hashtags=["技术问题"],
                    word_count=15
                )
                best_review = ReviewResult(
                    score=0.0,
                    dimensions={},
                    feedback="内容生成失败",
                    suggestions=["请检查系统配置"],
                    overall_assessment="失败"
                )
                best_score = 0.0
            elif best_score >= self.quality_threshold:
                status = "success"
            else:
                status = "timeout"
            
            # Create final output
            output = ContentOutput(
                article=best_article,
                review_result=best_review,
                iterations=iterations,
                generation_time=generation_time,
                final_score=best_score,
                status=status
            )
            
            logger.info(f"Content generation completed. Status: {status}, Score: {best_score:.2f}, "
                       f"Iterations: {iterations}, Time: {generation_time:.2f}s")
            
            return output
            
        except Exception as e:
            logger.error(f"Critical error in content generation: {e}")
            raise
    
    async def _provide_improvement_feedback(self, review_result: ReviewResult):
        """Provide feedback to writer agent for improvement."""
        # In a more sophisticated implementation, this could update the writer's context
        # For now, we log the feedback for the next iteration
        logger.info("Improvement feedback for next iteration:")
        logger.info(f"Current score: {review_result.score:.2f}")
        logger.info(f"Feedback: {review_result.feedback}")
        for i, suggestion in enumerate(review_result.suggestions, 1):
            logger.info(f"Suggestion {i}: {suggestion}")
    
    async def batch_generate(self, requests: List[ContentRequest]) -> List[ContentOutput]:
        """Generate multiple pieces of content in batch."""
        logger.info(f"Starting batch generation for {len(requests)} requests")
        
        results = []
        for i, request in enumerate(requests, 1):
            logger.info(f"Processing batch request {i}/{len(requests)}")
            try:
                result = await self.generate_content(request)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process batch request {i}: {e}")
                # Add failed result
                failed_result = ContentOutput(
                    article=Article(
                        title="批量生成失败",
                        content="此条内容生成失败",
                        summary="批量处理中的失败项",
                        hashtags=["生成失败"],
                        word_count=8
                    ),
                    review_result=ReviewResult(
                        score=0.0,
                        dimensions={},
                        feedback="批量生成失败",
                        suggestions=[],
                        overall_assessment="失败"
                    ),
                    iterations=0,
                    generation_time=0.0,
                    final_score=0.0,
                    status="failed"
                )
                results.append(failed_result)
        
        logger.info(f"Batch generation completed. {len(results)} results generated")
        return results
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status and health check."""
        try:
            # Test MCP server connectivity
            mcp_status = await self.writer_agent.mcp_client.health_check()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "writer_agent": "ready",
                "reviewer_agent": "ready",
                "mcp_server": "connected" if mcp_status else "disconnected",
                "quality_threshold": self.quality_threshold,
                "max_iterations": self.max_iterations
            }
        except Exception as e:
            logger.error(f"System status check failed: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def update_writer_config(self, new_config: Dict[str, Any]):
        """Update writer agent configuration dynamically."""
        try:
            self.writer_config.update(new_config)
            # Reinitialize writer agent with new config
            self.writer_agent = WriterAgent(self.writer_config, self.openai_config, self.mcp_server_url)
            logger.info("Writer configuration updated successfully")
        except Exception as e:
            logger.error(f"Failed to update writer config: {e}")
            raise
    
    async def update_reviewer_config(self, new_config: Dict[str, Any]):
        """Update reviewer agent configuration dynamically."""
        try:
            self.reviewer_config.update(new_config)
            # Reinitialize reviewer agent with new config
            self.reviewer_agent = ReviewerAgent(self.reviewer_config, self.openai_config)
            self.quality_threshold = self.reviewer_config["reviewer"]["quality_threshold"]
            logger.info("Reviewer configuration updated successfully")
        except Exception as e:
            logger.error(f"Failed to update reviewer config: {e}")
            raise