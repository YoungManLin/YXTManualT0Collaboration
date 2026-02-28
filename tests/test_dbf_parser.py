"""
DBF 解析器单元测试
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dbf_parser import DBFParser, DBFOrder


class TestDBFParser:
    """DBF 解析器测试"""
    
    def test_parse_excel(self, tmp_path):
        """测试 Excel 文件解析"""
        # 创建测试 Excel 文件
        test_file = tmp_path / "test_orders.xlsx"
        
        data = {
            'order_type': ['1', '2'],
            'price_type': ['18', '19'],
            'stock_code': ['600000', '000001'],
            'volume': ['1000', '500'],
            'account_id': ['ACC001', 'ACC002'],
        }
        
        df = pd.DataFrame(data)
        df.to_excel(test_file, sheet_name='详情', index=False)
        
        # 解析文件
        parser = DBFParser(test_file)
        orders = parser.parse()
        
        # 验证结果
        assert len(orders) == 2
        assert orders[0].stock_code == '600000'
        assert orders[0].volume == '1000'
        assert orders[1].stock_code == '000001'
    
    def test_validate_required_fields(self, tmp_path):
        """测试必填字段验证"""
        test_file = tmp_path / "test_invalid.xlsx"
        
        # 缺少必填字段
        data = {
            'order_type': ['1'],
            'stock_code': ['600000'],
            # 缺少 price_type, volume, account_id
        }
        
        df = pd.DataFrame(data)
        df.to_excel(test_file, sheet_name='详情', index=False)
        
        parser = DBFParser(test_file)
        orders = parser.parse()
        valid = parser.validate()
        
        assert not valid
        assert len(parser.parse_errors) > 0
    
    def test_get_summary(self, tmp_path):
        """测试摘要信息"""
        test_file = tmp_path / "test_summary.xlsx"
        
        data = {
            'order_type': ['1', '2', '3'],
            'price_type': ['18', '19', '18'],
            'stock_code': ['600000', '000001', '600000'],
            'volume': ['1000', '500', '800'],
            'account_id': ['ACC001', 'ACC001', 'ACC002'],
        }
        
        df = pd.DataFrame(data)
        df.to_excel(test_file, sheet_name='详情', index=False)
        
        parser = DBFParser(test_file)
        orders = parser.parse()
        summary = parser.get_summary()
        
        assert summary['total_orders'] == 3
        assert summary['unique_stocks'] == 2
        assert summary['unique_accounts'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
