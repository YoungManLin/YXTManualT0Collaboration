"""
DBF 预埋单文件解析模块 - 完整版

基于迅投 PB-DBF 预埋单参数说明文档 V2.15
支持读取 XT_DBF_ORDER.dbf 格式的委托文件

完整字段支持:
- order_type: 下单类型
- price_type: 委托价格类型  
- mode_price: 委托价格
- stock_code: 证券代码
- volume: 委托数量
- account_id: 下单资金账号
- act_type: 账号类别
- brokertype: 账号类型
- strategy: 策略备注
- note: 投资备注
- note1: 投资备注 2
- tradeparam: 交易参数
- command_id: 指令编号
- basketpath: 文件绝对路径
- inserttime: 写入时间
- extraparam: 额外参数
- batch_id: 批次 ID
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class DBFOrder:
    """DBF 委托订单数据类"""
    # 必填字段
    order_type: str  # 下单类型
    price_type: str  # 委托价格类型
    stock_code: str  # 证券代码
    volume: str  # 委托数量
    account_id: str  # 下单资金账号
    
    # 可选字段
    mode_price: Optional[str] = None  # 委托价格
    act_type: Optional[str] = None  # 账号类别
    brokertype: Optional[str] = None  # 账号类型
    strategy: Optional[str] = None  # 策略备注
    note: Optional[str] = None  # 投资备注
    note1: Optional[str] = None  # 投资备注 2
    tradeparam: Optional[str] = None  # 交易参数
    command_id: Optional[str] = None  # 指令编号
    basketpath: Optional[str] = None  # 文件绝对路径
    inserttime: Optional[str] = None  # 写入时间
    extraparam: Optional[str] = None  # 额外参数
    batch_id: Optional[str] = None  # 批次 ID
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证订单数据
        
        Returns:
            (是否有效，错误列表)
        """
        errors = []
        
        # 检查必填字段
        required_fields = ['order_type', 'price_type', 'stock_code', 'volume', 'account_id']
        for field in required_fields:
            value = getattr(self, field)
            if not value or value.strip() == '':
                errors.append(f"缺少必填字段：{field}")
        
        # 验证证券代码格式
        if self.stock_code and not re.match(r'^[0-9]{6}$', self.stock_code):
            # 支持 SH/SZ 前缀
            if not re.match(r'^(SH|SZ)[0-9]{6}$', self.stock_code):
                errors.append(f"证券代码格式错误：{self.stock_code}")
        
        # 验证数量
        if self.volume and not self.volume.isdigit():
            errors.append(f"委托数量必须为数字：{self.volume}")
        
        # 验证价格类型
        valid_price_types = ['18', '19', '3', '6', 'M1', 'M2', 'M5', 'M6', 'M8', 
                           '9001', '9002', '9003', '9004', '13', '17', '24', '106']
        if self.price_type and self.price_type not in valid_price_types:
            errors.append(f"委托价格类型未知：{self.price_type}")
        
        return (len(errors) == 0, errors)
    
    def get_direction(self) -> str:
        """
        获取买卖方向
        
        Returns:
            'BUY' 或 'SELL'
        """
        # 根据迅投数据字典
        buy_types = ['18', '1', 'BUY']
        sell_types = ['19', '2', 'SELL']
        
        if self.price_type in buy_types:
            return 'BUY'
        elif self.price_type in sell_types:
            return 'SELL'
        else:
            # 根据 order_type 判断
            # 这里需要根据完整的数据字典
            return 'UNKNOWN'


class DBFParser:
    """
    DBF 预埋单文件解析器
    
    支持格式：
    - .dbf 文件（原生 DBF 格式）
    - .xlsx 文件（Excel 导出格式）
    - .csv 文件（CSV 导出格式）
    """
    
    # 字段映射（中文列名转英文）
    FIELD_MAPPING = {
        '下单类型': 'order_type',
        '委托价格类型': 'price_type',
        '委托价格': 'mode_price',
        '证券代码': 'stock_code',
        '委托数量': 'volume',
        '下单资金账号': 'account_id',
        '账号类别': 'act_type',
        '账号类型': 'brokertype',
        '策略备注': 'strategy',
        '投资备注': 'note',
        '投资备注 2': 'note1',
        '交易参数': 'tradeparam',
        '指令编号': 'command_id',
        '文件路径': 'basketpath',
        '文件绝对路径': 'basketpath',
        '写入时间': 'inserttime',
        '额外参数': 'extraparam',
        '批次 ID': 'batch_id',
        '序号': 'index',
        '字段名': 'field_name',
        '类型': 'type',
        '说明': 'description',
        '必填': 'required',
        '备注': 'remark',
        '表头必有': 'header_required',
    }
    
    # 必填字段
    REQUIRED_FIELDS = ['order_type', 'price_type', 'stock_code', 'volume', 'account_id']
    
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.orders: List[DBFOrder] = []
        self.df: Optional[pd.DataFrame] = None
        self.parse_errors: List[str] = []
        self.validation_errors: List[str] = []
        
    def parse(self) -> List[DBFOrder]:
        """解析文件"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在：{self.file_path}")
        
        suffix = self.file_path.suffix.lower()
        
        if suffix == '.dbf':
            self._parse_dbf()
        elif suffix in ['.xlsx', '.xls']:
            self._parse_excel()
        elif suffix == '.csv':
            self._parse_csv()
        else:
            raise ValueError(f"不支持的文件格式：{suffix}")
        
        # 验证订单
        self._validate_orders()
        
        return self.orders
    
    def _parse_dbf(self):
        """解析 DBF 文件"""
        try:
            from dbfread import DBF
            dbf = DBF(str(self.file_path), encoding='gbk')
            
            records = []
            for record in dbf:
                records.append(record)
            
            self.df = pd.DataFrame(records)
            self._convert_to_orders()
            
        except ImportError:
            self.parse_errors.append("缺少 dbfread 库，尝试用 Excel 格式读取")
            self._parse_excel()
        except Exception as e:
            self.parse_errors.append(f"DBF 解析错误：{str(e)}")
    
    def _parse_excel(self):
        """解析 Excel 文件"""
        try:
            # 尝试读取"详情"工作表
            try:
                self.df = pd.read_excel(
                    self.file_path,
                    sheet_name='详情',
                    engine='openpyxl'
                )
            except:
                # 如果没有"详情"表，读取第一个工作表
                self.df = pd.read_excel(
                    self.file_path,
                    sheet_name=0,
                    engine='openpyxl'
                )
            
            self._convert_to_orders()
            
        except Exception as e:
            self.parse_errors.append(f"Excel 解析错误：{str(e)}")
    
    def _parse_csv(self):
        """解析 CSV 文件"""
        try:
            self.df = pd.read_csv(
                self.file_path,
                encoding='gbk'
            )
            self._convert_to_orders()
            
        except Exception as e:
            self.parse_errors.append(f"CSV 解析错误：{str(e)}")
    
    def _convert_to_orders(self):
        """将 DataFrame 转换为 DBFOrder 对象列表"""
        if self.df is None or self.df.empty:
            return
        
        # 标准化列名
        self.df = self._normalize_columns(self.df)
        
        # 检查是否有必要的列
        if not any(col in self.df.columns for col in self.REQUIRED_FIELDS):
            self.parse_errors.append("文件中未找到必要的订单数据列")
            return
        
        # 转换为 DBFOrder 对象
        for idx, row in self.df.iterrows():
            try:
                order = DBFOrder(
                    order_type=str(row.get('order_type', '')).strip(),
                    price_type=str(row.get('price_type', '')).strip(),
                    stock_code=str(row.get('stock_code', '')).strip(),
                    volume=str(row.get('volume', '')).strip(),
                    account_id=str(row.get('account_id', '')).strip(),
                    mode_price=str(row.get('mode_price', '')).strip() if pd.notna(row.get('mode_price')) else None,
                    act_type=str(row.get('act_type', '')).strip() if pd.notna(row.get('act_type')) else None,
                    brokertype=str(row.get('brokertype', '')).strip() if pd.notna(row.get('brokertype')) else None,
                    strategy=str(row.get('strategy', '')).strip() if pd.notna(row.get('strategy')) else None,
                    note=str(row.get('note', '')).strip() if pd.notna(row.get('note')) else None,
                    note1=str(row.get('note1', '')).strip() if pd.notna(row.get('note1')) else None,
                    tradeparam=str(row.get('tradeparam', '')).strip() if pd.notna(row.get('tradeparam')) else None,
                    command_id=str(row.get('command_id', '')).strip() if pd.notna(row.get('command_id')) else None,
                    basketpath=str(row.get('basketpath', '')).strip() if pd.notna(row.get('basketpath')) else None,
                    inserttime=str(row.get('inserttime', '')).strip() if pd.notna(row.get('inserttime')) else None,
                    extraparam=str(row.get('extraparam', '')).strip() if pd.notna(row.get('extraparam')) else None,
                    batch_id=str(row.get('batch_id', '')).strip() if pd.notna(row.get('batch_id')) else None,
                )
                self.orders.append(order)
                
            except Exception as e:
                self.parse_errors.append(f"行{idx+1}转换错误：{str(e)}")
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名（中文转英文）"""
        # 创建列名映射（反向）
        reverse_mapping = {v: k for k, v in self.FIELD_MAPPING.items()}
        
        # 重命名列
        new_columns = {}
        for col in df.columns:
            col_clean = str(col).strip()
            
            # 直接匹配
            if col_clean in self.FIELD_MAPPING:
                new_columns[col_clean] = self.FIELD_MAPPING[col_clean]
            else:
                # 模糊匹配
                matched = False
                for cn, en in self.FIELD_MAPPING.items():
                    if cn in col_clean or col_clean in cn:
                        new_columns[col_clean] = en
                        matched = True
                        break
                
                if not matched:
                    # 保留原列名
                    new_columns[col_clean] = col_clean
        
        df = df.rename(columns=new_columns)
        return df
    
    def _validate_orders(self):
        """验证所有订单"""
        self.validation_errors = []
        
        for i, order in enumerate(self.orders):
            valid, errors = order.validate()
            if not valid:
                for error in errors:
                    self.validation_errors.append(f"订单{i+1}: {error}")
    
    def validate(self) -> bool:
        """验证所有订单"""
        if not self.orders:
            return False
        
        self._validate_orders()
        return len(self.validation_errors) == 0
    
    def get_summary(self) -> Dict:
        """获取解析摘要"""
        return {
            'file_path': str(self.file_path),
            'total_orders': len(self.orders),
            'parse_errors': len(self.parse_errors),
            'validation_errors': len(self.validation_errors),
            'errors': self.parse_errors[:5] + self.validation_errors[:5],
            'unique_stocks': len(set(o.stock_code for o in self.orders)),
            'unique_accounts': len(set(o.account_id for o in self.orders)),
            'buy_orders': len([o for o in self.orders if o.get_direction() == 'BUY']),
            'sell_orders': len([o for o in self.orders if o.get_direction() == 'SELL']),
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        if not self.orders:
            return pd.DataFrame()
        
        return pd.DataFrame([o.to_dict() for o in self.orders])
    
    def filter_orders(self, 
                     stock_code: Optional[str] = None,
                     account_id: Optional[str] = None,
                     direction: Optional[str] = None) -> List[DBFOrder]:
        """
        筛选订单
        
        Args:
            stock_code: 证券代码
            account_id: 资金账号
            direction: 买卖方向 ('BUY' 或 'SELL')
        
        Returns:
            筛选后的订单列表
        """
        result = self.orders
        
        if stock_code:
            result = [o for o in result if o.stock_code == stock_code]
        
        if account_id:
            result = [o for o in result if o.account_id == account_id]
        
        if direction:
            result = [o for o in result if o.get_direction() == direction]
        
        return result
