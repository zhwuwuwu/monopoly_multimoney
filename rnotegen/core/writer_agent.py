"""WriterAgent (function-calling orchestration)

目标：使用 OpenAI function calling，仅保留 Writer / Reviewer 两个 agent；材料分析与深度检索作为工具函数暴露给 LLM。

策略：
1. 构建 system prompt，明确可用工具、输出 JSON Schema。
2. 启动对话：用户提供 theme + materials 摘要。
3. 循环：
     - 如果模型请求 tool -> 本地执行 -> 结果追加到 messages -> 继续。
     - 若模型直接给出最终文章 JSON -> 结束。
4. 失败/解析回退：提供最多 N 次重试。

输出结构（要求模型遵守）：
{
    "title": str,
    "content": str,
    "hashtags": [str],
    "summary": str
}
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import json
import re
from utils.logger import get_logger
from .models import Material, GeneratedContent
from . import tools as tool_module
from .base_agent import BaseOpenAIAgent

logger = get_logger(__name__)


class WriterAgent(BaseOpenAIAgent):
    """WriterAgent using function calling tools (analyze_materials, deep_research)."""

    def __init__(self, config_path: str = "config"):
        super().__init__(config_path=config_path)
        logger.info("WriterAgent initialized")

    def build_system_prompt(self) -> str:  # override hook
        if not self.writer_config:
            return "You are a writing assistant."
        writer = self.writer_config["writer"]
        return writer["system_prompt"].format(
            name=writer["name"],
            persona=writer["persona"],
            core_values="\n".join(f"- {v}" for v in writer["stance"]["core_values"]),
            writing_style="\n".join(f"- {s}" for s in writer["stance"]["writing_style"]),
            expertise_areas="\n".join(f"- {a}" for a in writer["stance"]["expertise_areas"]),
        )

    def _article_user_message(self, theme: str, materials: List[Material], additional_context: str) -> str:
        mats_brief = []
        for m in materials[:12]:
            mats_brief.append(f"标题:{m.title}\n来源:{m.source}\n类型:{m.type}\n内容片段:{m.content[:260]}")
        return (
            "任务: 根据给定主题与素材, 你可以调用工具进行分析与检索。完成后输出最终文章 JSON。\n"
            f"主题: {theme}\n"
            f"附加上下文: {additional_context[:400]}\n"
            "输出 JSON schema: {title:str, content:str, hashtags:list[str](<=6), summary:str}.\n"
            "需要遵守: 内容真实, 标注观点, 语言清晰, 不虚构来源。\n"
            "素材摘要:\n" + "\n---\n".join(mats_brief)
        )

    async def _call_llm(self, model: Optional[str], temperature: float, tools: list) -> Any:
        return await self.client.chat.completions.create(
            model=model or self.env_config.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=self._messages, temperature=temperature, tools=tools, tool_choice="auto"
        )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        if text.startswith("```json"):
            start = text.find("```json") + len("```json")
            end = text.rfind("```")
            text = text[start:end].strip() if end > start else text
        cleaned = re.sub(r'[\n\r\t]', ' ', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and {"title","content","summary"} & set(data.keys()):
                return data
        except json.JSONDecodeError:
            return None
        return None

    async def generate(self, theme: str, materials: List[Material], additional_context: str = "") -> GeneratedContent:
        # 初始化 messages
        self.reset_conversation()
        self.append("user", self._article_user_message(theme, materials, additional_context))

        tools_spec = tool_module.get_tool_specs()
        max_rounds = 12
        article_json: Optional[Dict[str, Any]] = None

        for round_i in range(max_rounds):
            resp = await self.chat(temperature=0.4, tools=tools_spec)
            msg = resp.choices[0].message
            tool_calls = getattr(msg, 'tool_calls', None)
            if tool_calls:
                # 处理第一批工具调用（按需可改为并行）
                for tc in tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments or '{}')
                    except json.JSONDecodeError:
                        fn_args = {}
                    impl = tool_module.TOOL_FUNCTIONS.get(fn_name)
                    if not impl:
                        tool_result = {"error": f"unknown tool {fn_name}"}
                    else:
                        try:
                            tool_result = impl(**fn_args)
                        except Exception as e:  # noqa
                            tool_result = {"error": str(e)}
                    self.append("tool", json.dumps(tool_result, ensure_ascii=False)[:8000], tool_call_id=tc.id, name=fn_name)
                continue  # 下一轮
            # 没有工具调用 -> 尝试解析文章
            content_text = msg.content or ""
            maybe_json = self.extract_json(content_text, required_keys={"title", "content", "summary"})
            if maybe_json:
                article_json = maybe_json
                break
            else:
                self.append("user", "请输出最终 JSON (title, content, hashtags, summary)")

        if not article_json:
            logger.warning("WriterAgent: 未成功获取结构化 JSON，返回占位")
            article_json = {"title": theme, "content": "", "hashtags": [], "summary": ""}

        platform_settings = self.column_config["columns"]["default_column"]["platform_settings"].get("xiaohongshu", {})
        hashtags = article_json.get("hashtags", [])
        if isinstance(hashtags, list):
            hashtags = hashtags[: platform_settings.get("hashtag_count", 5)]
        else:
            hashtags = []

        generated = GeneratedContent(
            title=article_json.get("title", theme),
            content=article_json.get("content", ""),
            hashtags=hashtags,
            summary=article_json.get("summary", ""),
            word_count=len(article_json.get("content", "")),
            sources=[m.source for m in materials],
            fact_checked=self.env_config.get("ENABLE_FACT_CHECKING", True)
        )
        return generated

    async def shutdown(self):  # override for consistency
        await super().shutdown()

