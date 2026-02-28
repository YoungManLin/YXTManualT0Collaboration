"""
测试数据生成模块
"""

import pandas as pd
from pathlib import Path


def create_sample_orders(output_path: str):
    """
    创建样例订单数据（Excel 格式）
    
    基于迅投 PB-DBF 预埋单参数说明文档 V2.15
    """
    # 样例订单数据
    data = {
        '序号': list(range(1, 11)),
        '字段名': [
            'order_type', 'price_type', 'mode_price', 'stock_code',
            'volume', 'account_id', 'act_type', 'brokertype',
            'strategy', 'note'
        ],
        '类型': ['String'] * 10,
        '说明': [
            '下单类型', '委托价格类型', '委托价格', '证券代码',
            '委托数量', '下单资金账号', '账号类别', '账号类型',
            '策略备注', '投资备注'
        ],
        '必填': ['Y', 'Y', 'N', 'Y', 'Y', 'Y', 'N', 'N', 'N', 'N'],
        '备注': [''] * 10,
        '表头必有': ['√'] * 10,
    }
    
    df = pd.DataFrame(data)
    
    # 保存到 Excel
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='详情', index=False)
    
    print(f"样例数据已创建：{output_file}")
    return output_file


if __name__ == '__main__':
    create_sample_orders('data/sample_orders.xlsx')
