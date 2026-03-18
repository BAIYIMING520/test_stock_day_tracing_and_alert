#!/usr/bin/env python3
"""
拟合分析领域 - 线性回归拟合与趋势分析
"""
import numpy as np
from typing import List, Tuple, Optional


def calculate_r_squared(y_true: List[float], y_pred: List[float]) -> float:
    """计算 R² 决定系数"""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return 1 - (ss_res / ss_tot)


def fit_linear(points: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    """一次线性拟合 y = ax + b

    Returns:
        a, b, r_squared
    """
    if len(points) < 2:
        return 0.0, 0.0, 0.0

    x = np.array([p[0] for p in points])
    y = np.array([p[1] for p in points])

    coef = np.polyfit(x, y, 1)
    a, b = coef[0], coef[1]
    y_pred = a * x + b
    r2 = calculate_r_squared(y, y_pred)

    return a, b, r2


def analyze_trend(prices: List[float], window: int = 60) -> dict:
    """分析价格趋势

    Args:
        prices: 价格列表
        window: 分析窗口大小

    Returns:
        包含趋势方向、斜率、置信度等
    """
    if len(prices) < window:
        window = len(prices)

    recent = prices[-window:]
    x = np.arange(len(recent))
    coef = np.polyfit(x, recent, 1)
    slope = coef[0]

    # 归一化斜率（相对价格均值）
    mean_price = np.mean(recent)
    normalized_slope = slope / mean_price * 100 if mean_price > 0 else 0

    return {
        'window': window,
        'slope': slope,
        'normalized_slope': normalized_slope,
        'trend': 'up' if slope > 0 else 'down',
        'mean_price': mean_price,
        'min_price': min(recent),
        'max_price': max(recent),
    }
