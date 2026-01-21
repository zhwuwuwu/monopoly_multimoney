"""
Writer Agent using OpenAI client.
"""

import json
import re
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import AsyncOpenAI

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Material:
    """Represents source material for content generation."""
    title: str
    content: str
    source: str
    type: str
    reliability_score: float = 0.0


@dataclass
class Article:
    """Represents generated article content."""
    title: str
    content: str
    hashtags: List[str]
    summary: str
    word_count: int
    sources: List[str]


class MCPClient:
    """Simple MCP client for tool calls."""
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url.rstrip("/")
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call MCP tool."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                f"{self.server_url}/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", {})
                else:
                    error_text = await response.text()
                    logger.error(f"MCP tool call failed: {response.status} - {error_text}")
                    return {"error": f"Tool call failed: {response.status}"}
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return {"error": str(e)}


class WriterAgent:
    """Writer Agent for content generation."""
    
    def __init__(self, config: Dict[str, Any], openai_config: Dict[str, str], mcp_config: Dict[str, str]):
        self.config = config
        self.openai_client = AsyncOpenAI(
            api_key=openai_config["api_key"],
            base_url=openai_config["base_url"]
        )
        self.model = openai_config.get("model", "GPT-4o")
        self.temperature = openai_config.get("temperature", 0.7)
        
        # Build system prompt
        self.system_prompt = self._build_system_prompt()
        
        # MCP client
        self.mcp_config = mcp_config
        
        logger.info("Writer Agent initialized successfully")
    
    def _build_system_prompt(self) -> str:
        """Build system prompt from configuration."""
        writer = self.config["writer"]
        
        return writer["system_prompt"].format(
            name=writer["name"],
            persona=writer["persona"],
            core_values="\n".join(f"- {value}" for value in writer["stance"]["core_values"]),
            writing_style="\n".join(f"- {style}" for style in writer["stance"]["writing_style"]),
            expertise_areas="\n".join(f"- {area}" for area in writer["stance"]["expertise_areas"])
        )
    
    async def generate_content(self, materials: List[Material], theme: str, context: str = "", feedback: str = None) -> Article:
        """Generate article content."""
        logger.info(f"Generating content for theme: {theme}")
        
        try:
            # 1. Analyze materials
            analysis = await self._analyze_materials(materials)
            
            # 2. Conduct research using MCP tools
            research_data = await self._conduct_research(theme, analysis.get("keywords", []))
            
            # 3. Generate article
            article = await self._generate_article(materials, analysis, research_data, theme, context, feedback)
            
            return article
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            raise
    
    async def _analyze_materials(self, materials: List[Material]) -> Dict[str, Any]:
        """Analyze provided materials."""
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
        6. 关键词提取（用于进一步研究）
        
        请以JSON格式返回分析结果。
        """
        
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3
        )
        
        return self._parse_json_response(response.choices[0].message.content)
    
    async def _conduct_research(self, theme: str, keywords: List[str]) -> Dict[str, Any]:
        """Conduct research using MCP tools."""
        logger.info(f"Conducting research for theme: {theme}")
        
        research_data = {
            "search_results": [],
            "fact_check_results": {}
        }
        
        async with MCPClient(self.mcp_config["server_url"]) as mcp_client:
            # Web search for additional information
            search_queries = [theme] + keywords[:3]  # Limit queries
            
            for query in search_queries:
                try:
                    search_result = await mcp_client.call_tool("web_search", {
                        "query": query,
                        "max_results": 3
                    })
                    
                    if "error" not in search_result:
                        research_data["search_results"].extend(search_result)
                except Exception as e:
                    logger.error(f"Search failed for query '{query}': {e}")
            
            # Fact checking for key claims
            if research_data["search_results"]:
                key_claims = [result.get("content", "")[:200] for result in research_data["search_results"][:5]]
                try:
                    fact_check_result = await mcp_client.call_tool("fact_check", {
                        "claims": key_claims
                    })
                    
                    if "error" not in fact_check_result:
                        research_data["fact_check_results"] = fact_check_result
                except Exception as e:
                    logger.error(f"Fact checking failed: {e}")
        
        return research_data
    
    async def _generate_article(self, materials: List[Material], analysis: Dict[str, Any], 
                               research_data: Dict[str, Any], theme: str, context: str, feedback: str = None) -> Article:
        """Generate the final article."""
        
        # Build content generation prompt
        content_prompt = f"""
        请基于以下信息生成一篇专栏文章：
        
        主题: {theme}
        额外上下文: {context}
        
        素材分析:
        {json.dumps(analysis, ensure_ascii=False, indent=2)}
        
        研究数据:
        {json.dumps(research_data, ensure_ascii=False, indent=2)}
        
        {'反馈意见: ' + feedback if feedback else ''}
        
        文章要求：
        1. 字数控制在1000-2000字
        2. 体现我的独特观点和立场
        3. 基于事实进行分析
        4. 适合小红书平台的阅读习惯
        5. 结尾要有提问式互动
        6. 包含5-8个相关话题标签
        
        请返回JSON格式，包含以下字段：
        - title: 文章标题
        - content: 正文内容
        - hashtags: 话题标签列表
        - summary: 文章摘要
        - key_points: 关键观点列表
        """
        
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": content_prompt}
            ],
            temperature=self.temperature
        )
        
        content_data = self._parse_json_response(response.choices[0].message.content)
        
        # Create Article object
        article = Article(
            title=content_data.get("title", ""),
            content=content_data.get("content", ""),
            hashtags=content_data.get("hashtags", []),
            summary=content_data.get("summary", ""),
            word_count=len(content_data.get("content", "")),
            sources=[mat.source for mat in materials] + [r.get("source", "") for r in research_data.get("search_results", [])]
        )
        
        logger.info(f"Article generated successfully: {article.word_count} characters")
        return article
    
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
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response_content[:500]}...")
            return {"error": "Failed to parse response"}