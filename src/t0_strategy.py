"""
T0 策略模块

支持手动 T0 交易的策略执行和监控
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .position_calc import T0Position


@dataclass
class T0Signal:
    """T0 交易信号"""
    stock_code: str
    account_id: str
    strategy: str
    signal_type: str  # 'BUY' or 'SELL'
    target_volume: int
    target_price: Optional[float]
    reason: str
    priority: int = 1  # 优先级 1-5
    created_at: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'stock_code': self.stock_code,
            'account_id': self.account_id,
            'strategy': self.strategy,
            'signal_type': self.signal_type,
            'target_volume': self.target_volume,
            'target_price': self.target_price,
            'reason': self.reason,
            'priority': self.priority,
            'created_at': self.created_at,
        }


class T0Strategy:
    """
    T0 策略引擎
    
    功能：
    1. 生成 T0 交易信号
    2. 监控 T0 执行状态
    3. 计算 T0 收益
    """
    
    def __init__(self):
        self.signals: List[T0Signal] = []
        self.executed_signals: List[T0Signal] = []
        
    def generate_signals(
        self,
        t0_positions: Dict[str, T0Position],
        prices: Dict[str, float],
        strategy_params: Optional[Dict] = None
    ) -> List[T0Signal]:
        """
        生成 T0 交易信号
        
        Args:
            t0_positions: T0 仓位字典
            prices: 当前价格字典
            strategy_params: 策略参数
            
        Returns:
            T0Signal 列表
        """
        self.signals = []
        params = strategy_params or {}
        
        for key, pos in t0_positions.items():
            stock_code = pos.stock_code
            current_price = prices.get(stock_code, 0)
            
            # 策略 1: T0 待完成配对
            if pos.t0_pending > 0:
                if pos.t0_buy_volume > pos.t0_sell_volume:
                    # 买入多了，需要卖出
                    signal = T0Signal(
                        stock_code=stock_code,
                        account_id=pos.account_id,
                        strategy=pos.strategy,
                        signal_type='SELL',
                        target_volume=pos.t0_pending,
                        target_price=current_price * (1 + params.get('sell_premium', 0.002)),
                        reason=f"T0 待完成：买入{pos.t0_buy_volume} > 卖出{pos.t0_sell_volume}",
                        priority=2,
                        created_at=datetime.now().isoformat()
                    )
                    self.signals.append(signal)
                else:
                    # 卖出多了，需要买入回补
                    signal = T0Signal(
                        stock_code=stock_code,
                        account_id=pos.account_id,
                        strategy=pos.strategy,
                        signal_type='BUY',
                        target_volume=pos.t0_pending,
                        target_price=current_price * (1 - params.get('buy_discount', 0.002)),
                        reason=f"T0 待完成：卖出{pos.t0_sell_volume} > 买入{pos.t0_buy_volume}",
                        priority=2,
                        created_at=datetime.now().isoformat()
                    )
                    self.signals.append(signal)
            
            # 策略 2: 底仓做 T
            if pos.base_volume > 0:
                # 检查是否有足够的可用仓位做 T
                available_for_t0 = pos.base_volume - pos.t0_buy_volume
                
                if available_for_t0 > 100:  # 至少 100 股
                    # 生成高抛信号
                    signal = T0Signal(
                        stock_code=stock_code,
                        account_id=pos.account_id,
                        strategy=pos.strategy,
                        signal_type='SELL',
                        target_volume=min(available_for_t0, 1000),  # 最多 1000 股
                        target_price=current_price * (1 + params.get('sell_premium', 0.002)),
                        reason=f"底仓做 T：可用{available_for_t0}股",
                        priority=3,
                        created_at=datetime.now().isoformat()
                    )
                    self.signals.append(signal)
        
        # 按优先级排序
        self.signals.sort(key=lambda x: x.priority)
        
        return self.signals
    
    def get_signal_summary(self) -> Dict:
        """获取信号摘要"""
        if not self.signals:
            return {'total_signals': 0}
        
        buy_signals = [s for s in self.signals if s.signal_type == 'BUY']
        sell_signals = [s for s in self.signals if s.signal_type == 'SELL']
        
        return {
            'total_signals': len(self.signals),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'total_buy_volume': sum(s.target_volume for s in buy_signals),
            'total_sell_volume': sum(s.target_volume for s in sell_signals),
            'signals': [s.to_dict() for s in self.signals],
        }
