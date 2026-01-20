# 快速入门指南

## 安装依赖

```bash
# 激活虚拟环境（如果有）
source quant_env/Scripts/activate  # Windows Git Bash
# 或
.\quant_env\Scripts\activate       # Windows CMD

# 安装依赖
pip install pyyaml
```

## 第一步：列出可用策略

```bash
python -m framework.cli list-presets
```

输出示例：
```
可用的预设策略:
======================================================================
  default             : 基础B1策略 - 当日收盘执行
  b1_tplus1           : B1策略 - T+1开盘执行
  b1_trailing         : B1策略 - 追踪止损8%
  b1_advanced         : B1高级策略 - 组合追踪止损和时间退出
  b1_aggressive       : 激进B1策略 - 放宽选股条件
  b1_conservative     : 保守B1策略 - 严格选股
```

## 第二步：运行第一个回测

### 方式1：使用预设策略（最简单）

```bash
python -m framework.cli backtest \
  --preset b1_tplus1 \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot
```

### 方式2：使用YAML配置文件

```bash
# 使用提供的配置文件
python -m framework.cli backtest --config configs/backtest_basic.yaml --preset b1_trailing

# 或使用自定义策略配置
python -m framework.cli backtest --config configs/backtest_custom.yaml
```

## 第三步：对比多个策略

```bash
python -m framework.cli experiments \
  --strategies "b1_tplus1,b1_trailing,b1_advanced" \
  --start 2025-01-01 \
  --end 2025-06-30 \
  --plot \
  --export results/my_first_experiment
```

## 理解配置文件

### 最小配置（使用预设）

```yaml
# configs/simple.yaml
backtest:
  start: "2025-01-01"
  end: "2025-06-30"
  plot: true
```

使用：
```bash
python -m framework.cli backtest --config configs/simple.yaml --preset b1_tplus1
```

### 完整自定义配置

```yaml
# configs/custom.yaml
backtest:
  start: "2025-01-01"
  end: "2025-06-30"
  
  strategy:
    name: "my_first_strategy"
    
    # 四层配置（必须完整）
    selection: "b1"              # 选股策略
    entry: "b1"                  # 入场策略
    exit: "trailing"             # 退出策略
    execution: "next_open"       # 执行模式
    
    # 各层参数（可选）
    selection_params:
      j_threshold: -8            # KDJ的J值阈值
    exit_params:
      trailing_pct: 0.08         # 8%追踪止损
  
  # 回测参数
  initial: 1000000
  max_positions: 5
  plot: true
  export: "results/my_test"
```

## 自定义你的第一个策略

### 步骤1：复制配置模板

```bash
cp configs/backtest_custom.yaml configs/my_strategy.yaml
```

### 步骤2：修改参数

编辑 `configs/my_strategy.yaml`，调整：
- `selection_params`: 选股条件
- `exit_params`: 止损止盈参数
- `max_positions`: 持仓数量
- `universe`: 股票池大小

### 步骤3：运行并查看结果

```bash
python -m framework.cli backtest --config configs/my_strategy.yaml
```

## 查看结果

回测完成后会输出：
1. **控制台**: 显示关键指标（CAGR、Sharpe、最大回撤等）
2. **图表**: equity.png（如果使用 --plot）
3. **CSV文件**: history.csv, trades.csv, metrics.csv（如果使用 --export）

## 下一步

1. **参数调优**: 修改YAML中的参数，观察回测结果变化
2. **策略对比**: 使用experiments命令对比多个策略
3. **开发新策略**: 参考README.md的"扩展开发"章节
4. **运行测试**: `python -m framework.cli tests`

## 常用命令速查

```bash
# 列出预设
python -m framework.cli list-presets

# 快速回测
python -m framework.cli backtest --preset b1_tplus1 --start 2025-01-01 --end 2025-06-30

# 使用配置文件
python -m framework.cli backtest --config configs/backtest_basic.yaml --preset b1_trailing

# 多策略对比
python -m framework.cli experiments --config configs/experiments.yaml

# 运行测试
python -m framework.cli tests
```

## 故障排除

### 错误：未找到PyYAML
```bash
pip install pyyaml
```

### 错误：策略配置不完整
确保YAML中包含完整的四层：selection, entry, exit, execution

### 错误：日期格式
使用 YYYY-MM-DD 格式，例如：2025-01-01

## 获取帮助

```bash
# 查看命令帮助
python -m framework.cli --help
python -m framework.cli backtest --help
python -m framework.cli experiments --help
```

祝你使用愉快！ 🚀
