"""
Core agent implementation for the columnist system.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import AsyncOpenAI
import yaml
import json
from pathlib import Path

from mcp.client import MCPClient
from utils.config_loader import ConfigLoader
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Material:
    """Represents source material for content generation."""
    title: str
    content: str
    source: str
    type: str  # news, historical, theoretical, etc.
    reliability_score: float = 0.0


@dataclass
class GeneratedContent:
    """Represents generated article content."""
    title: str
    content: str
    hashtags: List[str]
    summary: str
    word_count: int
    sources: List[str]
    fact_checked: bool = False


class ColumnistAgent:
    """Main columnist agent class."""
    
    def __init__(self, config_path: str = "config"):
        self.config_loader = ConfigLoader(config_path)
        self.writer_config = self.config_loader.load_writer_config()
        self.column_config = self.config_loader.load_column_config()
        self.env_config = self.config_loader.load_env_config()
        
        # Initialize OpenAI client
        openai_kwargs = {
            "api_key": self.env_config.get("OPENAI_API_KEY")
        }
        
        # Add base URL if provided
        base_url = self.env_config.get("OPENAI_BASE_URL")
        if base_url:
            openai_kwargs["base_url"] = base_url
            
        self.openai_client = AsyncOpenAI(**openai_kwargs)
        
        # Initialize MCP client
        self.mcp_client = MCPClient(
            server_url=self.env_config.get("MCP_SERVER_URL", "ws://localhost:8000")
        )
        
        # Build system prompt
        self.system_prompt = self._build_system_prompt()
        
        logger.info("Columnist agent initialized successfully")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from writer configuration."""
        writer = self.writer_config["writer"]
        
        return writer["system_prompt"].format(
            name=writer["name"],
            persona=writer["persona"],
            core_values="\n".join(f"- {value}" for value in writer["stance"]["core_values"]),
            writing_style="\n".join(f"- {style}" for style in writer["stance"]["writing_style"]),
            expertise_areas="\n".join(f"- {area}" for area in writer["stance"]["expertise_areas"])
        )
    
    async def analyze_materials(self, materials: List[Material]) -> Dict[str, Any]:
        """Analyze provided materials to extract key insights."""
        logger.info(f"Analyzing {len(materials)} materials")
        
        materials_text = "\n\n".join([
            f"标题: {mat.title}\n来源: {mat.source}\n类型: {mat.type}\n内容: {mat.content[:500]}..."
            for mat in materials
        ])
        
        analysis_prompt = f"""
        请分析以下素材，提取关键信息和潜在的写作角度：
        
        {materials_text}
        
        请从以下维度分析：
        1. 主要事实和数据
        2. 不同观点和立场
        3. 历史背景和趋势
        4. 潜在的争议点
        5. 适合的写作角度
        
        请以JSON格式返回分析结果。
        """
        
        response = await self.openai_client.chat.completions.create(
            model=self.env_config.get("OPENAI_MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3
        )
        
        try:
            response_content = response.choices[0].message.content
            logger.info(f"Raw analysis response: {response_content[:300]}...")
            
            # Extract JSON from code block if present
            if response_content.startswith("```json"):
                # Find the JSON content between ```json and ```
                start = response_content.find("```json") + len("```json")
                end = response_content.rfind("```")
                if end > start:
                    response_content = response_content[start:end].strip()
            
            # Clean up the JSON content to handle control characters
            import re
            response_content = re.sub(r'[\n\r\t]', ' ', response_content)
            response_content = re.sub(r'\s+', ' ', response_content)  # Normalize whitespace
            
            analysis = json.loads(response_content)
            logger.info("Material analysis completed successfully")
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis response as JSON: {e}")
            logger.error(f"Analysis response content: {response.choices[0].message.content}")
            return {"error": "Failed to parse analysis"}
    
    async def research_topic(self, topic: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Research additional information about the topic using MCP tools."""
        logger.info(f"Researching topic: {topic}")
        
        research_results = []
        
        # Use MCP client to search for information
        search_queries = [topic] + keywords[:3]  # Limit to avoid too many queries
        
        for query in search_queries:
            try:
                results = await self.mcp_client.search_internet(query)
                research_results.extend(results)
            except Exception as e:
                logger.error(f"Failed to search for '{query}': {e}")
        
        # Fact-check key claims using MCP tools
        if self.env_config.get("ENABLE_FACT_CHECKING", True):
            fact_check_results = await self.mcp_client.fact_check(research_results)
            logger.info(f"Fact-checking completed for {len(fact_check_results)} items")
        
        return research_results
    
    async def generate_content(
        self, 
        theme: str,
        materials: List[Material],
        additional_context: str = ""
    ) -> GeneratedContent:
        """Generate article content based on materials and theme."""
        logger.info(f"Generating content for theme: {theme}")
        
        # Analyze materials
        analysis = await self.analyze_materials(materials)
        
        # Research additional information
        if self.env_config.get("ENABLE_INTERNET_RESEARCH", True):
            research_results = await self.research_topic(
                theme, 
                self.column_config["columns"]["default_column"]["themes"].get(theme, {}).get("keywords", [])
            )
        else:
            research_results = []
        
        # Get theme configuration
        theme_config = self.column_config["columns"]["default_column"]["themes"].get(theme, {})
        platform_settings = self.column_config["columns"]["default_column"]["platform_settings"]["xiaohongshu"]
        
        # Build content generation prompt
        content_prompt = f"""
        请基于以下信息生成一篇专栏文章：
        
        主题: {theme_config.get('name', theme)}
        主题描述: {theme_config.get('description', '')}
        
        素材分析结果:
        {json.dumps(analysis, ensure_ascii=False, indent=2)}
        
        可选额外深度研究信息:
        {json.dumps(research_results[:5], ensure_ascii=False, indent=2)}  # Limit research results
        
        额外上下文:
        {additional_context}
        
        文章要求:
        1. 字数控制在{platform_settings['max_length']}字以内
        2. 忠于自己的人设、三观和风格
        3. 体现我的独特观点和立场
        4. 基于事实进行分析
        5. 适合小红书平台的阅读习惯
        6. 结尾要有{platform_settings['engagement_style']}
        
        请返回JSON格式，包含以下字段：
        - title: 文章标题
        - content: 正文内容
        - hashtags: 相关话题标签（{platform_settings['hashtag_count']}个）
        - summary: 文章摘要
        - key_points: 关键观点列表
        """
        
        # Prepare request parameters
        request_params = {
            "model": self.env_config.get("OPENAI_MODEL", "gpt-4o"),
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": content_prompt}
            ],
            "temperature": float(self.env_config.get("OPENAI_TEMPERATURE", 0.7))
        }
        
        # Only add max_tokens if it's not -1 (unlimited)
        max_tokens = int(self.env_config.get("OPENAI_MAX_TOKENS", 4000))
        if max_tokens > 0:
            request_params["max_tokens"] = max_tokens
        
        response = await self.openai_client.chat.completions.create(**request_params)
        
        try:
            response_content = response.choices[0].message.content
            logger.info(f"Raw response content: {response_content[:500]}...")  # Log first 500 chars
            
            # Extract JSON from code block if present
            if response_content.startswith("```json"):
                # Find the JSON content between ```json and ```
                start = response_content.find("```json") + len("```json")
                end = response_content.rfind("```")
                if end > start:
                    response_content = response_content[start:end].strip()
            
            # Clean up the JSON content to handle control characters
            import re
            # Replace problematic characters that might break JSON parsing
            response_content = re.sub(r'[\n\r\t]', ' ', response_content)
            response_content = re.sub(r'\s+', ' ', response_content)  # Normalize whitespace
            
            content_data = json.loads(response_content)
            
            generated_content = GeneratedContent(
                title=content_data["title"],
                content=content_data["content"],
                hashtags=content_data["hashtags"],
                summary=content_data["summary"],
                word_count=len(content_data["content"]),
                sources=[mat.source for mat in materials] + [r.get("source", "") for r in research_results],
                fact_checked=self.env_config.get("ENABLE_FACT_CHECKING", True)
            )
            
            logger.info(f"Content generated successfully: {len(generated_content.content)} characters")
            return generated_content
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse content generation response as JSON: {e}")
            logger.error(f"Response content: {response.choices[0].message.content}")
            raise ValueError("Failed to generate content")
    
    async def review_content(self, content: GeneratedContent) -> Dict[str, Any]:
        """Review generated content for quality and compliance."""
        logger.info("Reviewing generated content")
        
        review_prompt = f"""
        请评估以下文章内容的质量：
        
        标题: {content.title}
        内容: {content.content}
        字数: {content.word_count}
        
        评估维度：
        1. 事实准确性 (1-10分)
        2. 观点独特性 (1-10分)
        3. 逻辑清晰度 (1-10分)
        4. 可读性 (1-10分)
        5. 平台适配性 (1-10分)
        6. 合规安全性 (1-10分)
        7. 法律安全性 (1-10分)
        
        请指出潜在风险，需要改进的地方，并给出总体评分。
        返回JSON格式结果。
        """
        
        response = await self.openai_client.chat.completions.create(
            model=self.env_config.get("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": "你是一位专业的内容评审专家。"},
                {"role": "user", "content": review_prompt}
            ],
            temperature=0.2
        )
        
        try:
            review_result = json.loads(response.choices[0].message.content)
            logger.info(f"Content review completed with score: {review_result.get('total_score', 'N/A')}")
            return review_result
        except json.JSONDecodeError:
            logger.error("Failed to parse review response as JSON")
            return {"error": "Failed to review content"}
    
    async def shutdown(self):
        """Cleanup resources."""
        await self.mcp_client.close()
        logger.info("Columnist agent shutdown completed")