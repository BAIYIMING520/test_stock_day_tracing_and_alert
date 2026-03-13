#!/usr/bin/env python3
"""简单拟合/分析股票走势"""
import numpy as np

# 兆易创新今日数据
data = [
    ("09:30", 279.83), ("09:40", 278.50), ("09:50", 280.50), ("10:00", 282.00),
    ("10:10", 283.00), ("10:20", 283.83), ("10:30", 282.50), ("10:40", 281.00),
    ("10:50", 280.00), ("11:00", 279.00), ("11:10", 278.50), ("11:20", 278.00),
    ("11:30", 277.50), ("13:00", 277.50), ("13:10", 276.50), ("13:20", 275.50),
    ("13:30", 275.00), ("13:40", 274.50), ("13:50", 274.00), ("14:00", 273.50),
    ("14:10", 273.00), ("14:20", 272.50), ("14:30", 272.43), ("14:40", 273.00),
    ("14:50", 274.00), ("15:00", 274.78)
]

times = [d[0] for d in data]
prices = np.array([d[1] for d in data])
x = np.arange(len(prices))

print("=" * 60)
print("1. 线性回归趋势线")
print("=" * 60)
# 线性回归
coef = np.polyfit(x, prices, 1)
trend_line = np.poly1d(coef)
print(f"斜率: {coef[0]:.4f} (每10分钟变化)")
print(f"趋势线: y = {coef[0]:.4f}x + {coef[1]:.2f}")
print(f"开盘趋势预测: {trend_line(0):.2f}")
print(f"收盘趋势预测: {trend_line(26):.2f}")

print("\n" + "=" * 60)
print("2. 移动平均")
print("=" * 60)
# 5期均线
ma5 = np.convolve(prices, np.ones(5)/5, mode='valid')
print(f"5期均线(MA5): {ma5[-1]:.2f}")
# 10期均线
ma10 = np.convolve(prices, np.ones(10)/10, mode='valid')
print(f"10期均线(MA10): {ma10[-1]:.2f}")

print("\n" + "=" * 60)
print("3. 波动率分析")
print("=" * 60)
# 振幅
max_p = np.max(prices)
min_p = np.min(prices)
open_p = prices[0]
close_p = prices[-1]
print(f"最高: {max_p:.2f}")
print(f"最低: {min_p:.2f}")
print(f"开盘: {open_p:.2f}")
print(f"收盘: {close_p:.2f}")
print(f"振幅: {(max_p-min_p)/open_p*100:.2f}%")
print(f"涨跌: {(close_p-open_p)/open_p*100:.2f}%")

# 每段变化
changes = np.diff(prices)
print(f"\n最大单段涨幅: {np.max(changes):.2f}")
print(f"最大单段跌幅: {np.min(changes):.2f}")

print("\n" + "=" * 60)
print("4. 多项式拟合(3阶)")
print("=" * 60)
coef3 = np.polyfit(x, prices, 3)
poly3 = np.poly1d(coef3)
print(f"拟合函数: y = {coef3[0]:.6f}x³ + {coef3[1]:.4f}x² + {coef3[2]:.4f}x + {coef3[3]:.2f}")
print(f"拟合值(开盘): {poly3(0):.2f}, 实际: {prices[0]}")
print(f"拟合值(收盘): {poly3(26):.2f}, 实际: {prices[-1]}")
