"""Local tool functions used via OpenAI function calling for WriterAgent.

These are intentionally lightweight, deterministic helpers so that the LLM can
request structured analyses (材料分析 / 深度检索) without自身重复耗费 token。

You can later replace internals with real NLP / 向量检索 / 外部API 调用，而无需修改
WriterAgent 逻辑，只需保持函数签名 & 返回结构一致。
"""
from __future__ import annotations

from typing import List, Dict, Any
import math
import re
from collections import Counter


def _tokenize(text: str) -> List[str]:
    # 简单分词：按非字母数字中文字符拆分
    return [t for t in re.split(r"[^0-9A-Za-z\u4e00-\u9fa5]+", text.lower()) if t and len(t) > 1]


def analyze_materials(materials: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析素材，返回结构化要素。

    Returns dict with keys: facts, perspectives, trends, controversies, potential_angles.
    当前实现为启发式/占位：
    - facts: 取每条材料前 1 句。
    - perspectives: 基于 type/source 去重的视角描述。
    - trends: 高频关键词 (简单词频) Top-N。
    - controversies: 关键词中包含 risk/争议/风险 的句子占位。
    - potential_angles: 结合关键词 + materials 元数据合成的潜在写作角度。
    """
    facts = []
    perspectives = set()
    all_tokens: Counter = Counter()
    controversies = []

    for m in materials:
        content = m.get("content", "")
        first_sentence = re.split(r"[\n。.!?]", content)[:1]
        if first_sentence:
            facts.append(first_sentence[0][:160])
        perspectives.add(f"来源:{m.get('source','?')} 类型:{m.get('type','?')}")
        toks = _tokenize(content)[:800]  # 限制长度
        all_tokens.update(toks)
        if re.search(r"风险|risk|争议|controvers|legal", content, re.I):
            controversies.append(content[:180])

    # 去除停用词（极简)
    stop = {"the","and","with","this","that","from","have","has","were","been","will","would","about","there","their","which","对于","以及","并且","可以","我们"}
    freq = [w for w,_ in all_tokens.most_common(120) if w not in stop and not w.isdigit()]
    trends = freq[:15]

    potential_angles = []
    for t in trends[:6]:
        potential_angles.append(f"围绕 {t} 的发展与影响")
    if not potential_angles:
        potential_angles.append("综合材料的宏观视角分析")

    return {
        "facts": facts,
        "perspectives": list(perspectives),
        "trends": trends,
        "controversies": controversies[:5],
        "potential_angles": potential_angles[:8],
    }


def deep_research(theme: str, queries: List[str]) -> List[Dict[str, Any]]:
    """模拟深度检索 (占位实现)。

    真实环境可接入：
    - 向量数据库 (FAISS / Chroma)
    - Web 搜索 / 自有知识库
    - 财经/行业数据 API
    当前返回结构：[{query, key_points, risks?}]
    """
    dedup_q = []
    seen = set()
    for q in queries:
        qn = q.strip()
        if qn and qn.lower() not in seen:
            dedup_q.append(qn)
            seen.add(qn.lower())

    results = []
    base_points = ["市场现状", "驱动因素", "增长瓶颈", "竞争格局", "未来展望"]
    for q in dedup_q[:8]:
        # 轻度扰动以展示非静态
        rot = (abs(hash(q)) % len(base_points)) or 0
        sel = base_points[rot:] + base_points[:rot]
        results.append({
            "query": q,
            "key_points": sel[:3],
            "risks": ["监管不确定性", "技术替代", "宏观波动"][: (rot % 3) + 1]
        })
    return results


TOOL_FUNCTIONS = {
    "analyze_materials": analyze_materials,
    "deep_research": deep_research,
}


def get_tool_specs() -> list:
    """Return OpenAI function calling tool specs."""
    return [
        {
            "type": "function",
            "function": {
                "name": "analyze_materials",
                "description": "分析素材，提取 facts, perspectives, trends, controversies, potential_angles。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "materials": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "source": {"type": "string"},
                                    "type": {"type": "string"}
                                },
                                "required": ["title","content","source","type"],
                            }
                        }
                    },
                    "required": ["materials"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "deep_research",
                "description": "对主题补充检索，返回每个查询的 key_points 与 risks。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string"},
                        "queries": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["theme","queries"],
                },
            },
        },
    ]
