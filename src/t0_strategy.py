"""
T0 策略模块 - 完整版

支持手动 T0 交易的策略执行和监控
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .position_calc import T0Position, Position


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
    4. 底仓管理
    """
    
    # 默认策略参数
    DEFAULT_PARAMS = {
        'sell_premium': 0.002,  # 卖出溢价 0.2%
        'buy_discount': 0.002,  # 买入折价 0.2%
        'min_t0_volume': 100,  # 最小 T0 数量
        'max_t0_ratio': 0.5,  # 最大 T0 比例（相对于底仓）
    }
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.signals: List[T0Signal] = []
        self.executed_signals: List[T0Signal] = []
    
    def generate_signals(
        self,
        t0_positions: Dict[str, T0Position],
        prices: Dict[str, float],
        positions: Optional[Dict[str, Position]] = None
    ) -> List[T0Signal]:
        """
        生成 T0 交易信号
        
        Args:
            t0_positions: T0 仓位字典
            prices: 当前价格字典
            positions: 普通仓位字典（用于底仓检查）
        
        Returns:
            T0Signal 列表
        """
        self.signals = []
        
        for key, pos in t0_positions.items():
            stock_code = pos.stock_code
            current_price = prices.get(stock_code, 0)
            
            # 策略 1: T0 待完成配对
            if pos.t0_pending > 0:
                self._generate_pending_signals(pos, current_price)
            
            # 策略 2: 底仓做 T
            if positions:
                pos_key = f"{stock_code}_{pos.account_id}_{pos.strategy}"
                if pos_key in positions:
                    base_pos = positions[pos_key]
                    self._generate_base_t0_signals(base_pos, pos, current_price)
        
        # 按优先级排序
        self.signals.sort(key=lambda x: x.priority)
        
        return self.signals
    
    def _generate_pending_signals(self, t0_pos: T0Position, current_price: float):
        """生成待完成配对信号"""
        if t0_pos.t0_buy_volume > t0_pos.t0_sell_volume:
            # 买入多了，需要卖出
            signal = T0Signal(
                stock_code=t0_pos.stock_code,
                account_id=t0_pos.account_id,
                strategy=t0_pos.strategy,
                signal_type='SELL',
                target_volume=t0_pos.t0_pending,
                target_price=current_price * (1 + self.params['sell_premium']),
                reason=f"T0 待完成：买入{t0_pos.t0_buy_volume} > 卖出{t0_pos.t0_sell_volume}",
                priority=2,
                created_at=datetime.now().isoformat()
            )
            self.signals.append(signal)
        else:
            # 卖出多了，需要买入回补
            signal = T0Signal(
                stock_code=t0_pos.stock_code,
                account_id=t0_pos.account_id,
                strategy=t0_pos.strategy,
                signal_type='BUY',
                target_volume=t0_pos.t0_pending,
                target_price=current_price * (1 - self.params['buy_discount']),
                reason=f"T0 待完成：卖出{t0_pos.t0_sell_volume} > 买入{t0_pos.t0_buy_volume}",
                priority=2,
                created_at=datetime.now().isoformat()
            )
            self.signals.append(signal)
    
    def _generate_base_t0_signals(self, base_pos: Position, t0_pos: T0Position, current_price: float):
        """生成底仓做 T 信号"""
        # 检查是否有足够的可用仓位做 T
        available_for_t0 = base_pos.available_volume - t0_pos.t0_buy_volume
        
        if available_for_t0 >= self.params['min_t0_volume']:
            # 计算最大 T0 数量
            max_t0_volume = int(base_pos.total_volume * self.params['max_t0_ratio'])
            target_volume = min(available_for_t0, max_t0_volume, 1000)  # 最多 1000 股
            
            if target_volume >= self.params['min_t0_volume']:
                # 生成高抛信号
                signal = T0Signal(
                    stock_code=base_pos.stock_code,
                    account_id=base_pos.account_id,
                    strategy=base_pos.strategy,
                    signal_type='SELL',
                    target_volume=target_volume,
                    target_price=current_price * (1 + self.params['sell_premium']),
                    reason=f"底仓做 T：可用{available_for_t0}股，目标{target_volume}股",
                    priority=3,
                    created_at=datetime.now().isoformat()
                )
                self.signals.append(signal)
    
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
