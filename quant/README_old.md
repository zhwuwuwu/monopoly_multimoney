# 量化交易策略与回测框架（重构版）

> 重构目标：将原始单体脚本拆分为「策略分层 + 组合装配 + 回测引擎 + 指标与可视化」的可扩展架构。旧脚本已由统一 CLI 取代。

## 目录结构

```text
quant/
├── framework/            回测 & 实验 & 指标: backtester / engine / performance / visualize / cli
├── strategies/           策略分层 (selection / entry / exit / composite)
├── util/                 数据获取 (MarketDataHandler, AkShare 包装)
├── unitest/              单元测试（逐步扩展）
├── results/              运行输出（生成）
└── README.md
```

## 核心特性

* SelectionResult：选股结果含 score / reasons，可视化与 CSV 导出。
* Backtester：等权仓位、最大持仓、滑点(基点)、手续费、逐日 MTM。
* Performance：CAGR / Sharpe / 波动率 / 最大回撤 / Profit Factor / Win Rate 等集中计算。
* Engine：统一构建组合策略 & 批量实验。
* CLI：`filter` / `backtest` / `experiments` / `tests` 一站式。
* 模块解耦：Selection 与 Entry 分离，便于重用与 A/B。

## 安装与环境

```bash
pip install -r requirements.txt
```

仅核心逻辑可不安装 matplotlib（去掉可视化）。

## 快速开始

### 1. 运行选股 (filter)

```bash
python -m framework.cli filter --date 2025-08-01 --strategy default --stock_pool hs300 --details --plot
```

参数：
 
* --strategy: default | b1+ | volume_surge | loose | weighted
* --details: 打印得分与命中条件
* --plot: 可视化（需 matplotlib）
* --stock_pool: hs300 | zz500 | all_a | main | custom
* --symbols_file: 自定义股票池文件（custom 时）

### 2. 回测 (backtest)

```bash
python -m framework.cli backtest --start 2025-01-01 --end 2025-03-31 \
  --strategy b1 --initial 1000000 --max-positions 5 --universe 80 \
  --commission 0.0005 --slippage-bp 5 --plot --export results/bt_demo
```

生成：history.csv / trades.csv / metrics.csv / equity.png。

### 3. 多策略实验 (experiments)

```bash
python -m framework.cli experiments --start 2025-01-01 --end 2025-06-30 \
  --strategies b1,b1 --universe 60 --max-positions 5 --plot --export results/exp_demo
```

（可在 `strategies/composite/registry.py` 注册更多策略。）

### 4. 单元测试 (tests)

```bash
python -m framework.cli tests
```

## 策略分层与组合装配

| 层 | 作用 | 实现 |
|----|------|------|
| selection | 选股过滤 / 评分 | B1Selection (+ 变体工厂) |
| entry | 入场信号生成 | B1Entry |
| exit | 出场判定 | FixedRiskExit (占位) |
| composite | 装配 selection+entry+exit | B1Composite / B1CompositeStrategy / 自定义组装 |

### 组合策略装配方式

当前支持三种装配途径：

1. 快捷 B1：`--strategy b1`  （内部根据参数选择 T+1 或当日收盘、不同退出策略）
2. 自定义层组合：`--strategy custom` + 显式指定 `--selection / --entry / --exit` 与各层参数
3. 代码内直接调用工厂或类：`build_custom_strategy()` / `B1CompositeStrategy()` / `CompositeStrategy.from_names()`

#### 1) B1 快捷策略可选参数
通过 backtest CLI：

| 参数 | 说明 | 示例 |
|------|------|------|
| --entry-execution | 入场执行模式：`same_close` 当日收盘 / `t+1` 次日开盘 | `--entry-execution t+1` |
| --exit-type | 退出类型：fixed / time / trailing / advanced | `--exit-type trailing` |
| --exit-arg k=v | 退出参数：可多次传入 | `--exit-arg trailing_pct=0.08` |

示例：
```bash
python -m framework.cli backtest --start 2025-01-01 --end 2025-03-31 \
  --strategy b1 --entry-execution t+1 --exit-type advanced \
  --exit-arg trailing_pct=0.1 --exit-arg max_holding_days=40
```

#### 2) 自定义层组合（strategy=custom）

可自由拼装不同选股、入场、退出：

| CLI 参数 | 说明 | 示例 |
|----------|------|------|
| --selection | 选股策略名称（注册于 selection.registry） | `--selection b1` |
| --entry | 入场策略名称（entry.registry） | `--entry b1_tplus1` |
| --exit | 退出策略名称（exit.registry） | `--exit trailing` |
| --selection-param k=v | 选股层参数（可多次） | `--selection-param j_threshold=-5` |
| --entry-param k=v | 入场层参数（可多次） | `--entry-param take_profit_pct=0.25` |
| --exit-param k=v | 退出层参数（可多次） | `--exit-param trailing_pct=0.07` |
| --name | 自定义策略名（默认 customized_strategy） | `--name my_mix` |

示例：
```bash
python -m framework.cli backtest --start 2025-01-01 --end 2025-04-01 \
  --strategy custom \
  --selection b1 --selection-param j_threshold=-8 \
  --entry b1_tplus1 --entry-param take_profit_pct=0.28 \
  --exit advanced --exit-param trailing_pct=0.09 --exit-param max_holding_days=35 \
  --name my_custom_v1 --plot
```

#### 3) 代码内装配示例
```python
from strategies.composite import build_custom_strategy, B1CompositeStrategy

# 自定义层组合
mix = build_custom_strategy(selection_name='b1', entry_name='b1_tplus1', exit_name='trailing',
                            entry_params={'take_profit_pct': 0.25}, exit_params={'trailing_pct': 0.08},
                            name='mix_trailing')

# B1 专用类（默认 T+1）
b1_adv = B1CompositeStrategy(entry_execution='t+1', exit_type='advanced', exit_args={'trailing_pct': 0.12})
```

### 策略配置输出

回测结果中新增 `strategy_config.json`（或控制台打印）示例：

```json
{
  "selection": {"name": "B1Selection", "params": {"j_threshold": -10, "ma_window": 20, ...}},
  "entry": {"name": "b1_entry_tplus1", "params": {"take_profit_pct": 0.3, ...}},
  "exit": {"name": "trailing_exit", "params": {"trailing_pct": 0.08}},
  "composite_name": "customized_strategy"
}
```

便于：
* 复现实验（参数留痕）
* 多实验对比（自动聚合差异）
* 与交易日志/监控系统对接

扩展：实现新类 → 在 registry 注册 → CLI 调用。

## 回测执行顺序

1. 处理退出 (evaluate_exit)
2. 生成入场 (generate_entries)
3. 应用滑点/手续费，更新现金与仓位
4. Mark-To-Market 记录权益

## 指标说明

| 指标 | 说明 |
|------|------|
| total_return | 总收益率 |
| cagr | 年化复合增长率 |
| volatility | 年化波动率 (日收益 std * √252) |
| sharpe | 简化夏普（未扣无风险利率） |
| max_drawdown | 最大回撤 |
| profit_factor | 毛盈利 / 绝对值毛亏损 |
| win_rate | 盈利平仓数 / 平仓数 |
| avg_gain / avg_loss | 平均单笔盈亏 |
| avg_holding_days | 平均持仓天数 |
| net_profit | 已平仓净收益合计 |

计划：Sortino / Calmar / Turnover / Rolling 指标。

## B1 策略详解

### 1. Selection 选股条件

B1Selection 在最后一个交易日 (最新 K 线) 对启用的条件进行一次性评估，逻辑由 `logic`（AND / OR）决定是否全部满足或任一满足：

| 条件键 | 说明 | 默认启用 | 判定逻辑摘要 |
|--------|------|----------|--------------|
| kdj_condition | KDJ 中 J 低位（超卖区） | 是 | `J < j_threshold` |
| bottom_pattern_condition | 底部分型/三连结构弱势 | 是 | 当日 low 与 high 同时低于前两日对应值 |
| big_positive_condition | 当日大阳线确认 | 是 | `close > open * (1 + big_positive_pct)` |
| above_ma_condition | 价格重新站上短期均线 | 是 | `close > MA(close, ma_window)` |
| volume_surge_condition | 放量确认 | 否 | 当日成交量 > 近5日均量 * volume_ratio |
| volume_shrink_condition | 缩量企稳（可用于博弈） | 否 | 当日成交量 < 近5日均量 / volume_ratio |
| macd_golden_cross | MACD 金叉 (占位) | 否 | `MACD` 前值 < 0 且当前 > 0 |

打分方式：得分 = 命中条件数 / 启用条件数；用于排序/可视化。

### 2. Entry 入场逻辑 (B1Entry)

Entry 目前复用核心四个约束（KDJ 低位 + 底部分型 + 大阳线 + 均线站上），全部满足才生成 1 条当日入场信号：

生成字段：

* price: 当日收盘价
* stop_loss: 参考前一根 K 线 low * (1 - stop_loss_pct)
* target_price: 收盘价 * (1 + take_profit_pct)
* meta: `{"source": "b1_entry_independent"}`

### 3. Exit 出场逻辑 (FixedRiskExit)

简化：若价格 <= stop_loss → "stop_loss"；若价格 >= target_price → "take_profit"；否则持有。

### 4. 关键参数（默认值）

来自 `B1Selection.DEFAULT_PARAMS` 与 `B1Entry.DEFAULT_PARAMS`：

| 参数 | 默认 | 作用 | 影响模块 |
|------|------|------|----------|
| kdj_threshold | 10 (保留, 当前逻辑主要用 j_threshold) | （可扩展）备用阈值 | Selection |
| j_threshold | -10 /  Entry 用 -10 | J 低位判定（越低越激进） | Selection / Entry |
| min_trade_days | 20 | 数据长度过滤（不足不评估） | Selection / Entry |
| ma_window | 20 | 均线窗口 | Selection / Entry |
| volume_ratio | 2.0 | 放量/缩量倍数 | Selection |
| big_positive_pct | 0.05 | 大阳线收盘幅度阈值 | Selection / Entry |
| stop_loss_pct | 0.12 | 止损距离（相对于前一日 low） | Entry |
| take_profit_pct | 0.3 | 固定止盈目标 | Entry |

可通过变体工厂 `build_b1_selection_variant(name)` 切换启用集合与逻辑模式：

| 变体 | 逻辑 | 调整点 | 用途倾向 |
|------|------|--------|----------|
| default | AND | 基础四条件 | 均衡筛选 |
| b1+ | AND | 加强底部+大阳线+均线 | 更严格质量 |
| volume_surge | AND | 增加放量条件 | 动量确认 |
| loose | OR | j_threshold 放宽为 -5 | 更宽松探索/扩大覆盖 |
| weighted (暂退化为 AND) | AND | 启用更多条件 | 后续用于加权模型占位 |

### 5. 风险 / 缺陷提示

* 依赖末日单点判断，未对信号连续性/稳定性做统计过滤。
* 未考虑停牌、ST、涨跌停价及流动性过滤（可在 DataHandler 层扩展）。
* 盈亏比/止盈止损为固定百分比，未融入波动度 (ATR) / 自适应模型。
* Survivorship Bias：默认使用当前指数成分历史筛选，需后续实现“成分随时间”的数据源以降低偏差。

## CLI 参数说明

### filter 子命令

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| --date | 是 | - | 查询日期 (YYYY-MM-DD) 必须存在于数据索引中 |
| --strategy | 否 | default | B1 变体名称（见上表） |
| --stock_pool | 否 | hs300 | hs300 / zz500 / all_a / main / custom |
| --symbols_file | custom 时 | 无 | 自定义股票列表文件路径（每行代码） |
| --stock_count | 否 | -1 | 限制截取前 N 只（-1 表示全部） |
| --details | 否 | False | 输出得分与命中详情 |
| --plot | 否 | False | 可视化条形图（需 matplotlib） |
| --no_save | 否 | False | 不写出 CSV |
| --encoding | 否 | utf-8 | 自定义股票文件编码尝试顺序首选 |
| --quiet | 否 | False | 减少日志输出 |

输出：`results/b1_filtered_YYYYMMDD_<strategy>.csv`

### backtest 子命令

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| --start | 是 | - | 开始日期 YYYY-MM-DD |
| --end | 是 | - | 结束日期 YYYY-MM-DD |
| --strategy | 否 | b1 | 组合策略注册名（当前仅 b1） |
| --initial | 否 | 1_000_000 | 初始资金 |
| --max-positions | 否 | 5 | 最大并发持仓数 |
| --universe | 否 | 100 | 股票池截取规模（从 HS300 成分前 N 只） |
| --commission | 否 | 0.0005 | 单边手续费率 |
| --slippage-bp | 否 | 5.0 | 滑点（基点，1bp = 0.01%） 买入加价/卖出减价 |
| --plot | 否 | False | 输出资金曲线图 |
| --export | 否 | (None) | 指定目录导出 history/trades/metrics/equity.png |

### experiments 子命令

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| --start / --end | 是 | - | 时间区间 |
| --strategies | 是 | - | 逗号分隔策略名列表（例如 b1,b1） |
| --universe | 否 | 100 | 每个实验使用的股票池规模 |
| --max-positions | 否 | 5 | 持仓上限 |
| --plot | 否 | False | 比较资金曲线绘图 |
| --export | 否 | (None) | 导出各实验 history_*.csv / trades_*.csv 等 |

### tests 子命令

无参数，执行 `unitest/run_tests.py`（后续可迁移至 pytest）。

### 退出 / 成本相关内部公式

* 买入成交价 = close * (1 + slippage_bp / 10000)
* 卖出成交价 = close * (1 - slippage_bp / 10000)
* 手续费 = 成交金额 * commission_rate
* 仓位 sizing (默认等权) = `cash / remaining_slots // price`

### 参数调优建议

| 目标 | 优先调参 | 说明 |
|------|----------|------|
| 提高信号数量 | j_threshold 上调 (更接近 0) / 使用 loose | 放宽超卖判定与逻辑模式 |
| 筛选更严格 | 启用 volume_surge 或 b1+ | 要求更多确认条件 |
| 降低回撤 | 减小 max_positions / 增大 stop_loss_pct 保守 or 降低 take_profit_pct | 控制单笔风险与集中度 |
| 提高胜率 | 加入放量确认 / 增加 MA 窗口 | 牺牲覆盖换取质量 |

## Roadmap

* [ ] 多 Exit 规则（跟踪 / 时间 / ATR）
* [ ] CLI 动态参数：`--param k=v` 解析
* [ ] 并行 / 多进程实验
* [ ] 报告生成 (Markdown / HTML)
* [ ] 更全面单测（portfolio / sizing / edge cases）
* [ ] 动态历史股票池（降低幸存者偏差）
* [ ] 数据本地缓存策略

## FAQ

| 问题 | 可能原因 | 解决 |
|------|----------|------|
| 无选股结果 | 日期非交易日/条件过严 | 放宽条件或调整日期 |
| 无交易 | Entry 未触发 / 股票池过小 | 放宽触发条件或扩大池 |
| 可视化失败 | 未安装 matplotlib | 安装或移除 --plot |
| 拉取数据失败 | 网络 / 源接口不稳定 | 重试或实现本地缓存 |

## 扩展步骤（新增策略示例）

1. 在对应分层包实现新类（如 `strategies/selection/my_selection.py`）。
2. 在 `composite/registry.py` 注册构建函数。
3. （可选）添加可视化 / 详情输出接口。
4. 为关键逻辑补单元测试。
5. 更新 README Roadmap / 使用示例。

## 免责声明

本项目仅供学习与研究，不构成投资建议。实盘前请充分测试并自担风险。

## License

Apache-2.0

---

（文档最后更新：重构版精简整合）
