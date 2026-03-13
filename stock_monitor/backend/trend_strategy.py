#!/usr/bin/env python3
"""
多函数拟合趋势判断策略
一次函数 + 二次函数 + 三次函数 交叉验证
"""

import numpy as np
from typing import List, Dict

class TrendStrategy:
    """多函数拟合趋势判断"""
    
    def __init__(self, prices: List[float]):
        """
        Args:
            prices: 价格列表（按时间顺序）
        """
        self.prices = np.array(prices)
        self.x = np.arange(len(prices))
    
    def linear_fit(self) -> Dict:
        """一次函数拟合: y = ax + b"""
        coef = np.polyfit(self.x, self.prices, 1)
        return {
            'func': 'linear',
            'a': coef[0],  # 斜率
            'trend': 'up' if coef[0] > 0 else 'down',
            'strength': abs(coef[0])
        }
    
    def quadratic_fit(self) -> Dict:
        """二次函数拟合: y = ax² + bx + c"""
        coef = np.polyfit(self.x, self.prices, 2)
        return {
            'func': 'quadratic',
            'a': coef[0],  # 开口方向
            'b': coef[1],
            'trend': 'up' if coef[0] > 0 else 'down',
            'vertex_x': -coef[1] / (2 * coef[0]) if coef[0] != 0 else 0
        }
    
    def cubic_fit(self) -> Dict:
        """三次函数拟合: y = ax³ + bx² + cx + d"""
        coef = np.polyfit(self.x, self.prices, 3)
        # 判断趋势：直接看首尾价格更准确
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
        """综合分析"""
        r1 = self.linear_fit()
        r2 = self.quadratic_fit()
        r3 = self.cubic_fit()
        
        # 统计趋势
        trends = [r1['trend'], r2['trend'], r3['trend']]
        up_count = trends.count('up')
        down_count = trends.count('down')
        
        # 综合判断
        if down_count == 3:
            conclusion = '下跌趋势确认 ⬇️'
            signal = 'SELL'  # 可以做反T卖出
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
    """分析某只股票"""
    from database import get_minute_data
    
    data = get_minute_data(code)
    if not data:
        return {'error': '没有分时数据'}
    
    prices = [d['close'] for d in data]
    
    strategy = TrendStrategy(prices)
    result = strategy.analyze()
    
    result['data_count'] = len(data)
    result['price_range'] = f"{min(prices):.2f} ~ {max(prices):.2f}"
    
    return result


if __name__ == '__main__':
    # 测试：兆易创新
    data = [
        279.83, 278.50, 280.50, 282.00, 283.00, 283.83, 282.50, 281.00, 280.00, 279.00,
        278.50, 278.00, 277.50, 277.50, 276.50, 275.50, 275.00, 274.50, 274.00, 273.50,
        273.00, 272.50, 272.43, 273.00, 274.00, 274.78
    ]
    
    strategy = TrendStrategy(data)
    result = strategy.analyze()
    
    print("=" * 60)
    print("多函数拟合趋势分析")
    print("=" * 60)
    print(f"一次函数(线性): {result['linear']['trend']}, 斜率={result['linear']['a']:.4f}")
    print(f"二次函数:       {result['quadratic']['trend']}, a={result['quadratic']['a']:.6f}")
    print(f"三次函数:       {result['cubic']['trend']}, a={result['cubic']['a']:.8f}")
    print("-" * 60)
    print(f"上涨: {result['up_count']}/3, 下跌: {result['down_count']}/3")
    print(f"结论: {result['conclusion']}")
    print(f"信号: {result['signal']} (置信度: {result['confidence']})")
