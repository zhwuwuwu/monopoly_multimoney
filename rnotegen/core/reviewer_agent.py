"""ReviewerAgent evaluates generated content for quality & compliance, sharing base with WriterAgent."""

from __future__ import annotations

from typing import Dict, Any
from utils.logger import get_logger
from .models import GeneratedContent
from .base_agent import BaseOpenAIAgent

logger = get_logger(__name__)


class ReviewerAgent(BaseOpenAIAgent):
    def __init__(self, config_path: str = "config"):
        super().__init__(config_path=config_path)
        logger.info("ReviewerAgent initialized")

    def build_system_prompt(self) -> str:  # override
        return "你是一位严格、客观、注重事实与合规风险的中文内容审查专家。输出 JSON 评估。"

    async def review(self, content: GeneratedContent) -> Dict[str, Any]:
        self.reset_conversation()
        prompt = (
            "评估文章质量并给出风险。返回JSON: "
            "scores(factual, originality, logic, readability, platform_fit, compliance, legal), "
            "total_score, strengths, risks(list of {issue,severity,suggestion}), improvement_suggestions。"
            f"标题:{content.title} 字数:{content.word_count} 正文:{content.content}"
        )
        self.append("user", prompt)
        response = await self.chat(temperature=0.2)
        raw = response.choices[0].message.content or ""
        data = self.extract_json(raw, required_keys={"scores", "total_score"})
        if not data:
            logger.error("ReviewerAgent failed to parse JSON, returning raw snippet")
            return {"error": "parse_failed", "raw": raw[:1200]}
        return data

    async def shutdown(self):  # override for consistency
        await super().shutdown()

