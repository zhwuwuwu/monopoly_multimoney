"""统一 CLI 入口（重构版） - 支持YAML配置，仅保留 backtest/experiments/tests。

核心改进：
  1. 移除 filter 入口，专注于回测和实验
  2. 所有策略通过 factory 统一构建（四层完整）
  3. 支持YAML配置文件
  4. 支持预设策略和自定义策略
  
用法示例：
  # 使用预设策略
  python -m framework.cli backtest --config configs/backtest.yaml --preset b1_tplus1
  
  # 使用YAML配置自定义策略
  python -m framework.cli backtest --config configs/custom_strategy.yaml
  
  # 命令行参数覆盖
  python -m framework.cli backtest --config configs/base.yaml --initial 2000000
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings
from typing import Optional, Dict, Any

# 过滤第三方库的 FutureWarning（如 akshare/pandas）
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from strategies.composite.factory import build_custom_strategy
from strategies.composite.presets import get_preset_config, list_presets
from framework.engine import BacktestEngine, run_parallel_experiments
from framework.visualize import plot_equity, compare_equity


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """加载YAML配置文件"""
    if not YAML_AVAILABLE:
        print("错误: 需要安装 PyYAML 才能使用配置文件功能")
        print("请运行: pip install pyyaml")
        sys.exit(1)
    
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config or {}
    except Exception as e:
        print(f"错误: 无法解析YAML配置文件: {e}")
        sys.exit(1)


def merge_config_and_args(config: Dict[str, Any], args: argparse.Namespace, command: str) -> argparse.Namespace:
    """合并YAML配置和命令行参数，命令行参数优先级更高"""
    if not config:
        return args
    
    cmd_config = config.get(command, {})
    
    # 构建命令行提供的参数集合
    provided_args = set()
    for arg in sys.argv:
        if arg.startswith('--'):
            provided_args.add(arg[2:].replace('-', '_'))
    
    for key, value in cmd_config.items():
        attr_key = key.replace('-', '_')
        
        # 只有当命令行未提供该参数时，才使用配置文件的值
        if attr_key not in provided_args and hasattr(args, attr_key):
            current_value = getattr(args, attr_key)
            # 对于列表类型，特殊处理
            if isinstance(current_value, list) and not current_value:
                setattr(args, attr_key, value if isinstance(value, list) else [value])
            elif current_value is None or isinstance(current_value, (int, float, str, bool)):
                setattr(args, attr_key, value)
    
    return args


def build_strategy_from_config(config: Dict[str, Any], args: argparse.Namespace):
    """从配置构建策略"""
    # 优先使用预设
    if hasattr(args, 'preset') and args.preset:
        print(f"使用预设策略: {args.preset}")
        preset_config = get_preset_config(args.preset)
        return build_custom_strategy(
            selection_name=preset_config['selection'],
            entry_name=preset_config['entry'],
            exit_name=preset_config['exit'],
            execution_name=preset_config['execution'],
            selection_params=preset_config.get('selection_params'),
            entry_params=preset_config.get('entry_params'),
            exit_params=preset_config.get('exit_params'),
            name=args.preset,
            validate=True
        )
    
    # 从配置或命令行参数构建
    strategy_config = config.get('strategy', {})
    
    selection = getattr(args, 'selection', None) or strategy_config.get('selection', 'b1')
    entry = getattr(args, 'entry', None) or strategy_config.get('entry', 'b1')
    exit = getattr(args, 'exit', None) or strategy_config.get('exit', 'fixed')
    execution = getattr(args, 'execution', None) or strategy_config.get('execution', 'close')
    
    selection_params = strategy_config.get('selection_params', {})
    entry_params = strategy_config.get('entry_params', {})
    exit_params = strategy_config.get('exit_params', {})
    
    name = getattr(args, 'name', None) or strategy_config.get('name', 'custom_strategy')
    
    print(f"构建自定义策略: {name}")
    print(f"  选股: {selection}")
    print(f"  入场: {entry}")
    print(f"  退出: {exit}")
    print(f"  执行: {execution}")
    
    return build_custom_strategy(
        selection_name=selection,
        entry_name=entry,
        exit_name=exit,
        execution_name=execution,
        selection_params=selection_params,
        entry_params=entry_params,
        exit_params=exit_params,
        name=name,
        validate=True
    )


def cmd_backtest(args: argparse.Namespace):
    """执行回测命令"""
    # 加载配置
    config = {}
    if hasattr(args, 'config') and args.config:
        config = load_yaml_config(args.config)
        args = merge_config_and_args(config, args, 'backtest')
    
    # 验证必要参数
    if not args.start or not args.end:
        print("错误: 必须提供 --start 和 --end 参数")
        sys.exit(1)
    
    # 构建策略
    strategy = build_strategy_from_config(config, args)
    
    # 临时注册策略到 registry（避免 engine 重新构建）
    from strategies.composite.registry import STRATEGY_BUILDERS
    temp_strategy_name = '__temp_cli_strategy__'
    STRATEGY_BUILDERS[temp_strategy_name] = lambda **kwargs: strategy
    
    # 创建引擎并运行
    engine = BacktestEngine(
        strategy_name=temp_strategy_name,
        strategy_kwargs={},
        initial_capital=args.initial
    )
    
    res = engine.run(
        args.start,
        args.end,
        max_positions=args.max_positions,
        universe_size=args.universe,
        commission_rate=args.commission,
        slippage_bp=args.slippage_bp
    )
    
    # 添加策略配置到结果
    res['strategy_config'] = strategy.to_dict()
    
    # 输出结果
    print("\n" + "=" * 70)
    print("回测指标")
    print("=" * 70)
    for k, v in res['metrics'].items():
        if isinstance(v, float):
            if 'return' in k or 'cagr' in k or 'drawdown' in k:
                print(f"  {k:<25}: {v:>10.2%}")
            else:
                print(f"  {k:<25}: {v:>10.4f}")
        else:
            print(f"  {k:<25}: {v}")
    
    if res.get('strategy_config'):
        print("\n" + "=" * 70)
        print("策略配置")
        print("=" * 70)
        import json
        print(json.dumps(res['strategy_config'], ensure_ascii=False, indent=2, default=str))
    
    # 可视化
    if args.plot:
        save_path = f"{args.export}/equity.png" if args.export else None
        plot_equity(res['history'], save_path=save_path)
    
    # 导出
    if args.export:
        import csv
        os.makedirs(args.export, exist_ok=True)
        res['history'].to_csv(f"{args.export}/history.csv", index=False, encoding='utf-8-sig')
        res['trades'].to_csv(f"{args.export}/trades.csv", index=False, encoding='utf-8-sig')
        
        with open(f"{args.export}/metrics.csv", 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['metric', 'value'])
            for k, v in res['metrics'].items():
                w.writerow([k, v])
        
        if res.get('strategy_config'):
            import json
            with open(f"{args.export}/strategy_config.json", 'w', encoding='utf-8') as f:
                json.dump(res['strategy_config'], f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✓ 导出完成: {args.export}")


def cmd_experiments(args: argparse.Namespace):
    """执行多策略实验命令"""
    # 加载配置
    config = {}
    if hasattr(args, 'config') and args.config:
        config = load_yaml_config(args.config)
        args = merge_config_and_args(config, args, 'experiments')
    
    # 验证必要参数
    if not args.start or not args.end or not args.strategies:
        print("错误: 必须提供 --start, --end 和 --strategies 参数")
        sys.exit(1)
    
    # 解析策略列表
    strategy_names = [s.strip() for s in args.strategies.split(',') if s.strip()]
    
    # 构建每个策略的配置
    configs = []
    for strat_name in strategy_names:
        # 尝试作为预设加载
        try:
            preset_config = get_preset_config(strat_name)
            strategy = build_custom_strategy(
                selection_name=preset_config['selection'],
                entry_name=preset_config['entry'],
                exit_name=preset_config['exit'],
                execution_name=preset_config['execution'],
                selection_params=preset_config.get('selection_params'),
                entry_params=preset_config.get('entry_params'),
                exit_params=preset_config.get('exit_params'),
                name=strat_name,
                validate=True
            )
            configs.append({
                'strategy': strat_name,
                'strategy_obj': strategy,
                'universe_size': args.universe,
                'max_positions': args.max_positions
            })
        except ValueError:
            print(f"警告: 策略 '{strat_name}' 不是预设，跳过")
            continue
    
    if not configs:
        print("错误: 没有有效的策略配置")
        sys.exit(1)
    
    # 运行实验（这里需要适配engine以支持strategy对象）
    print(f"\n开始运行 {len(configs)} 个策略实验...")
    results = []
    
    from strategies.composite.registry import STRATEGY_BUILDERS
    
    for cfg in configs:
        print(f"\n运行策略: {cfg['strategy']}")
        
        # 临时注册策略
        temp_name = f"__temp_{cfg['strategy']}__"
        _strategy = cfg['strategy_obj']
        STRATEGY_BUILDERS[temp_name] = lambda _s=_strategy, **kwargs: _s
        
        engine = BacktestEngine(strategy_name=temp_name, initial_capital=1_000_000)
        res = engine.run(
            args.start,
            args.end,
            max_positions=cfg['max_positions'],
            universe_size=cfg['universe_size'],
            commission_rate=0.0005,
            slippage_bp=5.0
        )
        res['params'] = {'strategy': cfg['strategy']}
        res['strategy_config'] = cfg['strategy_obj'].to_dict()
        results.append(res)
    
    # 输出摘要
    print("\n" + "=" * 70)
    print("实验摘要")
    print("=" * 70)
    for r in results:
        m = r['metrics']
        strat = r['params']['strategy']
        print(f"  {strat:<20}: CAGR {m.get('cagr',0):>7.2%} | Sharpe {m.get('sharpe',0):>6.2f} | MDD {m.get('max_drawdown',0):>7.2%}")
    
    # 可视化对比
    if args.plot:
        save_path = f"{args.export}/equity_compare.png" if args.export else None
        compare_equity(results, save_path=save_path)
    
    # 导出
    if args.export:
        os.makedirs(args.export, exist_ok=True)
        for r in results:
            strat = r['params']['strategy']
            r['history'].to_csv(f"{args.export}/history_{strat}.csv", index=False, encoding='utf-8-sig')
            r['trades'].to_csv(f"{args.export}/trades_{strat}.csv", index=False, encoding='utf-8-sig')
        print(f"\n✓ 导出完成: {args.export}")


def cmd_tests(_args: argparse.Namespace):
    """运行单元测试"""
    import runpy
    run_tests_path = os.path.join(os.path.dirname(__file__), '..', 'unitest', 'run_tests.py')
    run_tests_path = os.path.abspath(run_tests_path)
    if not os.path.exists(run_tests_path):
        print("未找到 unitest/run_tests.py")
        return
    print(f"执行测试: {run_tests_path}")
    runpy.run_path(run_tests_path, run_name='__main__')


def cmd_list_presets(_args: argparse.Namespace):
    """列出所有可用的预设策略"""
    presets = list_presets()
    print("\n可用的预设策略:")
    print("=" * 70)
    for name, desc in presets.items():
        print(f"  {name:<20}: {desc}")
    print()


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="量化交易框架CLI（重构版） - 统一使用factory构建四层策略",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用预设策略回测
  python -m framework.cli backtest --preset b1_tplus1 --start 2025-01-01 --end 2025-06-30
  
  # 使用YAML配置文件
  python -m framework.cli backtest --config configs/backtest.yaml
  
  # YAML + 命令行参数覆盖
  python -m framework.cli backtest --config configs/base.yaml --initial 2000000
  
  # 列出所有预设策略
  python -m framework.cli list-presets
  
  # 多策略实验
  python -m framework.cli experiments --strategies "b1_tplus1,b1_trailing,b1_advanced" \\
      --start 2025-01-01 --end 2025-06-30
        """
    )
    
    parser.add_argument('--config', type=str, help='YAML配置文件路径（可选）')
    
    sub = parser.add_subparsers(dest="command", required=True)

    # ========== backtest 子命令 ==========
    p_bt = sub.add_parser("backtest", help="运行回测")
    p_bt.add_argument('--start', type=str, help='开始日期 YYYY-MM-DD')
    p_bt.add_argument('--end', type=str, help='结束日期 YYYY-MM-DD')
    
    # 策略选择：预设 或 自定义
    p_bt.add_argument('--preset', type=str, help='使用预设策略（优先级最高）')
    p_bt.add_argument('--selection', type=str, help='选股策略名称')
    p_bt.add_argument('--entry', type=str, help='入场策略名称')
    p_bt.add_argument('--exit', type=str, help='退出策略名称')
    p_bt.add_argument('--execution', type=str, help='执行模式名称 (close/next_open/tplus1/vwap)')
    p_bt.add_argument('--name', type=str, help='自定义策略名称')
    
    # 回测参数
    p_bt.add_argument('--initial', type=float, default=1_000_000, help='初始资金')
    p_bt.add_argument('--max-positions', type=int, default=5, help='最大持仓数')
    p_bt.add_argument('--universe', type=int, default=100, help='股票池规模')
    p_bt.add_argument('--commission', type=float, default=0.0005, help='单边费率')
    p_bt.add_argument('--slippage-bp', type=float, default=5.0, help='滑点 (basis points)')
    p_bt.add_argument('--plot', action='store_true', help='输出资金曲线')
    p_bt.add_argument('--export', nargs='?', const='results/backtest', help='导出目录')
    p_bt.set_defaults(func=cmd_backtest)

    # ========== experiments 子命令 ==========
    p_exp = sub.add_parser("experiments", help="并行多策略实验")
    p_exp.add_argument('--start', type=str, help='开始日期')
    p_exp.add_argument('--end', type=str, help='结束日期')
    p_exp.add_argument('--strategies', type=str, help='逗号分隔的预设策略名列表')
    p_exp.add_argument('--universe', type=int, default=100)
    p_exp.add_argument('--max-positions', type=int, default=5)
    p_exp.add_argument('--plot', action='store_true')
    p_exp.add_argument('--export', nargs='?', const='results/experiments')
    p_exp.set_defaults(func=cmd_experiments)

    # ========== tests 子命令 ==========
    p_tests = sub.add_parser("tests", help="运行单元测试")
    p_tests.set_defaults(func=cmd_tests)

    # ========== list-presets 子命令 ==========
    p_list = sub.add_parser("list-presets", help="列出所有可用的预设策略")
    p_list.set_defaults(func=cmd_list_presets)

    return parser


def main(argv: Optional[list[str]] = None):
    """CLI 主入口"""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
