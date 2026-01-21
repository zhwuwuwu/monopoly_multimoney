"""策略层包根：包含 selection / entry / exit / composite 四类子包。

Phase 1: 仅骨架，委托旧 `B1Strategy`；后续迁移逐步移除依赖。
"""

__all__ = [
    "selection",
    "entry",
    "exit",
    "composite",
]
