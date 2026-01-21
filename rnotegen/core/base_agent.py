"""Base OpenAI agent abstraction shared by writer & reviewer.

Provides:
- Config loading & OpenAI client initialization
- Conversation state (messages) management
- System prompt hook (override build_system_prompt)
- Chat invocation (with optional tools / function calling)
- JSON extraction helper
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import json
import re
from openai import AsyncOpenAI

from utils.config_loader import ConfigLoader
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseOpenAIAgent:
    def __init__(
        self,
        config_path: str = "config",
        model_env_key: str = "OPENAI_MODEL",
        default_model: str = "gpt-4o-mini",
    ):
        self.config_loader = ConfigLoader(config_path)
        self.env_config = self.config_loader.load_env_config()
        self.writer_config = None
        self.column_config = None
        # Optional configs (writer needs them; reviewer may not)
        try:
            self.writer_config = self.config_loader.load_writer_config()
            self.column_config = self.config_loader.load_column_config()
        except Exception:  # noqa: E722 - configs may not exist for certain agents
            pass

        openai_kwargs = {"api_key": self.env_config.get("OPENAI_API_KEY")}
        base_url = self.env_config.get("OPENAI_BASE_URL")
        if base_url:
            openai_kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**openai_kwargs)
        self.model_name = self.env_config.get(model_env_key, default_model)
        self._messages: List[Dict[str, Any]] = []
        self.system_prompt = self.build_system_prompt() or "You are a helpful assistant."
        self.reset_conversation()
        logger.debug(f"{self.__class__.__name__} initialized with model {self.model_name}")

    # ----- Hooks -----
    def build_system_prompt(self) -> str:  # override
        return ""

    # ----- Conversation management -----
    def reset_conversation(self):
        self._messages = [{"role": "system", "content": self.system_prompt}]

    def append(self, role: str, content: str, **extra):
        msg: Dict[str, Any] = {"role": role, "content": content}
        msg.update({k: v for k, v in extra.items() if v is not None})
        self._messages.append(msg)

    # ----- LLM call -----
    async def chat(
        self,
        temperature: float = 0.5,
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Any:
        return await self.client.chat.completions.create(
            model=model or self.model_name,
            messages=self._messages,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice or ("auto" if tools else None),
        )

    # ----- JSON extraction helper -----
    @staticmethod
    def extract_json(text: str, required_keys: Optional[set] = None) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        if text.startswith("```json"):
            start = text.find("```json") + len("```json")
            end = text.rfind("```")
            if end > start:
                text = text[start:end].strip()
        cleaned = re.sub(r'[\n\r\t]', ' ', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                if required_keys is None or (required_keys & set(data.keys())):
                    return data
        except Exception:  # noqa
            return None
        return None

    async def shutdown(self):  # override if needed
        logger.info(f"{self.__class__.__name__} shutdown")
