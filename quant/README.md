# 量化交易策略测试框架

这是一个用于测试和评估B1量化交易策略的框架。该框架允许用户测试不同的策略变体，筛选特定日期的交易信号，并评估策略在不同参数和条件下的表现。

## 目录结构

```
quant/
├── b1_strategy.py           # B1策略实现类，包含各种条件和信号生成逻辑
├── util/market_data_handler.py   # 市场数据处理模块，负责股票数据获取和指标计算
├── test_strategy_variations.py   # 测试不同策略变体的工具
├── get_b1_filtered_stocks.py     # 获取特定日期通过B1策略筛选的股票
├── results/                 # 筛选和测试结果保存目录
└── README.md                # 本说明文档
```

## 系统要求

- Python 3.8+
- 依赖库: pandas, numpy, matplotlib, akshare

安装依赖:
```bash
pip install -r requirements.txt
```

## B1策略介绍

B1策略是一种基于技术分析的股票筛选和交易策略，主要特点包括：

1. 使用KDJ指标识别超卖区域的股票
2. 识别底部形态和大阳线形态
3. 结合均线位置和成交量变化进行确认
4. 支持多种条件组合方式（与逻辑、或逻辑、加权评分）
5. 可配置的参数，如KDJ阈值、量比阈值等

## 实验设置

### 1. 测试不同策略变体 (`test_strategy_variations.py`)

这个脚本用于测试不同B1策略变体的性能，比较它们在相同时间段内产生的信号数量和分布。

#### 输入参数:

```bash
python test_strategy_variations.py [options]

选项:
  --start_date START_DATE    开始日期，格式为 YYYYMMDD (默认: 20250701)
  --end_date END_DATE        结束日期，格式为 YYYYMMDD (默认: 20250801)
  --stock_count STOCK_COUNT  测试股票数量 (默认: 30)
  --stock_pool STOCK_POOL    股票池类型: hs300(沪深300), zz500(中证500), custom(自定义) (默认: hs300)
  --symbols_file SYMBOLS_FILE  自定义股票池文件路径，每行一个股票代码
```

#### 输出:

1. 控制台输出：显示每个策略变体的信号统计信息
   - 总信号数
   - 有信号的股票数量
   - 每只股票平均信号数
   - 最多信号的股票及其信号数量

2. 图表输出：生成比较不同策略变体的柱状图 (`strategy_variations_comparison.png`)
   - 横轴：策略变体名称
   - 纵轴：信号数量和有信号的股票数量

#### 示例:

```bash
python test_strategy_variations.py --start_date 20250701 --end_date 20250801 --stock_count 50 --stock_pool hs300
```

### 2. 获取特定日期的筛选结果 (`get_b1_filtered_stocks.py`)

这个脚本用于查询特定日期通过B1策略筛选的股票列表。

#### 输入参数:

```bash
python get_b1_filtered_stocks.py [options]

选项:
  --date DATE               查询日期，格式为 YYYY-MM-DD (必填)
  --stock_count STOCK_COUNT 测试股票数量 (默认: 300)
  --strategy STRATEGY       策略变体: default, volume_surge, loose, weighted (默认: default)
  --stock_pool STOCK_POOL   股票池类型: hs300, zz500, custom (默认: hs300)
  --symbols_file SYMBOLS_FILE 自定义股票池文件路径，每行一个股票代码
```

#### 输出:

1. 控制台输出：显示通过筛选的股票列表
   - 股票代码
   - 股票名称
   - 当日价格
   - 止损价
   - 目标价
   - 满足条件数

2. CSV文件输出：保存在 `results/` 目录下
   - 文件命名格式：`b1_filtered_stocks_YYYYMMDD_strategy.csv`
   - 包含：股票代码、日期、价格、止损价、目标价、满足的条件列表

#### 示例:

```bash
python get_b1_filtered_stocks.py --date 2025-08-01 --strategy weighted --stock_pool hs300
```

## 策略变体说明

当前支持的策略变体包括：

1. **原始B1策略** (default)
   - 使用与逻辑（AND）组合KDJ、底部形态、大阳线和均线条件
   - 所有条件必须同时满足才会生成信号

2. **B1+放量策略** (volume_surge)
   - 在原始B1策略基础上添加成交量放大条件
   - 使用与逻辑（AND）组合所有条件

3. **宽松条件组合策略** (loose)
   - 使用或逻辑（OR）组合条件
   - 任一条件满足即可生成信号
   - KDJ阈值调整为-5，更宽松

4. **加权组合策略** (weighted)
   - 使用加权评分方式组合条件
   - 不同条件有不同权重，例如KDJ权重为2.0，大阳线权重为1.5
   - 加权得分大于0.7时生成信号

## 自定义股票池

支持三种股票池选择：

1. **沪深300** (hs300)：沪深300指数成分股
2. **中证500** (zz500)：中证500指数成分股
3. **自定义** (custom)：从文件加载自定义股票列表

创建自定义股票池文件示例：
```
# my_stocks.txt - 每行一个股票代码
000001.SZ
000002.SZ
600000.SH
...
```

## 返回值格式

### B1策略信号格式

`detect_b1_signal` 方法的返回值是一个列表，其中每个元素是一个包含以下键的字典：

```python
[
    {
        'date': Timestamp对象,  # 信号日期
        'price': float,        # 信号价格(收盘价)
        'stop_loss': float,    # 止损价格，基于前一天的低点计算
        'target_price': float  # 目标价格，基于止盈比例计算
    },
    # ... 更多信号
]
```

### 筛选结果格式

`get_filtered_stocks_by_date` 方法返回的详细信息字典格式：

```python
{
    '股票代码1': {
        'date': '日期字符串',
        'price': 收盘价,
        'stop_loss': 止损价,
        'target_price': 目标价,
        'conditions_met': ['满足的条件1', '满足的条件2', ...]
    },
    '股票代码2': {
        # ...
    }
}
```

## 使用示例

### 1. 测试策略变体

```bash
# 使用沪深300股票池测试
python test_strategy_variations.py --start_date 20250701 --end_date 20250801 --stock_count 50

# 使用中证500股票池测试
python test_strategy_variations.py --start_date 20250701 --end_date 20250801 --stock_pool zz500

# 使用自定义股票池测试
python test_strategy_variations.py --start_date 20250701 --end_date 20250801 --stock_pool custom --symbols_file my_stocks.txt
```

### 2. 获取特定日期的筛选结果

```bash
# 查询默认策略在2025-08-01的筛选结果
python get_b1_filtered_stocks.py --date 2025-08-01

# 查询加权策略在2025-08-01的筛选结果
python get_b1_filtered_stocks.py --date 2025-08-01 --strategy weighted

# 使用自定义股票池查询
python get_b1_filtered_stocks.py --date 2025-08-01 --stock_pool custom --symbols_file my_stocks.txt
```

## 扩展自定义策略

如果需要添加新的策略变体，可以修改以下文件：

1. 在 `b1_strategy.py` 中添加新的条件函数
2. 在 `test_strategy_variations.py` 中的 `strategy_variations` 列表中添加新的策略配置
3. 在 `get_b1_filtered_stocks.py` 中的 `configure_strategy_variant` 函数中添加新的策略配置

## 注意事项

1. 所有的日期参数格式：
   - `test_strategy_variations.py` 中使用 `YYYYMMDD` 格式
   - `get_b1_filtered_stocks.py` 中使用 `YYYY-MM-DD` 格式

2. 自定义股票池文件应确保股票代码格式正确，例如 `000001.SZ`

3. 测试前请确保已经激活正确的Python环境：
   ```bash
   source /C/D/quant/quant_env/Scripts/activate
   ```
