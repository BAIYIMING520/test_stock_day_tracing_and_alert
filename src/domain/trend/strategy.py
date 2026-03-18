#!/usr/bin/env python3
"""
趋势分析领域 - 多函数拟合判断股票短期趋势
"""
import numpy as np
from typing import List, Dict

from src.infrastructure.database import get_minute_data


class TrendStrategy:
    """多函数拟合趋势判断"""

    def __init__(self, prices: List[float]):
        self.prices = np.array(prices)
        self.x = np.arange(len(prices))

    def linear_fit(self) -> Dict:
        """一次函数拟合: y = ax + b"""
        coef = np.polyfit(self.x, self.prices, 1)
        return {
            'func': 'linear',
            'a': coef[0],
            'trend': 'up' if coef[0] > 0 else 'down',
            'strength': abs(coef[0])
        }

    def quadratic_fit(self) -> Dict:
        """二次函数拟合: y = ax² + bx + c"""
        coef = np.polyfit(self.x, self.prices, 2)
        return {
            'func': 'quadratic',
            'a': coef[0],
            'b': coef[1],
            'trend': 'up' if coef[0] > 0 else 'down',
            'vertex_x': -coef[1] / (2 * coef[0]) if coef[0] != 0 else 0
        }

    def cubic_fit(self) -> Dict:
        """三次函数拟合: y = ax³ + bx² + cx + d"""
        coef = np.polyfit(self.x, self.prices, 3)
        start_price = self.prices[0]
        end_price = self.prices[-1]
        change = (end_price - start_price) / start_price * 100
        return {
            'func': 'cubic',
            'a': coef[0],
            'trend': 'up' if end_price > start_price else 'down',
            'change_pct': change
        }

    def analyze(self) -> Dict:
        """综合分析三条拟合曲线，返回信号"""
        r1 = self.linear_fit()
        r2 = self.quadratic_fit()
        r3 = self.cubic_fit()

        trends = [r1['trend'], r2['trend'], r3['trend']]
        up_count = trends.count('up')
        down_count = trends.count('down')

        if down_count == 3:
            conclusion = '下跌趋势确认 ⬇️'
            signal = 'SELL'
            confidence = '高'
        elif up_count == 3:
            conclusion = '上涨趋势确认 ⬆️'
            signal = 'BUY'
            confidence = '高'
        elif down_count >= 2:
            conclusion = '偏下跌 📉'
            signal = 'SELL'
            confidence = '中'
        elif up_count >= 2:
            conclusion = '偏上涨 📈'
            signal = 'BUY'
            confidence = '中'
        else:
            conclusion = '震荡整理 ➡️'
            signal = 'HOLD'
            confidence = '低'

        return {
            'linear': r1,
            'quadratic': r2,
            'cubic': r3,
            'up_count': up_count,
            'down_count': down_count,
            'conclusion': conclusion,
            'signal': signal,
            'confidence': confidence
        }


def analyze_stock(code: str) -> Dict:
    """分析某只股票的趋势"""
    data = get_minute_data(code)
    if not data:
        return {'error': '没有分时数据'}

    prices = [d['close'] for d in data]
    strategy = TrendStrategy(prices)
    result = strategy.analyze()
    result['data_count'] = len(data)
    result['price_range'] = f"{min(prices):.2f} ~ {max(prices):.2f}"
    return result
