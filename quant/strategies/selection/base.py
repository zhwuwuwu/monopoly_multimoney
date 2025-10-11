from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import pandas as pd

try:  # 可选依赖：若环境缺失 matplotlib，不影响核心逻辑
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore


@dataclass
class SelectionResult:
    """单只股票选股结果详情。

    Attributes:
        symbol: 股票代码
        score: 可选评分/打分（若策略支持打分 / 排序）
        reasons: 满足的条件标签列表
        meta: 额外信息 (例如参数、触发日期、指标值等)
    """
    symbol: str
    score: Optional[float] = None
    reasons: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


class StockSelectionStrategy(ABC):
    """选股策略基类。

    统一接口：
      - select(market_data) -> List[str]  仅返回股票代码（向后兼容简单用法）
      - select_with_details(market_data) -> List[SelectionResult]  返回结构化信息
      - visualize(results)  简单条形图 / 表格输出
      - export(results, path)  导出 CSV
    """

    name: str = "base_selection"

    # ---- 核心抽象方法 ----
    @abstractmethod
    def select(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:  # pragma: no cover
        """最小接口：返回选中的股票代码列表。"""
        raise NotImplementedError

    # ---- 可覆盖的扩展：提供带详情结果 ----
    def select_with_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:
        """默认使用 select 包装成 SelectionResult 列表。

        子类若能提供更丰富的理由 / 打分，可重写本方法。
        """
        symbols = self.select(market_data)
        return [SelectionResult(symbol=s) for s in symbols]

    # ---- 可视化 / 导出辅助 ----
    def visualize(self, results: List[SelectionResult], top_n: int | None = None, save_path: str | None = None):  # pragma: no cover
        """可视化选股结果。

        逻辑：
          - 若存在 score 字段，用 score 排序并画条形图
          - 否则按照字母排序，仅展示数量条形图 (统一高度)
        """
        if not results:
            print("[visualize] 无选股结果。")
            return
        # 排序
        sortable = [r for r in results if r.score is not None]
        if sortable:
            ordered = sorted(results, key=lambda r: (r.score if r.score is not None else float('-inf')), reverse=True)
        else:
            ordered = sorted(results, key=lambda r: r.symbol)
        if top_n is not None:
            ordered = ordered[:top_n]

        # 控制台简表
        print(f"选股结果（展示 {len(ordered)}/{len(results)}）:")
        print(f"{'序号':<4} {'代码':<12} {'Score':<8} Reasons")
        for idx, r in enumerate(ordered, 1):
            score_str = f"{r.score:.3f}" if r.score is not None else "-"
            print(f"{idx:<4} {r.symbol:<12} {score_str:<8} {','.join(r.reasons) if r.reasons else ''}")

        if plt is None:
            print("[visualize] matplotlib 不可用，跳过图形输出。")
            return

        # 构建图形数据
        labels = [r.symbol for r in ordered]
        if sortable:
            values = [r.score if r.score is not None else 0 for r in ordered]
            title = f"{self.name} 选股得分前 {len(ordered)}"
            ylabel = 'Score'
        else:
            values = [1 for _ in ordered]
            title = f"{self.name} 选股结果示意 (无评分)"
            ylabel = 'Selected'

        fig, ax = plt.subplots(figsize=(max(8, len(labels)*0.5), 6))
        ax.bar(labels, values, color='#3A84F7')
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel('Symbol')
        ax.grid(True, linestyle='--', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[visualize] 图表已保存: {save_path}")
        else:
            plt.show()

    def export(self, results: List[SelectionResult], csv_path: str):  # pragma: no cover
        if not results:
            print("[export] 无结果，跳过导出。")
            return
        import csv
        from pathlib import Path
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'score', 'reasons'])
            for r in results:
                writer.writerow([r.symbol, '' if r.score is None else r.score, '|'.join(r.reasons)])
        print(f"[export] 结果已导出: {csv_path}")

__all__ = [
    'SelectionResult',
    'StockSelectionStrategy',
]
