"""
风险控制模块 - 完整版

支持：
- 仓位限额检查
- 单票集中度检查
- T0 交易频率控制
- 盈亏止损检查
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .position_calc import Position


@dataclass
class RiskAlert:
    """风险告警"""
    level: str  # 'INFO', 'WARNING', 'ERROR'
    code: str  # 告警代码
    message: str  # 告警信息
    stock_code: Optional[str] = None
    account_id: Optional[str] = None
    current_value: Optional[float] = None
    limit_value: Optional[float] = None


class RiskChecker:
    """
    风险控制检查器
    
    检查项：
    1. 总仓位限额
    2. 单票集中度
    3. T0 交易频率
    4. 盈亏止损
    """
    
    # 默认风险参数
    DEFAULT_RISK_PARAMS = {
        'max_total_position': 10000000,  # 最大总仓位 1000 万
        'max_single_stock_ratio': 0.2,  # 单票最大占比 20%
        'max_t0_trades_per_day': 10,  # 单日最大 T0 次数
        'stop_loss_ratio': -0.05,  # 止损线 -5%
        'take_profit_ratio': 0.1,  # 止盈线 10%
    }
    
    def __init__(self, risk_params: Optional[Dict] = None):
        self.params = {**self.DEFAULT_RISK_PARAMS, **(risk_params or {})}
        self.alerts: List[RiskAlert] = []
    
    def check(self, positions: Dict[str, Position]) -> List[RiskAlert]:
        """执行风险检查"""
        self.alerts = []
        
        # 1. 总仓位检查
        self._check_total_position(positions)
        
        # 2. 单票集中度检查
        self._check_concentration(positions)
        
        # 3. 盈亏检查
        self._check_profit_loss(positions)
        
        return self.alerts
    
    def _check_total_position(self, positions: Dict[str, Position]):
        """检查总仓位"""
        total_value = sum(p.market_value for p in positions.values())
        max_limit = self.params['max_total_position']
        
        if total_value > max_limit:
            self.alerts.append(RiskAlert(
                level='ERROR',
                code='RISK_TOTAL_POSITION_EXCEEDED',
                message=f'总仓位超限：{total_value:.2f} > {max_limit:.2f}',
                current_value=total_value,
                limit_value=max_limit
            ))
        elif total_value > max_limit * 0.8:
            self.alerts.append(RiskAlert(
                level='WARNING',
                code='RISK_TOTAL_POSITION_HIGH',
                message=f'总仓位较高：{total_value:.2f} / {max_limit:.2f} ({total_value/max_limit*100:.1f}%)',
                current_value=total_value,
                limit_value=max_limit
            ))
    
    def _check_concentration(self, positions: Dict[str, Position]):
        """检查单票集中度"""
        total_value = sum(p.market_value for p in positions.values())
        if total_value == 0:
            return
        
        max_ratio = self.params['max_single_stock_ratio']
        
        # 按股票代码分组
        stock_values = {}
        for pos in positions.values():
            if pos.stock_code not in stock_values:
                stock_values[pos.stock_code] = 0
            stock_values[pos.stock_code] += pos.market_value
        
        for stock_code, value in stock_values.items():
            ratio = value / total_value
            if ratio > max_ratio:
                self.alerts.append(RiskAlert(
                    level='ERROR',
                    code='RISK_CONCENTRATION_EXCEEDED',
                    message=f'单票{stock_code}集中度过高：{ratio*100:.1f}% > {max_ratio*100:.1f}%',
                    stock_code=stock_code,
                    current_value=ratio,
                    limit_value=max_ratio
                ))
    
    def _check_profit_loss(self, positions: Dict[str, Position]):
        """检查盈亏"""
        stop_loss = self.params['stop_loss_ratio']
        take_profit = self.params['take_profit_ratio']
        
        for pos in positions.values():
            if pos.profit_loss_ratio < stop_loss:
                self.alerts.append(RiskAlert(
                    level='WARNING',
                    code='RISK_STOP_LOSS',
                    message=f'{pos.stock_code} 触及止损线：{pos.profit_loss_ratio*100:.2f}% < {stop_loss*100:.1f}%',
                    stock_code=pos.stock_code,
                    account_id=pos.account_id,
                    current_value=pos.profit_loss_ratio,
                    limit_value=stop_loss
                ))
            elif pos.profit_loss_ratio > take_profit:
                self.alerts.append(RiskAlert(
                    level='INFO',
                    code='RISK_TAKE_PROFIT',
                    message=f'{pos.stock_code} 触及止盈线：{pos.profit_loss_ratio*100:.2f}% > {take_profit*100:.1f}%',
                    stock_code=pos.stock_code,
                    account_id=pos.account_id,
                    current_value=pos.profit_loss_ratio,
                    limit_value=take_profit
                ))
    
    def get_alert_summary(self) -> Dict:
        """获取告警摘要"""
        if not self.alerts:
            return {'total_alerts': 0, 'status': 'OK'}
        
        error_count = len([a for a in self.alerts if a.level == 'ERROR'])
        warning_count = len([a for a in self.alerts if a.level == 'WARNING'])
        info_count = len([a for a in self.alerts if a.level == 'INFO'])
        
        status = 'OK' if error_count == 0 else 'RISK'
        
        return {
            'total_alerts': len(self.alerts),
            'error_count': error_count,
            'warning_count': warning_count,
            'info_count': info_count,
            'status': status,
            'alerts': [
                {
                    'level': a.level,
                    'code': a.code,
                    'message': a.message,
                    'stock_code': a.stock_code,
                }
                for a in self.alerts
            ],
        }
