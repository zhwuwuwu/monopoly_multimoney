"""
Reviewer Agent using OpenAI client.
"""

import json
import re
from typing import Dict, Any, List
from dataclasses import dataclass
from openai import AsyncOpenAI

from .writer_agent import Article
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReviewResult:
    """Review result data structure."""
    score: float
    dimensions: Dict[str, int]
    feedback: str
    suggestions: List[str]
    overall_assessment: str


class ReviewerAgent:
    """Reviewer Agent for content quality assessment."""
    
    def __init__(self, config: Dict[str, Any], openai_config: Dict[str, str]):
        self.config = config
        self.openai_client = AsyncOpenAI(
            api_key=openai_config["api_key"],
            base_url=openai_config["base_url"]
        )
        self.model = openai_config.get("model", "GPT-4o")
        self.temperature = 0.2  # Lower temperature for more consistent reviews
        
        # Extract review configuration
        self.reviewer_config = config["reviewer"]
        self.evaluation_criteria = self.reviewer_config["evaluation_criteria"]
        self.quality_threshold = self.reviewer_config["quality_threshold"]
        self.system_prompt = self.reviewer_config["system_prompt"]
        
        logger.info("Reviewer Agent initialized successfully")
    
    async def review_content(self, article: Article) -> ReviewResult:
        """Review article content and provide detailed feedback."""
        logger.info(f"Reviewing article: {article.title}")
        
        try:
            # Build review prompt
            review_prompt = self._build_review_prompt(article)
            
            # Get review from OpenAI
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": review_prompt}
                ],
                temperature=self.temperature
            )
            
            # Parse review response
            review_data = self._parse_json_response(response.choices[0].message.content)
            
            # Calculate weighted total score
            total_score = self._calculate_total_score(review_data)
            
            # Create ReviewResult
            review_result = ReviewResult(
                score=total_score,
                dimensions=review_data.get("dimensions", {}),
                feedback=review_data.get("feedback", ""),
                suggestions=review_data.get("suggestions", []),
                overall_assessment=self._get_overall_assessment(total_score)
            )
            
            logger.info(f"Review completed with score: {total_score:.2f}")
            return review_result
            
        except Exception as e:
            logger.error(f"Failed to review content: {e}")
            raise
    
    def _build_review_prompt(self, article: Article) -> str:
        """Build review prompt for the article."""
        criteria_descriptions = []
        for criterion, config in self.evaluation_criteria.items():
            criteria_descriptions.append(f"- {criterion}: {config['description']} (权重: {config['weight']})")
        
        return f"""
        请评估以下文章的质量：
        
        标题: {article.title}
        字数: {article.word_count}
        摘要: {article.summary}
        话题标签: {', '.join(article.hashtags)}
        
        正文内容:
        {article.content}
        
        评估标准:
        {chr(10).join(criteria_descriptions)}
        
        请从以下维度进行评分（1-10分）：
        1. 事实准确性 (factual_accuracy): 信息是否准确可靠
        2. 观点独特性 (originality): 是否有独特见解和创新观点
        3. 可读性 (readability): 表达是否清晰，易于理解
        4. 平台适配性 (platform_compliance): 是否符合小红书平台特点
        5. 逻辑清晰度 (logical_clarity): 逻辑结构是否清晰
        6. 互动性 (engagement): 是否能引发读者思考和讨论
        
        请返回JSON格式，包含：
        - dimensions: 各维度评分字典
        - feedback: 详细反馈意见
        - suggestions: 具体改进建议列表
        - strengths: 文章优点
        - weaknesses: 需要改进的地方
        - risks: 潜在风险点
        """
    
    def _calculate_total_score(self, review_data: Dict[str, Any]) -> float:
        """Calculate weighted total score."""
        dimensions = review_data.get("dimensions", {})
        total_score = 0.0
        total_weight = 0.0
        
        for criterion, config in self.evaluation_criteria.items():
            if criterion in dimensions:
                score = dimensions[criterion]
                weight = config["weight"]
                total_score += score * weight
                total_weight += weight
        
        return round(total_score / total_weight if total_weight > 0 else 0.0, 2)
    
    def _get_overall_assessment(self, score: float) -> str:
        """Get overall assessment based on score."""
        if score >= self.reviewer_config.get("excellent_threshold", 8.5):
            return "优秀"
        elif score >= self.quality_threshold:
            return "良好"
        elif score >= 5.0:
            return "一般"
        else:
            return "需要改进"
    
    def _parse_json_response(self, response_content: str) -> Dict[str, Any]:
        """Parse JSON response with error handling."""
        try:
            # Handle code block wrapping
            if response_content.startswith("```json"):
                start = response_content.find("```json") + len("```json")
                end = response_content.rfind("```")
                if end > start:
                    response_content = response_content[start:end].strip()
            
            # Clean up control characters
            response_content = re.sub(r'[\n\r\t]', ' ', response_content)
            response_content = re.sub(r'\s+', ' ', response_content)
            
            return json.loads(response_content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse review response: {e}")
            logger.error(f"Response content: {response_content[:500]}...")
            # Return default structure if parsing fails
            return {
                "dimensions": {
                    "factual_accuracy": 5,
                    "originality": 5,
                    "readability": 5,
                    "platform_compliance": 5,
                    "logical_clarity": 5,
                    "engagement": 5
                },
                "feedback": "无法解析评审结果",
                "suggestions": ["请检查内容生成质量"],
                "strengths": [],
                "weaknesses": ["评审过程出现错误"],
                "risks": []
            }
    
    def is_quality_acceptable(self, review_result: ReviewResult) -> bool:
        """Check if the content quality meets the threshold."""
        return review_result.score >= self.quality_threshold