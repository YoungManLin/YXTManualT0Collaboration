"""
仓位计算核心模块

支持：
- 实时仓位计算
- T0 交易仓位管理
- 多账户/多策略仓位汇总
- 盈亏计算
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from .dbf_parser import DBFOrder


@dataclass
class Position:
    """仓位数据类"""
    stock_code: str  # 证券代码
    account_id: str  # 资金账号
    strategy: str  # 策略名称
    total_volume: int = 0  # 总持仓数量
    available_volume: int = 0  # 可用数量
    frozen_volume: int = 0  # 冻结数量
    buy_volume: int = 0  # 买入委托数量
    sell_volume: int = 0  # 卖出委托数量
    avg_cost: float = 0.0  # 平均成本
    current_price: float = 0.0  # 当前价格
    market_value: float = 0.0  # 市值
    profit_loss: float = 0.0  # 盈亏
    profit_loss_ratio: float = 0.0  # 盈亏比例
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'account_id': self.account_id,
            'strategy': self.strategy,
            'total_volume': self.total_volume,
            'available_volume': self.available_volume,
            'frozen_volume': self.frozen_volume,
            'buy_volume': self.buy_volume,
            'sell_volume': self.sell_volume,
            'avg_cost': self.avg_cost,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'profit_loss': self.profit_loss,
            'profit_loss_ratio': self.profit_loss_ratio,
        }


@dataclass
class T0Position:
    """T0 交易仓位数据类"""
    stock_code: str  # 证券代码
    account_id: str  # 资金账号
    strategy: str  # 策略名称
    base_volume: int = 0  # 底仓数量
    t0_buy_volume: int = 0  # T0 买入数量
    t0_sell_volume: int = 0  # T0 卖出数量
    t0_completed: int = 0  # T0 完成数量（配对成功）
    t0_pending: int = 0  # T0 待完成数量
    t0_profit: float = 0.0  # T0 盈亏
    avg_buy_price: float = 0.0  # T0 平均买入价
    avg_sell_price: float = 0.0  # T0 平均卖出价
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'account_id': self.account_id,
            'strategy': self.strategy,
            'base_volume': self.base_volume,
            't0_buy_volume': self.t0_buy_volume,
            't0_sell_volume': self.t0_sell_volume,
            't0_completed': self.t0_completed,
            't0_pending': self.t0_pending,
            't0_profit': self.t0_profit,
            'avg_buy_price': self.avg_buy_price,
            'avg_sell_price': self.avg_sell_price,
        }


class PositionCalculator:
    """
    仓位计算器
    
    核心功能：
    1. 根据 DBF 委托文件计算仓位
    2. 支持 T0 交易仓位管理
    3. 多账户/多策略汇总
    4. 盈亏计算
    """
    
    # 买卖方向映射（迅投 DBF 数据字典）
    DIRECTION_MAP = {
        '18': 'BUY',   # 买入
        '19': 'SELL',  # 卖出
        '1': 'BUY',    # 买入（备用）
        '2': 'SELL',   # 卖出（备用）
    }
    
    def __init__(self):
        """初始化仓位计算器"""
        self.positions: Dict[str, Position] = {}  # key: stock_code+account_id+strategy
        self.t0_positions: Dict[str, T0Position] = {}  # T0 仓位
        self.orders: List[DBFOrder] = []
        self.trades: List[Dict] = []  # 成交记录
        self.prices: Dict[str, float] = {}  # 当前价格 {stock_code: price}
        
    def load_orders(self, orders: List[DBFOrder]):
        """
        加载委托订单
        
        Args:
            orders: DBFOrder 对象列表
        """
        self.orders = orders
    
    def load_trades(self, trades: List[Dict]):
        """
        加载成交记录
        
        Args:
            trades: 成交记录列表，每条记录包含：
                   - stock_code: 证券代码
                   - account_id: 资金账号
                   - strategy: 策略名称
                   - direction: 买卖方向 (BUY/SELL)
                   - volume: 成交数量
                   - price: 成交价格
                   - trade_time: 成交时间
        """
        self.trades = trades
    
    def set_prices(self, prices: Dict[str, float]):
        """
        设置当前价格
        
        Args:
            prices: {stock_code: current_price} 字典
        """
        self.prices = prices
    
    def calculate(self) -> Dict[str, Position]:
        """
        计算仓位
        
        Returns:
            {position_key: Position} 字典
        """
        self.positions = {}
        
        # 1. 根据成交记录计算实际持仓
        self._calculate_from_trades()
        
        # 2. 根据委托记录计算冻结仓位
        self._calculate_frozen_from_orders()
        
        # 3. 计算市值和盈亏
        self._calculate_market_value_and_pl()
        
        return self.positions
    
    def _calculate_from_trades(self):
        """根据成交记录计算持仓"""
        for trade in self.trades:
            key = self._make_position_key(
                trade['stock_code'],
                trade['account_id'],
                trade.get('strategy', 'DEFAULT')
            )
            
            if key not in self.positions:
                self.positions[key] = Position(
                    stock_code=trade['stock_code'],
                    account_id=trade['account_id'],
                    strategy=trade.get('strategy', 'DEFAULT')
                )
            
            pos = self.positions[key]
            direction = trade.get('direction', 'BUY')
            volume = int(trade.get('volume', 0))
            price = float(trade.get('price', 0))
            
            if direction == 'BUY':
                # 买入：增加持仓，更新平均成本
                total_cost = pos.avg_cost * pos.total_volume + price * volume
                pos.total_volume += volume
                pos.avg_cost = total_cost / pos.total_volume if pos.total_volume > 0 else 0
            elif direction == 'SELL':
                # 卖出：减少持仓
                pos.total_volume = max(0, pos.total_volume - volume)
            
            # 更新当前价格
            if trade['stock_code'] in self.prices:
                pos.current_price = self.prices[trade['stock_code']]
    
    def _calculate_frozen_from_orders(self):
        """根据委托记录计算冻结仓位"""
        for order in self.orders:
            key = self._make_position_key(
                order.stock_code,
                order.account_id,
                order.strategy or 'DEFAULT'
            )
            
            if key not in self.positions:
                self.positions[key] = Position(
                    stock_code=order.stock_code,
                    account_id=order.account_id,
                    strategy=order.strategy or 'DEFAULT'
                )
            
            pos = self.positions[key]
            volume = int(order.volume) if order.volume.isdigit() else 0
            
            # 根据委托类型判断买卖方向
            direction = self._get_order_direction(order)
            
            if direction == 'BUY':
                pos.buy_volume += volume
                pos.frozen_volume += volume
            elif direction == 'SELL':
                pos.sell_volume += volume
                # 卖出冻结的是持仓
                pos.frozen_volume += volume
    
    def _calculate_market_value_and_pl(self):
        """计算市值和盈亏"""
        for key, pos in self.positions.items():
            # 市值 = 持仓数量 × 当前价格
            pos.market_value = pos.total_volume * pos.current_price
            
            # 盈亏 = (当前价格 - 平均成本) × 持仓数量
            if pos.total_volume > 0 and pos.avg_cost > 0:
                pos.profit_loss = (pos.current_price - pos.avg_cost) * pos.total_volume
                pos.profit_loss_ratio = (pos.current_price - pos.avg_cost) / pos.avg_cost
            
            # 可用数量 = 总持仓 - 冻结数量
            pos.available_volume = max(0, pos.total_volume - pos.frozen_volume)
    
    def calculate_t0(self) -> Dict[str, T0Position]:
        """
        计算 T0 交易仓位
        
        T0 交易特点：
        - 日内买入卖出配对
        - 底仓不变
        - 计算 T0 盈亏
        
        Returns:
            {t0_position_key: T0Position} 字典
        """
        self.t0_positions = {}
        
        # 按股票 + 账户分组交易记录
        trade_groups = defaultdict(list)
        for trade in self.trades:
            key = f"{trade['stock_code']}_{trade['account_id']}_{trade.get('strategy', 'DEFAULT')}"
            trade_groups[key].append(trade)
        
        # 对每个分组计算 T0
        for key, trades in trade_groups.items():
            # 按时间排序
            trades.sort(key=lambda x: x.get('trade_time', ''))
            
            t0_pos = T0Position(
                stock_code=trades[0]['stock_code'] if trades else '',
                account_id=trades[0]['account_id'] if trades else '',
                strategy=trades[0].get('strategy', 'DEFAULT') if trades else 'DEFAULT'
            )
            
            # T0 配对逻辑：买入和卖出配对
            buy_orders = []
            sell_orders = []
            
            for trade in trades:
                direction = trade.get('direction', 'BUY')
                volume = int(trade.get('volume', 0))
                price = float(trade.get('price', 0))
                
                if direction == 'BUY':
                    buy_orders.append({'volume': volume, 'price': price})
                    t0_pos.t0_buy_volume += volume
                elif direction == 'SELL':
                    sell_orders.append({'volume': volume, 'price': price})
                    t0_pos.t0_sell_volume += volume
            
            # 配对计算 T0 盈亏
            t0_completed, t0_profit = self._match_t0_trades(buy_orders, sell_orders)
            t0_pos.t0_completed = t0_completed
            t0_pos.t0_profit = t0_profit
            t0_pos.t0_pending = abs(t0_pos.t0_buy_volume - t0_pos.t0_sell_volume)
            
            self.t0_positions[key] = t0_pos
        
        return self.t0_positions
    
    def _match_t0_trades(self, buys: List[Dict], sells: List[Dict]) -> Tuple[int, float]:
        """
        T0 交易配对计算盈亏
        
        Args:
            buys: 买入记录列表 [{volume, price}, ...]
            sells: 卖出记录列表 [{volume, price}, ...]
            
        Returns:
            (completed_volume, profit) 配对数量和盈亏
        """
        completed = 0
        profit = 0.0
        
        buy_idx = 0
        sell_idx = 0
        
        while buy_idx < len(buys) and sell_idx < len(sells):
            buy = buys[buy_idx]
            sell = sells[sell_idx]
            
            # 配对数量
            match_volume = min(buy['volume'], sell['volume'])
            
            if match_volume > 0:
                # T0 盈亏 = (卖出价 - 买入价) × 数量
                profit += (sell['price'] - buy['price']) * match_volume
                completed += match_volume
                
                # 更新剩余数量
                buy['volume'] -= match_volume
                sell['volume'] -= match_volume
                
                if buy['volume'] == 0:
                    buy_idx += 1
                if sell['volume'] == 0:
                    sell_idx += 1
            else:
                break
        
        return completed, profit
    
    def _make_position_key(self, stock_code: str, account_id: str, strategy: str) -> str:
        """生成仓位唯一键"""
        return f"{stock_code}_{account_id}_{strategy}"
    
    def _get_order_direction(self, order: DBFOrder) -> str:
        """
        根据订单类型判断买卖方向
        
        Args:
            order: DBFOrder 对象
            
        Returns:
            'BUY' 或 'SELL'
        """
        order_type = order.order_type
        price_type = order.price_type
        
        # 根据迅投 DBF 数据字典判断
        # 这里简化处理，实际需要根据完整的数据字典
        if price_type in ['18', '1', 'BUY']:
            return 'BUY'
        elif price_type in ['19', '2', 'SELL']:
            return 'SELL'
        else:
            # 默认根据 order_type 判断
            # 具体映射需要参考数据字典
            return 'BUY'  # 默认买入
    
    def get_summary(self) -> Dict:
        """
        获取仓位摘要
        
        Returns:
            摘要信息字典
        """
        if not self.positions:
            return {'total_positions': 0}
        
        total_market_value = sum(p.market_value for p in self.positions.values())
        total_profit_loss = sum(p.profit_loss for p in self.positions.values())
        
        return {
            'total_positions': len(self.positions),
            'total_market_value': total_market_value,
            'total_profit_loss': total_profit_loss,
            'profit_loss_ratio': total_profit_loss / total_market_value if total_market_value > 0 else 0,
            'positions': [p.to_dict() for p in self.positions.values()],
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为 DataFrame
        
        Returns:
            包含所有仓位的 DataFrame
        """
        if not self.positions:
            return pd.DataFrame()
        
        return pd.DataFrame([p.to_dict() for p in self.positions.values()])
    
    def export_report(self, output_path: str):
        """
        导出仓位报告
        
        Args:
            output_path: 输出文件路径（.xlsx）
        """
        df = self.to_dataframe()
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='仓位明细', index=False)
            
            # 汇总信息
            summary = self.get_summary()
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, sheet_name='汇总', index=False)
