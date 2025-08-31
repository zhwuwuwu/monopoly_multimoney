#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
指数贡献选股策略使用示例
"""

import sys
import os

# 添加父目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filter.index_contribution_filter import IndexContributionFilter
from datetime import datetime, timedelta


def example_list_all_sectors():
    """示例1: 列出所有板块信息"""
    print("=" * 60)
    print("示例1: 列出所有板块信息")
    print("=" * 60)
    
    filter = IndexContributionFilter(verbose=True)
    sectors = filter.get_all_sectors()
    filter.display_sectors(sectors)
    
    return sectors


def example_filter_specific_sectors():
    """示例2: 筛选特定板块的权重股"""
    print("\n" + "=" * 60)
    print("示例2: 筛选特定板块的权重股")
    print("=" * 60)
    
    # 使用昨天的日期作为示例
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    filter = IndexContributionFilter(verbose=True)
    
    # 示例板块代码（这些需要根据实际情况调整）
    example_sectors = ['BK0447', 'BK0478']  # 示例概念板块代码
    
    results = filter.run(
        target_date=target_date,
        sector_codes=example_sectors,
        sector_type='concept',
        top_n=5,  # 每个板块取前5只
        kdj_threshold=15.0,
        save_results=True
    )
    
    return results


def example_usage_workflow():
    """示例3: 完整的使用流程"""
    print("\n" + "=" * 60)
    print("示例3: 完整的使用流程")
    print("=" * 60)
    
    # 步骤1: 先查看所有板块
    filter = IndexContributionFilter(verbose=True)
    sectors = filter.get_all_sectors()
    
    # 步骤2: 选择感兴趣的板块（这里选择前几个概念板块作为示例）
    concept_sectors = sectors.get('concept', [])
    if concept_sectors:
        selected_sectors = [sector['code'] for sector in concept_sectors[:3]]  # 选择前3个板块
        
        print(f"\n选择的板块: {selected_sectors}")
        
        # 步骤3: 运行筛选
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        results = filter.run(
            target_date=target_date,
            sector_codes=selected_sectors,
            sector_type='concept',
            top_n=10,
            kdj_threshold=15.0,
            save_results=True
        )
        
        return results
    else:
        print("未能获取到概念板块信息")
        return {}


def main():
    """主函数"""
    print("指数贡献选股策略使用示例")
    print("=" * 60)
    
    try:
        # 示例1: 列出所有板块
        sectors = example_list_all_sectors()
        
        # 如果成功获取到板块信息，则继续其他示例
        if sectors:
            # 示例2: 筛选特定板块
            # example_filter_specific_sectors()
            
            # 示例3: 完整流程
            example_usage_workflow()
        
    except Exception as e:
        print(f"运行示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
