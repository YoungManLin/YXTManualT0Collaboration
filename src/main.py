#!/usr/bin/env python3
"""
YXT Manual T0 Collaboration - 主入口

用法:
    python src/main.py --input data/sample_orders.xlsx --output reports/position_report.xlsx
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from dbf_parser import DBFParser
from position_calc import PositionCalculator
from t0_strategy import T0Strategy
from risk_check import RiskChecker


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='策略团队仓位计算系统')
    parser.add_argument('--input', '-i', required=True, help='输入文件路径（DBF/Excel）')
    parser.add_argument('--output', '-o', default='reports/position_report.xlsx', help='输出报告路径')
    parser.add_argument('--prices', '-p', help='当前价格文件（JSON 格式）')
    parser.add_argument('--trades', '-t', help='成交记录文件（Excel/CSV）')
    parser.add_argument('--config', '-c', help='配置文件路径（JSON 格式）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("YXT Manual T0 Collaboration - 策略团队仓位计算系统")
    print("=" * 60)
    print()
    
    # 1. 解析输入文件
    print(f"[1/5] 解析输入文件：{args.input}")
    dbf_parser = DBFParser(args.input)
    orders = dbf_parser.parse()
    
    summary = dbf_parser.get_summary()
    print(f"  - 总订单数：{summary['total_orders']}")
    print(f"  - 股票数量：{summary['unique_stocks']}")
    print(f"  - 账户数量：{summary['unique_accounts']}")
    
    if summary['parse_errors']:
        print(f"  - 解析错误：{len(summary['parse_errors'])}")
        for err in summary['parse_errors'][:3]:
            print(f"    * {err}")
    
    print()
    
    # 2. 加载价格数据
    prices = {}
    if args.prices:
        print(f"[2/5] 加载价格数据：{args.prices}")
        with open(args.prices, 'r', encoding='utf-8') as f:
            prices = json.load(f)
        print(f"  - 加载价格数量：{len(prices)}")
    else:
        print("[2/5] 跳过价格数据加载")
    print()
    
    # 3. 计算仓位
    print("[3/5] 计算仓位...")
    calc = PositionCalculator()
    calc.load_orders(orders)
    
    # 如果有成交记录，加载成交
    if args.trades:
        print(f"  - 加载成交记录：{args.trades}")
        # TODO: 实现成交记录加载
    
    calc.set_prices(prices)
    positions = calc.calculate()
    
    pos_summary = calc.get_summary()
    print(f"  - 仓位数量：{pos_summary['total_positions']}")
    print(f"  - 总市值：{pos_summary['total_market_value']:.2f}")
    print(f"  - 总盈亏：{pos_summary['total_profit_loss']:.2f}")
    print()
    
    # 4. T0 策略分析
    print("[4/5] T0 策略分析...")
    t0_positions = calc.calculate_t0()
    print(f"  - T0 仓位数量：{len(t0_positions)}")
    
    t0_strategy = T0Strategy()
    signals = t0_strategy.generate_signals(t0_positions, prices)
    signal_summary = t0_strategy.get_signal_summary()
    print(f"  - 生成信号：{signal_summary['total_signals']}")
    print(f"    * 买入信号：{signal_summary['buy_signals']}")
    print(f"    * 卖出信号：{signal_summary['sell_signals']}")
    print()
    
    # 5. 风险检查
    print("[5/5] 风险检查...")
    risk_checker = RiskChecker()
    alerts = risk_checker.check(positions)
    alert_summary = risk_checker.get_alert_summary()
    print(f"  - 告警总数：{alert_summary['total_alerts']}")
    print(f"  - 风险状态：{alert_summary['status']}")
    
    if alert_summary['error_count'] > 0:
        print(f"  - 错误告警：{alert_summary['error_count']}")
        for alert in alert_summary['alerts']:
            if alert['level'] == 'ERROR':
                print(f"    * {alert['message']}")
    print()
    
    # 6. 导出报告
    print(f"[6/6] 导出报告：{args.output}")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    calc.export_report(str(output_path))
    print(f"  - 报告已保存：{output_path.absolute()}")
    print()
    
    # 7. 输出摘要
    print("=" * 60)
    print("计算完成!")
    print("=" * 60)
    print(f"时间：{datetime.now().isoformat()}")
    print(f"输入：{args.input}")
    print(f"输出：{args.output}")
    print(f"订单数：{summary['total_orders']}")
    print(f"仓位数：{pos_summary['total_positions']}")
    print(f"总市值：¥{pos_summary['total_market_value']:,.2f}")
    print(f"总盈亏：¥{pos_summary['total_profit_loss']:,.2f}")
    print(f"风险状态：{alert_summary['status']}")
    print()


if __name__ == '__main__':
    main()
