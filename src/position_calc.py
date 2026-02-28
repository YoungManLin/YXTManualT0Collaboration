"""
仓位计算核心模块 - 完整版

支持：
- 实时仓位计算
- T0 交易仓位管理
- 多账户/多策略仓位汇总
- 盈亏计算
- 批次合并
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
    t0_profit: float = 0.0  # T0 盈亏
    
    def to_dict(self) -> Dict:
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
            't0_profit': self.t0_profit,
        }


@dataclass
class T0Position:
    """T0 交易仓位数据类"""
    stock_code: str
    account_id: str
    strategy: str
    base_volume: int = 0  # 底仓数量
    t0_buy_volume: int = 0  # T0 买入数量
    t0_sell_volume: int = 0  # T0 卖出数量
    t0_completed: int = 0  # T0 完成数量（配对成功）
    t0_pending: int = 0  # T0 待完成数量
    t0_profit: float = 0.0  # T0 盈亏
    avg_buy_price: float = 0.0  # T0 平均买入价
    avg_sell_price: float = 0.0  # T0 平均卖出价
    
    def to_dict(self) -> Dict:
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
    5. 批次合并
    """
    
    # 买卖方向映射
    DIRECTION_MAP = {
        '18': 'BUY',   # 买入
        '19': 'SELL',  # 卖出
        '1': 'BUY',
        '2': 'SELL',
    }
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.t0_positions: Dict[str, T0Position] = {}
        self.orders: List[DBFOrder] = []
        self.trades: List[Dict] = []
        self.prices: Dict[str, float] = {}
        
    def load_orders(self, orders: List[DBFOrder]):
        """加载委托订单"""
        self.orders = orders
    
    def load_trades(self, trades: List[Dict]):
        """
        加载成交记录
        
        trades: [{
            'stock_code': '600000',
            'account_id': 'ACC001',
            'strategy': 'STRAT1',
            'direction': 'BUY',
            'volume': 1000,
            'price': 14.2,
            'trade_time': '2026-02-28 10:30:00'
        }, ...]
        """
        self.trades = trades
    
    def set_prices(self, prices: Dict[str, float]):
        """设置当前价格"""
        self.prices = prices
    
    def calculate(self) -> Dict[str, Position]:
        """计算仓位"""
        self.positions = {}
        
        # 1. 根据成交记录计算实际持仓
        if self.trades:
            self._calculate_from_trades()
        else:
            # 如果没有成交记录，根据订单估算
            self._calculate_from_orders()
        
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
    
    def _calculate_from_orders(self):
        """根据订单估算持仓（简化版本）"""
        order_groups = defaultdict(list)
        
        for order in self.orders:
            key = self._make_position_key(
                order.stock_code,
                order.account_id,
                order.strategy or 'DEFAULT'
            )
            order_groups[key].append(order)
        
        for key, orders in order_groups.items():
            stock_code = orders[0].stock_code
            account_id = orders[0].account_id
            strategy = orders[0].strategy or 'DEFAULT'
            
            # 计算买卖数量
            buy_volume = sum(int(o.volume) for o in orders if o.get_direction() == 'BUY' and o.volume.isdigit())
            sell_volume = sum(int(o.volume) for o in orders if o.get_direction() == 'SELL' and o.volume.isdigit())
            
            # 估算持仓
            total_volume = buy_volume - sell_volume
            
            if total_volume > 0:
                self.positions[key] = Position(
                    stock_code=stock_code,
                    account_id=account_id,
                    strategy=strategy,
                    total_volume=total_volume,
                    available_volume=total_volume,
                    current_price=self.prices.get(stock_code, 0),
                )
    
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
            direction = order.get_direction()
            
            if direction == 'BUY':
                pos.buy_volume += volume
                pos.frozen_volume += volume
            elif direction == 'SELL':
                pos.sell_volume += volume
                pos.frozen_volume += volume
        
        # 更新可用数量
        for pos in self.positions.values():
            pos.available_volume = max(0, pos.total_volume - pos.frozen_volume)
    
    def _calculate_market_value_and_pl(self):
        """计算市值和盈亏"""
        for key, pos in self.positions.items():
            # 市值
            pos.market_value = pos.total_volume * pos.current_price
            
            # 盈亏
            if pos.total_volume > 0 and pos.avg_cost > 0:
                pos.profit_loss = (pos.current_price - pos.avg_cost) * pos.total_volume
                pos.profit_loss_ratio = (pos.current_price - pos.avg_cost) / pos.avg_cost
            
            # 可用数量
            pos.available_volume = max(0, pos.total_volume - pos.frozen_volume)
    
    def calculate_t0(self) -> Dict[str, T0Position]:
        """计算 T0 交易仓位"""
        self.t0_positions = {}
        
        # 按股票 + 账户分组订单
        order_groups = defaultdict(list)
        for order in self.orders:
            key = f"{order.stock_code}_{order.account_id}_{order.strategy or 'DEFAULT'}"
            order_groups[key].append(order)
        
        # 计算每个分组的 T0 仓位
        for key, orders in order_groups.items():
            t0_pos = T0Position(
                stock_code=orders[0].stock_code,
                account_id=orders[0].account_id,
                strategy=orders[0].strategy or 'DEFAULT'
            )
            
            # 统计 T0 买卖数量
            for order in orders:
                volume = int(order.volume) if order.volume.isdigit() else 0
                direction = order.get_direction()
                
                if direction == 'BUY':
                    t0_pos.t0_buy_volume += volume
                elif direction == 'SELL':
                    t0_pos.t0_sell_volume += volume
            
            # 计算 T0 配对
            t0_pos.t0_completed = min(t0_pos.t0_buy_volume, t0_pos.t0_sell_volume)
            t0_pos.t0_pending = abs(t0_pos.t0_buy_volume - t0_pos.t0_sell_volume)
            
            self.t0_positions[key] = t0_pos
        
        return self.t0_positions
    
    def _make_position_key(self, stock_code: str, account_id: str, strategy: str) -> str:
        """生成仓位唯一键"""
        return f"{stock_code}_{account_id}_{strategy}"
    
    def get_summary(self) -> Dict:
        """获取仓位摘要"""
        if not self.positions:
            return {'total_positions': 0}
        
        total_market_value = sum(p.market_value for p in self.positions.values())
        total_profit_loss = sum(p.profit_loss for p in self.positions.values())
        total_t0_profit = sum(p.t0_profit for p in self.positions.values())
        
        return {
            'total_positions': len(self.positions),
            'total_market_value': total_market_value,
            'total_profit_loss': total_profit_loss,
            'total_t0_profit': total_t0_profit,
            'profit_loss_ratio': total_profit_loss / total_market_value if total_market_value > 0 else 0,
            'positions': [p.to_dict() for p in self.positions.values()],
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        if not self.positions:
            return pd.DataFrame()
        return pd.DataFrame([p.to_dict() for p in self.positions.values()])
    
    def export_report(self, output_path: str):
        """导出仓位报告"""
        df = self.to_dataframe()
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='仓位明细', index=False)
            
            # 汇总信息
            summary = self.get_summary()
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, sheet_name='汇总', index=False)
