"""统一 CLI 入口

提供子命令：
  filter   运行 B1 选股筛选
  backtest (预留) 回测接口扩展
  tests    触发单元测试入口包装

用法示例：
  python -m framework.cli filter --date 2025-08-01 --strategy default --stock_pool hs300
  python -m framework.cli tests
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from strategies.selection.b1_variants import build_b1_selection_variant
from framework.screener import StockPoolProvider, StockScreener
from strategies.composite.registry import get_strategy
from strategies.composite.factory import build_custom_strategy
from strategies.composite.b1_composite import B1CompositeStrategy
from framework.engine import BacktestEngine, run_parallel_experiments
from framework.visualize import plot_equity, compare_equity


def cmd_filter(args: argparse.Namespace):
    # 环境代理屏蔽（与旧实现一致）
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ[k] = ""

    selection = build_b1_selection_variant(args.strategy) if args.strategy else None
    pool_provider = StockPoolProvider(verbose=not args.quiet)
    screener = StockScreener(history_days=60, verbose=not args.quiet)
    custom_symbols = None
    if args.stock_pool == 'custom' and args.symbols_file:
        # 尝试读取自定义股票池
        encodings = [args.encoding, 'utf-8', 'gbk']
        for enc in encodings:
            try:
                with open(args.symbols_file, 'r', encoding=enc) as f:
                    custom_symbols = [line.strip() for line in f if line.strip()]
                if not args.quiet:
                    print(f"读取自定义股票池成功(编码={enc})：{len(custom_symbols)} 只")
                break
            except Exception:  # noqa
                continue
        if custom_symbols is None:
            print("自定义股票池文件读取失败，退出。")
            sys.exit(1)

    symbols = custom_symbols if (args.stock_pool == 'custom' and custom_symbols) else pool_provider.get_symbols(args.stock_pool)
    if args.stock_count > 0:
        symbols = symbols[:args.stock_count]
    # 加载数据并执行
    market_data = screener.load_stock_data(symbols, args.date)
    if selection is None:
        # 默认使用 composite 注册的 b1 selection
        composite = get_strategy('b1')
        selection = composite.selection
    # details mode
    if getattr(args, 'details', False) and hasattr(selection, 'select_with_details'):
        details = selection.select_with_details(market_data)  # type: ignore
        selected = [d.symbol for d in details]
        if not args.quiet:
            print(f"选出 {len(selected)} 只股票：")
            for d in details:
                print(f"  {d.symbol} score={d.score} reasons={','.join(d.reasons)}")
        if getattr(args, 'plot', False):
            try:
                selection.visualize(details, top_n=30)
            except Exception as e:  # noqa
                print(f"可视化失败: {e}")
    else:
        selected = selection.select(market_data)
        if not args.quiet:
            print(f"选出 {len(selected)} 只股票: {selected}")
    # 可选保存
    if not args.no_save:
        import csv
        out_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.abspath(os.path.join(out_dir, f"b1_filtered_{args.date.replace('-', '')}_{args.strategy}.csv"))
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol'])
            for s in selected:
                writer.writerow([s])
        if not args.quiet:
            print(f"结果已保存到 {out_path}")


def cmd_tests(_args: argparse.Namespace):
    """统一测试执行：调用 unitest/run_tests.py"""
    import runpy
    run_tests_path = os.path.join(os.path.dirname(__file__), '..', 'unitest', 'run_tests.py')
    run_tests_path = os.path.abspath(run_tests_path)
    if not os.path.exists(run_tests_path):
        print("未找到 unitest/run_tests.py")
        return
    print(f"执行测试: {run_tests_path}")
    runpy.run_path(run_tests_path, run_name='__main__')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="统一量化框架 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # filter 子命令
    p_filter = sub.add_parser("filter", help="运行 B1 选股筛选")
    p_filter.add_argument('--date', type=str, required=True, help='查询日期 YYYY-MM-DD')
    p_filter.add_argument('--stock_count', type=int, default=-1, help='截取股票数，-1 全部')
    p_filter.add_argument('--strategy', type=str, default='default',
                          choices=['default', 'b1+', 'volume_surge', 'loose', 'weighted'],
                          help='B1 变体')
    p_filter.add_argument('--stock_pool', type=str, default='hs300',
                          choices=['hs300', 'zz500', 'all_a', 'main', 'custom'], help='股票池')
    p_filter.add_argument('--symbols_file', type=str, help='自定义股票池文件路径 (配合 custom)')
    p_filter.add_argument('--no_save', action='store_true', help='不保存结果CSV')
    p_filter.add_argument('--details', action='store_true', help='打印得分与命中条件')
    p_filter.add_argument('--plot', action='store_true', help='可视化结果')
    p_filter.add_argument('--quiet', action='store_true', help='安静模式')
    p_filter.add_argument('--encoding', type=str, default='utf-8', help='自定义股票池文件编码')
    p_filter.set_defaults(func=cmd_filter)

    # tests 子命令
    p_tests = sub.add_parser("tests", help="运行单元测试入口")
    p_tests.set_defaults(func=cmd_tests)

    # backtest 子命令
    p_bt = sub.add_parser("backtest", help="运行回测")
    p_bt.add_argument('--start', required=True, type=str, help='开始日期 YYYY-MM-DD')
    p_bt.add_argument('--end', required=True, type=str, help='结束日期 YYYY-MM-DD')
    p_bt.add_argument('--strategy', type=str, default='b1', help='策略名称 (b1 / custom)')
    # 组合层参数（仅当 strategy=custom 或覆盖默认时使用）
    p_bt.add_argument('--selection', type=str, help='选股策略名称')
    p_bt.add_argument('--entry', type=str, help='入场策略名称')
    p_bt.add_argument('--exit', type=str, help='出场策略名称')
    p_bt.add_argument('--selection-param', action='append', default=[], help='选股层参数 k=v，可多次')
    p_bt.add_argument('--entry-param', action='append', default=[], help='入场层参数 k=v，可多次')
    p_bt.add_argument('--exit-param', action='append', default=[], help='出场层参数 k=v，可多次')
    p_bt.add_argument('--name', type=str, help='自定义策略名称')
    p_bt.add_argument('--entry-execution', type=str, help='B1 组合专用：same_close / t+1')
    p_bt.add_argument('--exit-type', type=str, help='B1 组合专用：fixed/time/trailing/advanced')
    p_bt.add_argument('--exit-arg', action='append', default=[], help='B1 退出策略参数 k=v (trailing_pct=0.08 等)')
    p_bt.add_argument('--initial', type=float, default=1_000_000, help='初始资金')
    p_bt.add_argument('--max-positions', type=int, default=5, help='最大持仓数')
    p_bt.add_argument('--universe', type=int, default=100, help='股票池规模')
    p_bt.add_argument('--commission', type=float, default=0.0005, help='单边费率')
    p_bt.add_argument('--slippage-bp', type=float, default=5.0, help='滑点 (basis points)')
    p_bt.add_argument('--plot', action='store_true', help='输出资金曲线')
    p_bt.add_argument('--export', nargs='?', const='results/backtest', help='导出目录')
    def _parse_kv(pairs):
        out = {}
        for kv in pairs:
            if '=' not in kv:
                continue
            k, v = kv.split('=', 1)
            k = k.strip()
            v = v.strip()
            # 尝试转换数字
            try:
                if v.lower() in {'true','false'}:
                    v_cast = v.lower() == 'true'
                elif '.' in v:
                    v_cast = float(v)
                    if v_cast.is_integer():
                        v_cast = int(v_cast)
                else:
                    v_cast = int(v)
                out[k] = v_cast
                continue
            except Exception:  # noqa
                pass
            out[k] = v
        return out

    def _build_strategy_from_args(a):
        if a.strategy == 'custom':
            sel_params = _parse_kv(a.selection_param)
            ent_params = _parse_kv(a.entry_param)
            ex_params = _parse_kv(a.exit_param)
            return build_custom_strategy(
                selection_name=a.selection or 'b1',
                entry_name=a.entry or 'b1',
                exit_name=a.exit or 'fixed',
                selection_params=sel_params or None,
                entry_params=ent_params or None,
                exit_params=ex_params or None,
                name=a.name or 'customized_strategy'
            )
        # b1 快捷策略（可覆盖 entry_execution / exit_type / exit_args ）
        strat_params = {}
        if a.entry_execution:
            strat_params['entry_execution'] = a.entry_execution
        if a.exit_type:
            strat_params['exit_type'] = a.exit_type
        exit_args = _parse_kv(a.exit_arg)
        if exit_args:
            strat_params['exit_args'] = exit_args
        return get_strategy('b1', params=strat_params if strat_params else None)

    def _run_bt(a):  # noqa: ANN001
        # 若传递 custom 则直接装配，否则用 BacktestEngine + registry
        custom_strategy_obj = None
        if a.strategy == 'custom':
            custom_strategy_obj = _build_strategy_from_args(a)
            engine = BacktestEngine(strategy_name='custom', strategy_kwargs={}, initial_capital=a.initial)
        else:
            engine = BacktestEngine(strategy_name=a.strategy, initial_capital=a.initial,
                                    strategy_kwargs=None if a.strategy != 'b1' else None)
        res = engine.run(a.start, a.end,
                         max_positions=a.max_positions,
                         universe_size=a.universe,
                         commission_rate=a.commission,
                         slippage_bp=a.slippage_bp)
        if custom_strategy_obj is not None:
            # 替换结果中的策略配置为自定义对象的 config
            res['strategy_config'] = getattr(custom_strategy_obj, 'to_dict', lambda: {})()
        print("回测指标:")
        print("回测指标:")
        for k, v in res['metrics'].items():
            if isinstance(v, float):
                if 'return' in k or 'cagr' in k or 'drawdown' in k:
                    print(f"  {k}: {v:.2%}")
                else:
                    print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")
        if 'strategy_config' in res:
            print("策略配置:")
            import json
            print(json.dumps(res['strategy_config'], ensure_ascii=False, indent=2, default=str))
        if a.plot:
            plot_equity(res['history'], save_path=(f"{a.export}/equity.png" if a.export else None))
        if a.export:
            import csv
            os.makedirs(a.export, exist_ok=True)
            res['history'].to_csv(f"{a.export}/history.csv", index=False, encoding='utf-8-sig')
            res['trades'].to_csv(f"{a.export}/trades.csv", index=False, encoding='utf-8-sig')
            with open(f"{a.export}/metrics.csv", 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(['metric', 'value'])
                for k, v in res['metrics'].items():
                    w.writerow([k, v])
            if 'strategy_config' in res:
                import json
                with open(f"{a.export}/strategy_config.json", 'w', encoding='utf-8') as f:
                    json.dump(res['strategy_config'], f, ensure_ascii=False, indent=2, default=str)
            print(f"导出完成: {a.export}")
    p_bt.set_defaults(func=_run_bt)

    # experiments 子命令
    p_exp = sub.add_parser("experiments", help="并行多策略实验")
    p_exp.add_argument('--start', required=True)
    p_exp.add_argument('--end', required=True)
    p_exp.add_argument('--strategies', required=True, help='逗号分隔策略名列表')
    p_exp.add_argument('--universe', type=int, default=100)
    p_exp.add_argument('--max-positions', type=int, default=5)
    p_exp.add_argument('--plot', action='store_true')
    p_exp.add_argument('--export', nargs='?', const='results/experiments')
    def _run_exp(a):  # noqa: ANN001
        configs = []
        for s in [x.strip() for x in a.strategies.split(',') if x.strip()]:
            configs.append({'strategy': s, 'universe_size': a.universe, 'max_positions': a.max_positions})
        res_list = run_parallel_experiments(configs, a.start, a.end)
        print("实验摘要:")
        for r in res_list:
            m = r['metrics']
            print(f"  {r['params']['strategy']}: CAGR {m.get('cagr',0):.2%} Sharpe {m.get('sharpe',0):.2f} MDD {m.get('max_drawdown',0):.2%}")
        if a.plot:
            compare_equity(res_list, save_path=(f"{a.export}/equity_compare.png" if a.export else None))
        if a.export:
            os.makedirs(a.export, exist_ok=True)
            for r in res_list:
                strat = r['params']['strategy']
                r['history'].to_csv(f"{a.export}/history_{strat}.csv", index=False, encoding='utf-8-sig')
                r['trades'].to_csv(f"{a.export}/trades_{strat}.csv", index=False, encoding='utf-8-sig')
    p_exp.set_defaults(func=_run_exp)

    return parser


def main(argv: Optional[list[str]] = None):  # pragma: no cover - CLI 入口
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':  # pragma: no cover
    main()
