# 量化交易策略与回测框架（重构版 v2.0）

> 统一使用四层策略架构（选股-入场-退出-执行），支持YAML配置，专注回测与策略实验。

## 核心特性 🚀

- ✅ **四层策略架构**：selection（选股）→ entry（入场）→ exit（退出）→ execution（执行）
- ✅ **统一Factory构建**：所有策略通过factory统一创建，确保完整性
- ✅ **YAML配置支持**：复杂参数通过配置文件管理
- ✅ **预设策略库**：提供6种经过测试的预设策略组合
- ✅ **移除filter入口**：专注于回测和策略实验
- ✅ **完整性验证**：强制检查策略四层是否完整
- ✅ **参数可配置化**：所有策略参数都可通过命令行或YAML灵活调整

## 默认策略配置 📊

**新版默认策略**（`default` preset）：
- **选股层**：沪深300权重Top20（`hs300_top_weight`，可配置top_n）
- **入场层**：日KDJ超卖信号（`b1`，J<13，可配置j_threshold）
- **退出层**：固定持有期（`time`，持有10天，可配置max_holding_days）
- **执行层**：T+1开盘价执行（`next_open`）

**一键回测**：
```bash
python -m framework.cli backtest --preset default --start 2025-01-01 --end 2025-06-30 --plot
```

## 目录结构

```text
quant/
├── configs/              YAML配置文件目录（新增）
│   ├── backtest_basic.yaml
│   ├── backtest_custom.yaml
│   ├── backtest_conservative.yaml
│   ├── backtest_aggressive.yaml
│   └── experiments.yaml
├── framework/            回测引擎 & CLI
│   ├── cli.py           重构版CLI（仅保留backtest/experiments/tests）
│   ├── engine.py
│   ├── backtester.py
│   ├── performance.py
│   └── visualize.py
├── strategies/           四层策略架构
│   ├── selection/       选股层（b1, hs300_top_weight, index_contribute）
│   ├── entry/           入场层（b1, b1_tplus1）
│   ├── exit/            退出层（fixed, time, trailing, advanced）
│   ├── execution/       执行层（close, next_open, tplus1, vwap）
│   └── composite/       组合层
│       ├── factory.py   四层策略工厂（核心）
│       ├── base.py      四层组合基类
│       ├── presets.py   预设策略配置
│       └── registry.py  策略注册器
├── util/                 数据获取（MarketDataHandler）
├── unitest/              单元测试
└── results/              输出结果
```

## 安装与环境

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装PyYAML（新增依赖）
pip install pyyaml
```

## 快速开始 ⚡

### 1. 最简单的方式 - 使用默认策略

```bash
# 使用默认策略运行回测（沪深300 Top20 + 日KDJ + 持有10天 + T+1开盘）
python -m framework.cli backtest \
  --preset default \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot

# 输出结果：
# - 回测指标（收益率、夏普比、最大回撤等）
# - 资金曲线图
# - 交易明细
```

### 2. 调整参数 - 覆盖默认值

```bash
# 修改选股数量：从Top20改为Top30
python -m framework.cli backtest \
  --preset default \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --initial 2000000 \
  --max-positions 8

# 通过YAML配置更复杂的参数
python -m framework.cli backtest \
  --config configs/backtest_custom.yaml \
  --preset default
```

### 3. 列出所有可用策略

### 3. 列出所有可用策略

```bash
python -m framework.cli list-presets
```

**可用预设：**
- `default`: 沪深300权重Top20 + 日KDJ(J<13) + 持有10天 - T+1开盘执行 ⭐推荐
- `b1_tplus1`: B1策略 - T+1开盘执行
- `b1_trailing`: B1策略 - 追踪止损8%
- `b1_advanced`: B1高级策略 - 组合追踪止损和时间退出
- `b1_aggressive`: 激进B1策略 - 放宽选股条件
- `b1_conservative`: 保守B1策略 - 严格选股

### 4. 多策略对比实验

```bash
# 对比默认策略和其他策略的表现
python -m framework.cli experiments \
  --strategies "default,b1_tplus1,b1_trailing,b1_advanced" \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot \
  --export results/comparison

# 使用配置文件
python -m framework.cli experiments --config configs/experiments.yaml
```

### 5. 导出详细结果

```bash
# 导出回测结果（包含交易明细、净值曲线、指标等）
python -m framework.cli backtest \
  --preset default \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --export results/my_backtest \
  --plot

# 导出内容：
# - results/my_backtest/history.csv      # 每日净值数据
# - results/my_backtest/trades.csv       # 交易明细
# - results/my_backtest/metrics.csv      # 绩效指标
# - results/my_backtest/strategy_config.json  # 策略配置
# - results/my_backtest/equity.png       # 资金曲线图
```

### 6. 自定义策略参数

```bash
# 方式1：命令行直接指定四层策略
python -m framework.cli backtest \
  --selection hs300_top_weight \
  --entry b1 \
  --exit time \
  --execution next_open \
  --start 2025-01-01 \
  --end 2025-06-30

# 方式2：使用YAML配置文件（推荐用于复杂参数）
# 见下文"YAML配置文件详解"章节
```

### 7. 运行单元测试

```bash
python -m framework.cli tests
```

## 四层策略架构详解 🏗️

每个完整策略由四层组成，缺一不可：

### 架构图示

```
┌─────────────────────────────────────────────────────────────┐
│                       回测引擎                                │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  第一层：Selection（选股层）- 从市场中筛选候选股票池          │
│  输入：市场所有股票数据                                       │
│  输出：候选股票列表 ['600519', '601318', ...]               │
│  常用策略：b1, hs300_top_weight, index_contribute            │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  第二层：Entry（入场层）- 对候选股票生成具体买入信号          │
│  输入：单只股票的历史数据                                     │
│  输出：买入信号 [{symbol, date, price, stop_loss, ...}]      │
│  常用策略：b1 (KDJ超卖), b1_tplus1                           │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  第三层：Exit（退出层）- 判断持仓何时退出                     │
│  输入：持仓信息 + 当前价格                                    │
│  输出：是否退出 + 退出原因 (止损/止盈/时间到期/追踪止损)      │
│  常用策略：fixed, time, trailing, advanced                   │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│  第四层：Execution（执行层）- 决定如何执行买卖指令            │
│  输入：交易信号                                              │
│  输出：实际成交价格和时间                                     │
│  常用模式：close（当日收盘）, next_open（次日开盘/T+1）       │
└─────────────────────────────────────────────────────────────┘
```

### 各层策略列表

| 层级 | 注册名称 | 作用说明 | 关键参数 |
|------|---------|---------|---------|
| **selection** | `b1` | B1技术选股（KDJ+形态+均线） | `j_threshold`, `ma_window` |
| | `hs300_top_weight` | 沪深300权重Top N ⭐ | `top_n`(默认20), `index_code` |
| | `index_contribute` | 通用指数/行业权重选股 | `index_code`, `top_n` |
| **entry** | `b1` | 日KDJ超卖信号 ⭐ | `j_threshold`(默认13) |
| | `b1_tplus1` | B1入场+T+1执行 | 同上 |
| **exit** | `fixed` | 固定止损止盈 | `stop_loss`, `target_price` |
| | `time` | 固定持有期 ⭐ | `max_holding_days`(默认10) |
| | `trailing` | 追踪止损 | `trailing_pct` |
| | `advanced` | 组合退出（止损+追踪+时间） | 多种参数组合 |
| **execution** | `close` | 当日收盘价执行 | 无 |
| | `next_open` / `tplus1` | 次日开盘价执行（T+1）⭐ | 无 |
| | `vwap` | VWAP近似执行 | 无 |

⭐ 标记表示默认策略使用的组件

### 策略构建方式对比

#### 方式1：使用预设（推荐新手）⭐

```bash
# 最简单，使用经过测试的策略组合
python -m framework.cli backtest \
  --preset default \
  --start 2025-01-01 \
  --end 2025-06-30
```

**优点**：开箱即用，参数已优化  
**适用**：快速验证、初学者

#### 方式2：YAML配置（推荐生产环境）⭐⭐

```yaml
# configs/my_strategy.yaml
backtest:
  start: "2025-01-01"
  end: "2025-06-30"
  
  strategy:
    name: "hs300_kdj_time"
    selection: "hs300_top_weight"
    selection_params:
      top_n: 30              # 选择权重Top30
      index_code: "000300"   # 沪深300指数
    
    entry: "b1"
    entry_params:
      j_threshold: 10        # J值小于10时买入
      min_trade_days: 20
    
    exit: "time"
    exit_params:
      max_holding_days: 15   # 持有15天后卖出
    
    execution: "next_open"   # T+1开盘执行
  
  initial: 2000000           # 初始资金200万
  max_positions: 8           # 最多持有8只
  universe: 150              # 股票池150只
  plot: true
  export: "results/my_strategy"
```

```bash
python -m framework.cli backtest --config configs/my_strategy.yaml
```

**优点**：参数清晰、可版本控制、易于分享  
**适用**：正式回测、参数调优、团队协作

#### 方式3：命令行参数（推荐快速测试）

```bash
# 直接在命令行指定四层策略
python -m framework.cli backtest \
  --selection hs300_top_weight \
  --entry b1 \
  --exit time \
  --execution next_open \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --initial 1500000 \
  --max-positions 6
```

**优点**：快速迭代，无需创建配置文件  
**适用**：参数微调、临时测试

#### 方式4：Python代码（推荐高级开发）

```python
from strategies.composite.factory import build_custom_strategy
from framework.engine import BacktestEngine

# 构建自定义策略
strategy = build_custom_strategy(
    selection_name='hs300_top_weight',
    entry_name='b1',
    exit_name='time',
    execution_name='next_open',
    selection_params={'top_n': 25, 'index_code': '000300'},
    entry_params={'j_threshold': 12},
    exit_params={'max_holding_days': 12},
    name='my_custom',
    validate=True  # 验证四层完整性
)

# 使用策略运行回测
engine = BacktestEngine(strategy_name='custom', initial_capital=1_500_000)
results = engine.run(
    start_date='2025-01-01',
    end_date='2025-06-30',
    max_positions=8,
    universe_size=150
)

# 查看结果
print(f"总收益率: {results['metrics']['total_return']:.2%}")
print(f"夏普比率: {results['metrics']['sharpe']:.2f}")
```

**优点**：最大灵活性、可编程、可集成  
**适用**：批量回测、参数优化、自动化系统

## YAML配置文件详解 📝

### 完整配置示例

```yaml
# 回测配置
backtest:
  # === 时间范围 ===
  start: "2025-01-01"
  end: "2025-06-30"
  
  # === 策略配置（四层完整）===
  strategy:
    name: "我的策略"
    
    # 选股层
    selection: "hs300_top_weight"
    selection_params:
      top_n: 20              # 选择权重前20名
      index_code: "000300"   # 沪深300（000016=中证50，000905=中证500）
    
    # 入场层
    entry: "b1"
    entry_params:
      j_threshold: 13        # KDJ的J值阈值（J<13时买入）
      min_trade_days: 20     # 最少交易天数
      stop_loss_pct: 0.12    # 止损比例12%
      take_profit_pct: 0.3   # 止盈比例30%
    
    # 退出层
    exit: "time"
    exit_params:
      max_holding_days: 10   # 最多持有10天
    
    # 执行层
    execution: "next_open"   # T+1开盘价执行（选项：close/next_open/tplus1/vwap）
  
  # === 回测参数 ===
  initial: 1000000           # 初始资金（单位：元）
  max_positions: 5           # 最大持仓数量
  universe: 100              # 股票池规模（从选股结果中取前N只）
  commission: 0.0005         # 单边手续费率（0.05%）
  slippage_bp: 5.0           # 滑点（基点，5bp=0.05%）
  
  # === 输出选项 ===
  plot: true                 # 是否生成净值曲线图
  export: "results/my_test"  # 导出目录
```

### 多策略实验配置

```yaml
# experiments配置
experiments:
  start: "2025-01-01"
  end: "2025-06-30"
  
  # 要对比的策略列表（必须是已注册的预设）
  strategies: "default,b1_tplus1,b1_trailing,b1_advanced"
  
  universe: 100
  max_positions: 5
  plot: true
  export: "results/experiments"
```

### 参数说明表

#### Selection层参数（hs300_top_weight）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `top_n` | int | 20 | 选择权重排名前N的股票 |
| `index_code` | str | "000300" | 指数代码（000300=沪深300，000016=中证50，000905=中证500） |

#### Entry层参数（b1）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `j_threshold` | float | 13 | KDJ指标J值阈值，J<threshold时触发买入信号 |
| `min_trade_days` | int | 20 | 最少交易天数（数据量过少不参与） |
| `stop_loss_pct` | float | 0.12 | 建议止损比例（12%） |
| `take_profit_pct` | float | 0.3 | 建议止盈比例（30%） |
| `big_positive_pct` | float | 0.05 | 大阳线涨幅阈值（5%） |
| `ma_window` | int | 20 | 均线窗口（20日均线） |

#### Exit层参数

**time（时间退出）**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_holding_days` | int | 10 | 最大持有天数 |

**fixed（固定止损止盈）**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `stop_loss` | float | None | 止损价格（绝对值） |
| `target_price` | float | None | 止盈价格（绝对值） |

**trailing（追踪止损）**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `trailing_pct` | float | 0.1 | 追踪止损比例（从最高点回撤10%触发） |

**advanced（组合退出）**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `stop_loss_pct` | float | None | 止损比例 |
| `trailing_pct` | float | None | 追踪止损比例 |
| `target_pct` | float | None | 止盈比例 |
| `max_holding_days` | int | 40 | 最大持有天数 |

#### Execution层（无需参数）

- `close`: 当日收盘价执行
- `next_open` / `tplus1`: 次日开盘价执行（T+1）
- `vwap`: VWAP近似价格执行

### 配置优先级规则 🔄

**优先级从高到低**：命令行参数 > YAML配置 > 预设默认值 > 类DEFAULT_PARAMS

```bash
# YAML中配置了initial=1000000，但命令行指定2000000
python -m framework.cli backtest \
  --config my_config.yaml \
  --initial 2000000        # ✅ 最终使用2000000

# 使用预设，但覆盖某些参数
python -m framework.cli backtest \
  --preset default \        # 预设：default策略
  --start 2025-01-01 \
  --end 2025-06-30 \
  --initial 3000000 \       # ✅ 覆盖初始资金
  --max-positions 10        # ✅ 覆盖持仓数
```

**灵活组合示例**：

```bash
# 场景1：使用YAML配置，但修改时间和资金
python -m framework.cli backtest \
  --config configs/my_strategy.yaml \
  --start 2024-01-01 \      # 覆盖YAML中的start
  --initial 5000000          # 覆盖YAML中的initial

# 场景2：使用预设，但通过YAML微调参数
# 先创建 configs/adjust_default.yaml：
# strategy:
#   selection_params:
#     top_n: 30              # 修改选股数量
#   entry_params:
#     j_threshold: 10        # 修改J阈值

python -m framework.cli backtest \
  --preset default \
  --config configs/adjust_default.yaml \
  --start 2025-01-01 \
  --end 2025-06-30
```

## 预设策略详解 📚

### default - 默认策略（沪深300 + KDJ + 持有10天）⭐

**适用场景**：稳健的指数成分股轮动策略，适合中长期持有

```python
selection: "hs300_top_weight"  # 沪深300权重前20
  └─ top_n: 20
  └─ index_code: "000300"

entry: "b1"                    # 日KDJ超卖信号
  └─ j_threshold: 13           # J<13时买入

exit: "time"                   # 固定持有期
  └─ max_holding_days: 10      # 持有10天

execution: "next_open"         # T+1开盘执行
```

**使用**：
```bash
python -m framework.cli backtest --preset default --start 2025-01-01 --end 2025-06-30
```

---

### b1_tplus1 - B1技术策略（T+1执行）

**适用场景**：技术面选股，T+1执行符合A股实际

```python
selection: "b1"                # B1技术选股（KDJ+形态+均线）
entry: "b1"                    # B1入场信号
exit: "fixed"                  # 固定止损止盈
execution: "next_open"         # T+1开盘执行
```

---

### b1_trailing - 追踪止损策略

**适用场景**：捕捉趋势行情，动态止损保护利润

```python
selection: "b1"
entry: "b1"
exit: "trailing"               # 追踪止损
  └─ trailing_pct: 0.08        # 从最高点回撤8%时退出
execution: "next_open"
```

---

### b1_advanced - 高级组合策略

**适用场景**：多重风控，适合波动市场

```python
selection: "b1"
  └─ j_threshold: -10          # J<-10（更严格）
  └─ big_positive_pct: 0.06

entry: "b1"
  └─ take_profit_pct: 0.25     # 25%止盈

exit: "advanced"               # 组合退出
  └─ trailing_pct: 0.10        # 10%追踪止损
  └─ max_holding_days: 20      # 最多20天

execution: "next_open"
```

---

### b1_aggressive - 激进策略

**适用场景**：高风险高收益，追求快速盈利

```python
selection: "b1"
  └─ j_threshold: -5           # 放宽条件（J<-5）
  └─ big_positive_pct: 0.04    # 降低涨幅要求

entry: "b1"
  └─ take_profit_pct: 0.35     # 35%止盈目标

exit: "trailing"
  └─ trailing_pct: 0.12        # 12%追踪止损（较宽）

execution: "close"             # 当日收盘执行
```

---

### b1_conservative - 保守策略

**适用场景**：稳健投资，严格风控

```python
selection: "b1"
  └─ j_threshold: -15          # 更深度超卖（J<-15）
  └─ big_positive_pct: 0.07    # 更大的阳线
  └─ ma_window: 30             # 30日均线（更长期）

entry: "b1"
  └─ stop_loss_pct: 0.08       # 8%止损
  └─ take_profit_pct: 0.20     # 20%止盈

exit: "fixed"
  └─ stop_loss: 0.08
  └─ target_price_pct: 0.20

execution: "next_open"
```

## CLI命令完整参考 ⌨️

### backtest - 单策略回测

```bash
python -m framework.cli backtest [选项]
```

#### 必选参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--start` | 回测开始日期（YYYY-MM-DD） | `--start 2025-01-01` |
| `--end` | 回测结束日期（YYYY-MM-DD） | `--end 2025-06-30` |

#### 策略选择（三选一）

| 参数 | 说明 | 优先级 |
|------|------|--------|
| `--preset NAME` | 使用预设策略 | 🥇 最高 |
| `--config FILE` | 使用YAML配置文件 | 🥈 中等 |
| `--selection/entry/exit/execution` | 命令行指定四层 | 🥉 基础 |

#### 策略层参数（仅在不使用preset时）

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `--selection` | 选股策略名称 | `b1`, `hs300_top_weight`, `index_contribute` |
| `--entry` | 入场策略名称 | `b1`, `b1_tplus1` |
| `--exit` | 退出策略名称 | `fixed`, `time`, `trailing`, `advanced` |
| `--execution` | 执行模式 | `close`, `next_open`, `tplus1`, `vwap` |
| `--name` | 自定义策略名称 | 任意字符串 |

#### 回测参数（可选）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--initial` | float | 1000000 | 初始资金（元） |
| `--max-positions` | int | 5 | 最大持仓数量 |
| `--universe` | int | 100 | 股票池规模 |
| `--commission` | float | 0.0005 | 单边手续费率（0.05%） |
| `--slippage-bp` | float | 5.0 | 滑点（基点，5bp=0.05%） |

#### 输出选项（可选）

| 参数 | 说明 |
|------|------|
| `--plot` | 生成净值曲线图 |
| `--export DIR` | 导出结果到指定目录（不指定则不导出） |

#### 完整示例

```bash
# 示例1：使用预设，最简单
python -m framework.cli backtest \
  --preset default \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot

# 示例2：使用YAML配置 + 覆盖部分参数
python -m framework.cli backtest \
  --config configs/my_strategy.yaml \
  --initial 2000000 \
  --max-positions 8 \
  --export results/test1

# 示例3：命令行完全自定义
python -m framework.cli backtest \
  --selection hs300_top_weight \
  --entry b1 \
  --exit time \
  --execution next_open \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --name "my_test" \
  --initial 1500000 \
  --max-positions 6 \
  --plot \
  --export results/custom_test
```

---

### experiments - 多策略对比实验

```bash
python -m framework.cli experiments [选项]
```

#### 必选参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--start` | 开始日期 | `--start 2025-01-01` |
| `--end` | 结束日期 | `--end 2025-06-30` |
| `--strategies` | 预设策略列表（逗号分隔） | `--strategies "default,b1_tplus1,b1_trailing"` |

#### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | str | - | YAML配置文件路径 |
| `--universe` | int | 100 | 股票池规模 |
| `--max-positions` | int | 5 | 最大持仓数 |
| `--plot` | - | - | 生成对比曲线图 |
| `--export` | str | - | 导出目录 |

#### 示例

```bash
# 对比多个预设策略
python -m framework.cli experiments \
  --strategies "default,b1_tplus1,b1_trailing,b1_advanced" \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot \
  --export results/comparison

# 使用配置文件
python -m framework.cli experiments \
  --config configs/experiments.yaml
```

---

### list-presets - 列出所有预设策略

```bash
python -m framework.cli list-presets
```

**输出示例**：
```
可用的预设策略:
======================================================================
  default             : 沪深300权重Top20 + 日KDJ(J<13) + 持有10天 - T+1开盘执行
  b1_tplus1           : B1策略 - T+1开盘执行
  b1_trailing         : B1策略 - 追踪止损8%
  b1_advanced         : B1高级策略 - 组合追踪止损和时间退出
  b1_aggressive       : 激进B1策略 - 放宽选股条件
  b1_conservative     : 保守B1策略 - 严格选股
```

---

### tests - 运行单元测试

```bash
python -m framework.cli tests
```

执行所有单元测试（位于 `unitest/` 目录）。

## 回测结果详解 📊

### 输出指标说明

| 指标名称 | 英文 | 计算方式 | 好坏标准 |
|---------|------|---------|---------|
| **总收益率** | total_return | (期末净值 - 期初净值) / 期初净值 | 越高越好 |
| **年化收益率** | cagr | (期末净值/期初净值)^(365/天数) - 1 | 越高越好，>15%优秀 |
| **年化波动率** | volatility | 日收益率标准差 × √252 | 越低越稳定 |
| **夏普比率** | sharpe | (年化收益 - 无风险利率) / 年化波动率 | >1良好，>2优秀，>3卓越 |
| **最大回撤** | max_drawdown | (波谷净值 - 波峰净值) / 波峰净值 | 越小越好，<20%可接受 |
| **盈亏比** | profit_factor | 总盈利 / 总亏损 | >1盈利，>2良好 |
| **胜率** | win_rate | 盈利交易次数 / 总交易次数 | >50%为正，>60%优秀 |
| **总交易次数** | trades_total | 买卖成交次数 | 过多可能过度交易 |
| **平均持仓天数** | avg_holding_days | Σ持仓天数 / 交易次数 | 取决于策略类型 |

### 终端输出示例

```bash
$ python -m framework.cli backtest --preset default --start 2025-01-01 --end 2025-06-30 --plot

======================================================================
回测指标
======================================================================
  total_return            :     18.45%
  cagr                    :     38.23%
  volatility              :      0.2145
  sharpe                  :      1.78
  max_drawdown            :     -8.67%
  profit_factor           :      2.34
  win_rate                :     65.00%
  trades_total            :         20
  avg_holding_days        :      10.5

======================================================================
策略配置
======================================================================
{
  "name": "default",
  "selection": "hs300_top_weight",
  "entry": "b1",
  "exit": "time",
  "execution": "next_open",
  "selection_params": {"top_n": 20},
  "entry_params": {"j_threshold": 13},
  "exit_params": {"max_holding_days": 10}
}

✓ 导出完成: results/my_backtest
```

### 导出文件说明

使用 `--export results/my_backtest` 后，生成以下文件：

```
results/my_backtest/
├── history.csv              # 每日净值曲线数据
├── trades.csv               # 交易明细（买入卖出记录）
├── metrics.csv              # 绩效指标汇总
├── strategy_config.json     # 策略配置信息
└── equity.png               # 净值曲线图（需--plot）
```

#### history.csv 示例

| date | equity | drawdown | daily_return |
|------|--------|----------|--------------|
| 2025-01-02 | 1000000 | 0.00% | 0.00% |
| 2025-01-03 | 1012500 | 0.00% | 1.25% |
| 2025-01-04 | 1008300 | -0.41% | -0.41% |
| ... | ... | ... | ... |

#### trades.csv 示例

| symbol | entry_date | entry_price | exit_date | exit_price | return | holding_days | exit_reason |
|--------|------------|-------------|-----------|------------|--------|--------------|-------------|
| 600519 | 2025-01-03 | 1580.50 | 2025-01-15 | 1689.30 | 6.88% | 10 | time_stop |
| 601318 | 2025-01-05 | 65.80 | 2025-01-17 | 62.40 | -5.17% | 10 | time_stop |
| ... | ... | ... | ... | ... | ... | ... | ... |

## 扩展开发指南 🛠️

### 添加新的选股策略

**步骤1**：创建策略类文件

```python
# strategies/selection/my_selection.py
from __future__ import annotations
from typing import Dict, List, Optional
from .base import StockSelectionStrategy

class MySelection(StockSelectionStrategy):
    name = "my_selection"
    
    DEFAULT_PARAMS = {
        'threshold': 0.05,  # 自定义参数
        'window': 20
    }
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
    
    def select(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        """选股逻辑实现
        
        Args:
            market_data: {symbol: DataFrame(包含OHLCV数据)}
        
        Returns:
            候选股票代码列表
        """
        candidates = []
        threshold = self.params['threshold']
        
        for symbol, df in market_data.items():
            if len(df) < self.params['window']:
                continue
            
            # 实现你的选股逻辑
            if self._my_condition(df, threshold):
                candidates.append(symbol)
        
        return candidates
    
    def _my_condition(self, df, threshold):
        # 具体选股条件
        return df['close'].iloc[-1] > df['close'].iloc[-20] * (1 + threshold)
```

**步骤2**：在注册表中注册

```python
# strategies/selection/registry.py
from .my_selection import MySelection

SELECTION_STRATEGIES = {
    'b1': B1Selection,
    'hs300_top_weight': HS300TopWeightSelection,
    'my_selection': MySelection,  # ✅ 添加新策略
}
```

**步骤3**：使用新策略

```bash
# 命令行使用
python -m framework.cli backtest \
  --selection my_selection \
  --entry b1 \
  --exit time \
  --execution next_open \
  --start 2025-01-01 \
  --end 2025-06-30

# YAML配置
strategy:
  selection: "my_selection"
  selection_params:
    threshold: 0.08
    window: 30
```

---

### 添加新的入场策略

```python
# strategies/entry/my_entry.py
from __future__ import annotations
from typing import Dict, List, Any
import pandas as pd
from .base import EntrySignalStrategy

class MyEntry(EntrySignalStrategy):
    name = "my_entry"
    
    DEFAULT_PARAMS = {
        'signal_threshold': 0.5,
    }
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
    
    def generate(self, symbol: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """生成入场信号
        
        Returns:
            List[{
                'symbol': str,
                'date': datetime,
                'price': float,
                'stop_loss': float,      # 可选
                'target_price': float,   # 可选
            }]
        """
        signals = []
        
        for i in range(len(df)):
            if self._check_entry_condition(df, i):
                signals.append({
                    'symbol': symbol,
                    'date': df.index[i],
                    'price': float(df['close'].iloc[i]),
                    'stop_loss': float(df['close'].iloc[i] * 0.90),
                    'target_price': float(df['close'].iloc[i] * 1.20),
                })
        
        return signals
    
    def _check_entry_condition(self, df, i):
        # 实现入场条件判断
        return True  # 简化示例
```

注册方式同上，在 `strategies/entry/registry.py` 中添加。

---

### 添加新的退出策略

```python
# strategies/exit/my_exit.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from .base import ExitSignalStrategy, ExitDecision

@dataclass
class MyExit(ExitSignalStrategy):
    name: str = "my_exit"
    my_param: float = 0.15
    
    def evaluate(self, position: Dict[str, Any], bar: Dict[str, Any]) -> ExitDecision:
        """评估是否退出
        
        Args:
            position: {
                'symbol': str,
                'entry_date': datetime,
                'entry_price': float,
                'quantity': int,
                ...
            }
            bar: {
                'date': datetime,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': float,
            }
        
        Returns:
            ExitDecision(should_exit, reason, exit_price)
        """
        current_price = float(bar['close'])
        entry_price = position['entry_price']
        pnl_pct = (current_price - entry_price) / entry_price
        
        # 实现退出逻辑
        if pnl_pct >= self.my_param:
            return ExitDecision(True, "profit_target", current_price)
        elif pnl_pct <= -0.10:
            return ExitDecision(True, "stop_loss", current_price)
        
        return ExitDecision(False)  # 继续持有
```

注册在 `strategies/exit/registry.py`。

---

### 添加新的预设策略

编辑 `strategies/composite/presets.py`：

```python
STRATEGY_PRESETS = {
    # ... 现有预设 ...
    
    "my_preset": {
        "selection": "my_selection",
        "entry": "my_entry",
        "exit": "my_exit",
        "execution": "next_open",
        "selection_params": {
            "threshold": 0.08,
            "window": 30
        },
        "entry_params": {
            "signal_threshold": 0.6
        },
        "exit_params": {
            "my_param": 0.20
        },
        "description": "我的自定义预设策略"
    },
}
```

使用：
```bash
python -m framework.cli backtest --preset my_preset --start 2025-01-01 --end 2025-06-30
```

---

### 开发提示 💡

1. **参数命名**：使用 `DEFAULT_PARAMS` 字典定义默认参数
2. **类型提示**：使用Python类型注解提高代码可读性
3. **错误处理**：处理数据不足、缺失值等边界情况
4. **测试先行**：在 `unitest/` 中添加单元测试
5. **文档字符串**：为类和方法添加清晰的文档说明
6. **注册顺序**：先实现 → 后注册 → 再测试

## 常见问题解答 ❓

### Q1: 为什么移除了filter命令？

**A**: 重构后采用四层策略架构，选股（selection）是策略的第一层，应该在完整的回测流程中验证效果。单独的filter命令会导致：
- 选股结果无法验证实际收益
- 脱离入场/退出逻辑，缺乏完整性
- 增加维护成本

建议：使用 `backtest` 命令运行完整策略，通过回测结果验证选股效果。

---

### Q2: 必须提供完整的四层策略吗？

**A**: 是的。四层架构确保了策略的完整性和可追踪性：
- **Selection**: 解决"买什么"
- **Entry**: 解决"何时买"
- **Exit**: 解决"何时卖"
- **Execution**: 解决"如何成交"

缺少任何一层都无法进行完整回测。但您可以：
- 使用预设策略快速开始（`--preset default`）
- 混合使用不同层的策略（如：hs300选股 + b1入场）

---

### Q3: 如何查看可用的策略？

**A**: 查看各层的注册表文件：

```bash
# 查看选股策略
cat strategies/selection/registry.py

# 查看入场策略
cat strategies/entry/registry.py

# 查看退出策略
cat strategies/exit/registry.py

# 查看执行模式
cat strategies/execution/registry.py

# 列出所有预设
python -m framework.cli list-presets
```

---

### Q4: YAML配置和命令行参数冲突怎么办？

**A**: **命令行参数优先级更高**，会覆盖YAML和预设中的配置。

优先级：命令行 > YAML > 预设 > 默认值

```bash
# YAML中设置initial=1000000，命令行覆盖为2000000
python -m framework.cli backtest \
  --config config.yaml \
  --initial 2000000  # ✅ 最终使用2000000
```

---

### Q5: 如何调整默认策略的参数？

**A**: 三种方法：

**方法1**：命令行覆盖（临时调整）
```bash
python -m framework.cli backtest \
  --preset default \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --initial 2000000 \
  --max-positions 10
```

**方法2**：YAML配置（推荐）
```yaml
# configs/my_default.yaml
backtest:
  start: "2025-01-01"
  end: "2025-06-30"
  strategy:
    selection: "hs300_top_weight"
    selection_params:
      top_n: 30  # 修改为Top30
    entry: "b1"
    entry_params:
      j_threshold: 10  # 修改阈值
    exit: "time"
    exit_params:
      max_holding_days: 15  # 修改持有期
    execution: "next_open"
```

**方法3**：修改默认值（永久修改）
- 编辑 `strategies/entry/b1_entry.py` 的 `DEFAULT_PARAMS`
- 编辑 `strategies/exit/advanced_exit.py` 的默认参数
- 编辑 `strategies/composite/presets.py` 的 `default` 配置

---

### Q6: 回测速度慢怎么办？

**A**: 优化建议：

1. **减少股票池规模**：`--universe 50`（默认100）
2. **缩短回测周期**：先用3个月验证，再跑全年
3. **减少持仓数量**：`--max-positions 3`（减少计算）
4. **使用缓存**：MarketDataHandler会缓存已下载的数据
5. **并行实验**：使用 `experiments` 命令对比多策略

---

### Q7: 如何解读回测指标？

**A**: 关键指标评价标准：

| 指标 | 优秀 | 良好 | 一般 | 较差 |
|------|------|------|------|------|
| **CAGR** | >20% | 10-20% | 5-10% | <5% |
| **Sharpe** | >2.0 | 1.5-2.0 | 1.0-1.5 | <1.0 |
| **最大回撤** | <10% | 10-20% | 20-30% | >30% |
| **胜率** | >60% | 50-60% | 40-50% | <40% |
| **盈亏比** | >2.5 | 2.0-2.5 | 1.5-2.0 | <1.5 |

注意：不要只看单一指标，综合评估风险收益比。

---

### Q8: T+1执行和当日收盘执行有什么区别？

**A**: 

| 执行模式 | 说明 | 优势 | 劣势 | 适用 |
|---------|------|------|------|------|
| **close** | 当日收盘价成交 | 快速、无延迟 | 不符合A股规则 | 理论研究 |
| **next_open** | 次日开盘价成交（T+1） | 符合A股实际 | 有隔夜风险 | ⭐实盘推荐 |
| **vwap** | VWAP均价成交 | 更真实 | 计算复杂 | 大资金 |

**建议**：实盘前回测必须使用 `next_open` 或 `tplus1` 模式。

---

### Q9: 策略回测效果很好，但实盘亏损怎么办？

**A**: 常见原因和避免方法：

1. **过拟合**：参数过度优化导致
   - 避免：使用多时间段验证、样本外测试

2. **滑点和手续费**：回测设置过于理想
   - 避免：设置合理的 `--commission` 和 `--slippage-bp`

3. **流动性问题**：回测未考虑成交量
   - 避免：增加成交量过滤条件

4. **市场环境变化**：历史规律失效
   - 避免：定期重新回测和调整策略

5. **心理因素**：实盘情绪影响执行
   - 避免：严格按策略执行，设置自动化

---

### Q10: 如何进行参数优化？

**A**: 推荐使用 `experiments` 命令对比不同参数：

```bash
# 步骤1：创建多个参数变体预设（在presets.py中）
"test_j10": {
    "selection": "hs300_top_weight",
    "entry": "b1",
    "entry_params": {"j_threshold": 10},  # 测试j=10
    ...
},
"test_j13": {
    "entry_params": {"j_threshold": 13},  # 测试j=13
    ...
},
"test_j15": {
    "entry_params": {"j_threshold": 15},  # 测试j=15
    ...
}

# 步骤2：运行对比实验
python -m framework.cli experiments \
  --strategies "test_j10,test_j13,test_j15" \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot \
  --export results/param_optimization

# 步骤3：分析结果，选择最优参数
```

**警告**：避免过度优化！使用样本外数据验证。

---

### Q11: 数据从哪里获取？

**A**: 框架使用 `akshare` 和 `yfinance` 自动获取数据：
- **A股数据**: akshare（免费、无需API key）
- **美股数据**: yfinance
- **缓存机制**: 数据自动缓存到本地，加快后续回测

无需手动下载数据，首次运行会自动获取。

---

### Q12: 如何贡献代码或报告问题？

**A**: 
- 报告Bug：在GitHub Issues中提交
- 功能建议：通过Pull Request贡献
- 讨论交流：加入项目讨论组

---

需要更多帮助？查看源代码中的文档字符串和示例配置文件！

## 版本历史 📜

### v2.0 (2026-01) - 重大重构

**核心更新**：
- ✅ 重构为四层策略架构（selection-entry-exit-execution）
- ✅ 添加YAML配置支持
- ✅ 统一使用factory构建策略
- ✅ 移除filter命令，专注回测
- ✅ 添加6种预设策略库
- ✅ 强制策略完整性验证
- ✅ 所有参数可配置化

**默认策略变更**：
- 选股：B1技术选股 → 沪深300权重Top20
- 入场：KDJ(J<-10) → KDJ(J<13)
- 退出：固定止损止盈 → 固定持有10天
- 执行：当日收盘 → T+1开盘

**新增功能**：
- 参数优先级系统（命令行 > YAML > 预设 > 默认）
- 策略配置导出（JSON格式）
- 多策略对比实验命令
- 预设策略列表查看
- 详细的CLI帮助文档

**依赖更新**：
- 新增：PyYAML >= 6.0.1

**文档改进**：
- 全新README with完整使用指南
- YAML配置示例
- 参数详细说明
- 常见问题解答

---

### v1.0 (2025-12) - 初始版本

- 基础三层策略架构（选股-入场-退出）
- B1技术策略实现
- 基础回测引擎
- 简单命令行接口

---

## 未来规划 🚀

### v2.1 计划
- [ ] 添加更多指数选股策略（中证500、科创50等）
- [ ] 增加周级别KDJ入场策略
- [ ] 支持多因子选股
- [ ] 增加风险管理模块（组合级别止损）
- [ ] 优化数据缓存机制

### v3.0 规划
- [ ] 实时监控模式
- [ ] 策略自动优化（网格搜索/贝叶斯优化）
- [ ] Web UI界面
- [ ] 回测结果数据库存储
- [ ] 支持期货/期权回测

欢迎提交Issue和Pull Request参与开发！

## 免责声明

本项目仅供学习与研究，不构成投资建议。实盘前请充分测试并自担风险。

## License

Apache-2.0
