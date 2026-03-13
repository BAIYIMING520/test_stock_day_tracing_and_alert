#!/usr/bin/env python3
"""
A股分时监控服务 - Web服务器
功能：前端管理界面 + 实时数据展示 + 分时图表
"""

from flask import Flask, render_template_string, jsonify, request
import threading
import time
import os
from datetime import datetime
import sys

sys.path.append(os.path.dirname(__file__))

from config import load_config, save_config, add_stock, remove_stock, get_stocks, is_trading_time
from client import EastMoneyClient, get_all_realtime
from database import init_db, get_minute_data

app = Flask(__name__)

# 初始化数据库
init_db()

# ==================== HTML模板 ====================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A股分时监控</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #00d4ff;
            margin-bottom: 20px;
            font-size: 28px;
        }
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #16213e;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #666;
        }
        .status-dot.active { background: #00ff88; animation: pulse 2s infinite; }
        .status-dot.inactive { background: #ff4444; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .add-form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: #16213e;
            color: #fff;
            font-size: 16px;
        }
        input[type="text"]::placeholder { color: #666; }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-add { background: #00d4ff; color: #1a1a2e; }
        .btn-add:hover { background: #00b8e6; }
        .btn-delete {
            background: #ff4757;
            color: #fff;
            padding: 6px 12px;
            font-size: 14px;
        }
        .btn-delete:hover { background: #ff3344; }
        .stock-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }
        .stock-card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            position: relative;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stock-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 212, 255, 0.2);
        }
        .stock-card .delete-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: transparent;
            color: #666;
            padding: 5px;
            font-size: 20px;
            z-index: 10;
        }
        .stock-card .delete-btn:hover { color: #ff4757; }
        .stock-name {
            font-size: 18px;
            font-weight: bold;
            color: #00d4ff;
            margin-bottom: 5px;
        }
        .stock-code {
            font-size: 14px;
            color: #666;
            margin-bottom: 15px;
        }
        .stock-price {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .price-up { color: #ff4757; }
        .price-down { color: #00ff88; }
        .stock-change {
            font-size: 16px;
            margin-bottom: 5px;
        }
        .stock-info {
            display: flex;
            gap: 15px;
            align-items: center;
            margin-bottom: 10px;
        }
        .yesterday-close {
            font-size: 14px;
            color: #888;
        }
        .alert-section {
            background: #1a1a2e;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .alert-section h4 { margin: 0 0 10px 0; color: #00d4ff; }
        .alert-section input[type="number"] {
            background: #16213e;
            border: 1px solid #333;
            color: #fff;
            padding: 5px 10px;
            border-radius: 4px;
            width: 60px;
        }
        .stock-time {
            font-size: 12px;
            color: #666;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }
        .empty-state h2 { margin-bottom: 10px; }
        .last-update {
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-size: 14px;
        }
        
        /* Tab 导航 */
        .tab-nav {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
            padding-bottom: 0;
        }
        .tab-btn {
            background: none;
            border: none;
            color: #888;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.3s;
        }
        .tab-btn:hover {
            color: #fff;
        }
        .tab-btn.active {
            color: #00d4ff;
            border-bottom-color: #00d4ff;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        
        /* 告警列表 */
        .alert-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .alert-item {
            background: #1a1a2e;
            border-radius: 8px;
            padding: 12px 15px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 4px solid #00d4ff;
        }
        .alert-item.high {
            border-left-color: #ff6b6b;
            background: linear-gradient(90deg, rgba(255,107,107,0.1) 0%, transparent 100%);
        }
        .alert-item.medium {
            border-left-color: #ffa500;
            background: linear-gradient(90deg, rgba(255,165,0,0.1) 0%, transparent 100%);
        }
        .alert-item.low {
            border-left-color: #4caf50;
        }
        .alert-icon {
            font-size: 20px;
        }
        .alert-info {
            flex: 1;
        }
        .alert-msg {
            color: #fff;
            font-size: 14px;
            margin-bottom: 4px;
        }
        .alert-time {
            color: #666;
            font-size: 12px;
        }
        .alert-clear {
            background: #333;
            border: none;
            color: #888;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .alert-clear:hover {
            background: #ff6b6b;
            color: #fff;
        }
        
        /* 弹窗图表 */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: #16213e;
            border-radius: 16px;
            padding: 20px;
            width: 90%;
            max-width: 900px;
            max-height: 90vh;
            overflow: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-title {
            font-size: 20px;
            font-weight: bold;
            color: #00d4ff;
        }
        .modal-close {
            background: none;
            border: none;
            color: #666;
            font-size: 28px;
            cursor: pointer;
            padding: 0;
        }
        .modal-close:hover { color: #fff; }
        .chart-container {
            height: 400px;
            position: relative;
        }
        .chart-loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 A股分时监控</h1>
        
        <div class="status-bar">
            <div class="status-item">
                <div class="status-dot {% if is_trading %}active{% else %}inactive{% endif %}" id="statusDot"></div>
                <span>{% if is_trading %}● 交易中{% else %}○ 休市{% endif %}</span>
            </div>
            <div class="status-item">
                <span>自选股: <strong id="stockCount">0</strong> 只</span>
            </div>
            <div class="status-item">
                <span>刷新: <strong id="interval">-</strong>秒</span>
            </div>
        </div>
        
        <!-- Tab 导航 -->
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('stocks')">📊 自选股</button>
            <button class="tab-btn" onclick="switchTab('alerts')">🚨 告警历史</button>
        </div>
        
        <!-- Tab 内容：自选股 -->
        <div class="tab-content active" id="tab-stocks">
        
        <div class="add-form">
            <input type="text" id="stockInput" placeholder="输入股票代码 (如 600519, 000001, 300750)" maxlength="6">
            <button class="btn-add" onclick="addStock()">+ 添加股票</button>
            <button class="btn-add" style="background:#ff6b6b" onclick="openAlertConfig()">⚙️ 告警配置</button>
        </div>
        
        <div class="stock-grid" id="stockGrid">
            <div class="empty-state">
                <h2>暂无自选股</h2>
                <p>添加股票代码开始监控</p>
            </div>
        </div>
        
        <div class="last-update">
            最后更新: <span id="lastUpdate">-</span>
        </div>
        
        </div>
        <!-- Tab 内容：告警历史 -->
        <div class="tab-content" id="tab-alerts">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
                <h3>🚨 告警历史</h3>
                <button class="alert-clear" onclick="clearAlertHistory()">清空</button>
            </div>
            <div class="alert-list" id="alertList">
                <div class="empty-state">
                    <h2>暂无告警记录</h2>
                    <p>触发告警后会显示在这里</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 图表弹窗 -->
    <div class="modal-overlay" id="chartModal">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title" id="chartTitle">分时图</div>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="chart-container">
                <canvas id="minuteChart"></canvas>
                <div class="chart-loading" id="chartLoading">加载中...</div>
            </div>
        </div>
    </div>
    
    <!-- 告警配置弹窗 -->
    <div class="modal-overlay" id="alertModal">
        <div class="modal" style="max-width:600px">
            <div class="modal-header">
                <div class="modal-title">告警配置</div>
                <button class="modal-close" onclick="closeAlertModal()">×</button>
            </div>
            <div style="padding:20px;max-height:70vh;overflow-y:auto">
                <div class="alert-section">
                    <h4>📈 涨跌幅告警</h4>
                    <label><input type="checkbox" id="alert-price-change-enabled"> 启用</label>
                    <input type="number" id="alert-price-change-threshold" placeholder="阈值%" style="width:80px"> % 以上触发
                </div>
                <div class="alert-section">
                    <h4>⚡ 快速波动告警</h4>
                    <label><input type="checkbox" id="alert-rapid-enabled"> 启用</label>
                    <input type="number" id="alert-rapid-minutes" placeholder="30" style="width:60px"> 分钟内涨跌
                    <input type="number" id="alert-rapid-threshold" placeholder="3" style="width:60px"> % 触发
                </div>
                <div class="alert-section">
                    <h4>📊 放量告警</h4>
                    <label><input type="checkbox" id="alert-volume-enabled"> 启用</label>
                    成交量增加 <input type="number" id="alert-volume-threshold" placeholder="50" style="width:60px"> % 触发
                </div>
                <div class="alert-section">
                    <h4>📉 趋势拟合告警</h4>
                    <label><input type="checkbox" id="alert-trend-enabled"> 启用</label>
                    <br>回看时间: <input type="number" id="alert-trend-lookback" placeholder="60" style="width:60px"> 分钟
                    <br><small>用多少分钟的数据做拟合（60=1小时，120=2小时）</small>
                    <br><small>注: 数据点少于12个时不触发</small>
                </div>
                <div class="alert-section">
                    <h4>📈📉 连续涨/跌监控</h4>
                    <label><input type="checkbox" id="alert-continuous-enabled"> 启用</label>
                    <br>监控时间窗口: 
                    <input type="number" id="alert-continuous-30" placeholder="30" style="width:50px"> 分
                    <input type="number" id="alert-continuous-60" placeholder="60" style="width:50px"> 分
                    <input type="number" id="alert-continuous-120" placeholder="120" style="width:50px"> 分
                    <input type="number" id="alert-continuous-180" placeholder="180" style="width:50px"> 分
                    <br>最小涨跌幅: <input type="number" id="alert-continuous-min" placeholder="0.5" style="width:50px"> %
                    <br><small>同时满足多个时间窗口持续涨/跌时触发</small>
                </div>
                <div class="alert-section">
                    <h4">🔄 刷新间隔</h4>
                    <input type="number" id="alert-refresh-interval" placeholder="60" style="width:80px"> 秒
                </div>
                <div class="alert-section">
                    <h4">🔔 开盘/收盘推送</h4>
                    <label><input type="checkbox" id="alert-open-enabled"> 开盘推送</label>
                    <label><input type="checkbox" id="alert-close-enabled"> 收盘推送</label>
                </div>
                <button class="btn-add" onclick="saveAlertConfig()" style="margin-top:20px;width:100%">保存配置</button>
            </div>
        </div>
    </div>
    
    <script>
        let stocks = [];
        let autoRefresh = null;
        let minuteChart = null;
        
        // 加载股票列表
        async function loadStocks() {
            const res = await fetch('/api/stocks');
            stocks = await res.json();
            document.getElementById('stockCount').textContent = stocks.length;
            
            // 获取刷新间隔配置
            const alertsRes = await fetch('/api/alerts');
            const alerts = await alertsRes.json();
            const refreshInterval = (alerts.refresh_interval || 60) * 1000;
            
            document.getElementById('interval').textContent = alerts.refresh_interval || 60;
            
            renderStocks();
            startAutoRefresh(refreshInterval);
        }
        
        // 渲染股票卡片
        function renderStocks() {
            const grid = document.getElementById('stockGrid');
            
            if (stocks.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state">
                        <h2>暂无自选股</h2>
                        <p>添加股票代码开始监控</p>
                    </div>
                `;
                return;
            }
            
            grid.innerHTML = stocks.map(s => `
                <div class="stock-card" onclick="showChart('${s.code}')" id="card-${s.code}">
                    <button class="delete-btn" onclick="event.stopPropagation(); deleteStock('${s.code}')">×</button>
                    <div class="stock-name">${s.name || '-'}</div>
                    <div class="stock-code">${s.code}</div>
                    <div class="stock-price ${s.change_pct >= 0 ? 'price-up' : 'price-down'}">
                        ${s.price || '-'}
                    </div>
                    <div class="stock-info">
                        <span class="yesterday-close">昨收: ${s.yesterday_close || '-'}</span>
                        <span class="stock-change ${s.change_pct >= 0 ? 'price-up' : 'price-down'}">
                            ${s.change >= 0 ? '+' : ''}${s.change || 0} (${s.change_pct >= 0 ? '+' : ''}${s.change_pct || 0}%)
                        </span>
                    </div>
                    <div class="stock-time">${s.time || '-'}</div>
                </div>
            `).join('');
        }
        
        // 添加股票
        async function addStock() {
            const input = document.getElementById('stockInput');
            const code = input.value.trim().toUpperCase();
            
            if (!code) return;
            if (!/^\\d{6}$/.test(code)) {
                alert('请输入6位股票代码');
                return;
            }
            
            const res = await fetch('/api/stocks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            });
            
            const result = await res.json();
            if (result.success) {
                input.value = '';
                loadStocks();
            } else {
                alert(result.message || '添加失败');
            }
        }
        
        // 删除股票
        async function deleteStock(code) {
            if (!confirm(`确定删除 ${code}?`)) return;
            
            const res = await fetch(`/api/stocks/${code}`, {method: 'DELETE'});
            const result = await res.json();
            if (result.success) {
                loadStocks();
            }
        }
        
        // 刷新数据
        async function refreshData() {
            const res = await fetch('/api/realtime');
            const data = await res.json();
            
            stocks = data;
            renderStocks();
            
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
        
        // 自动刷新
        function startAutoRefresh(intervalMs = 60000) {
            if (autoRefresh) clearInterval(autoRefresh);
            autoRefresh = setInterval(refreshData, intervalMs);
            refreshData();
        }
        
        // 回车添加
        document.getElementById('stockInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') addStock();
        });
        
        // 显示图表
        async function showChart(code) {
            const modal = document.getElementById('chartModal');
            const loading = document.getElementById('chartLoading');
            const title = document.getElementById('chartTitle');
            
            modal.classList.add('show');
            loading.style.display = 'block';
            
            // 获取股票名称和昨日收盘价
            const stock = stocks.find(s => s.code === code);
            const yesterdayClose = stock?.yesterday_close;
            title.textContent = `${stock?.name || code} - 分时图 (昨收: ${yesterdayClose || '-'})`;
            
            // 获取分时数据
            const res = await fetch(`/api/minute/${code}`);
            const data = await res.json();
            
            loading.style.display = 'none';
            
            if (!data || data.length === 0) {
                alert('暂无分时数据');
                return;
            }
            
            // 准备图表数据
            const times = data.map(d => d.time);
            const prices = data.map(d => d.close);
            const volumes = data.map(d => d.volume);
            
            // 渲染图表
            const ctx = document.getElementById('minuteChart').getContext('2d');
            
            if (minuteChart) {
                minuteChart.destroy();
            }
            
            const isUp = prices[prices.length - 1] >= (yesterdayClose || prices[0]);
            const color = isUp ? '#ff4757' : '#00ff88';
            
            minuteChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: times,
                    datasets: [
                        {
                            label: '价格',
                            data: prices,
                            borderColor: color,
                            backgroundColor: color + '20',
                            fill: true,
                            yAxisID: 'y',
                            tension: 0.1
                        },
                        {
                            label: '成交量',
                            data: volumes,
                            type: 'bar',
                            backgroundColor: '#333',
                            yAxisID: 'y1'
                        },
                        ...(yesterdayClose ? [{
                            label: '昨日收盘',
                            data: Array(times.length).fill(yesterdayClose),
                            borderColor: '#888',
                            borderDash: [5, 5],
                            borderWidth: 1,
                            pointRadius: 0,
                            yAxisID: 'y'
                        }] : [])
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        legend: { labels: { color: '#999' } }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#666', maxTicksLimit: 20 },
                            grid: { color: '#333' }
                        },
                        y: {
                            type: 'linear',
                            position: 'left',
                            ticks: { color: color },
                            grid: { color: '#333' }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            ticks: { color: '#666' },
                            grid: { display: false }
                        }
                    }
                }
            });
        }
        
        // 关闭弹窗
        function closeModal() {
            document.getElementById('chartModal').classList.remove('show');
        }
        
        // 打开告警配置
        async function openAlertConfig() {
            const res = await fetch('/api/alerts');
            const config = await res.json();
            
            // 刷新间隔
            document.getElementById('alert-refresh-interval').value = config.refresh_interval || 60;
            
            // 涨跌幅告警
            const pc = config.price_change || {};
            document.getElementById('alert-price-change-enabled').checked = pc.enabled !== false;
            document.getElementById('alert-price-change-threshold').value = pc.threshold || 5;
            
            // 快速波动
            const rc = config.rapid_change || {};
            document.getElementById('alert-rapid-enabled').checked = rc.enabled !== false;
            document.getElementById('alert-rapid-minutes').value = rc.minutes || 30;
            document.getElementById('alert-rapid-threshold').value = rc.threshold || 3;
            
            // 放量
            const vs = config.volume_surge || {};
            document.getElementById('alert-volume-enabled').checked = vs.enabled !== false;
            document.getElementById('alert-volume-threshold').value = vs.threshold || 50;
            
            // 趋势拟合
            const tf = config.trend_fit || {};
            document.getElementById('alert-trend-enabled').checked = tf.enabled !== false;
            document.getElementById('alert-trend-lookback').value = tf.lookback || 60;
            
            // 连续涨/跌监控
            const ct = config.continuous_trend || {};
            document.getElementById('alert-continuous-enabled').checked = ct.enabled !== false;
            document.getElementById('alert-continuous-30').value = (ct.intervals && ct.intervals[0]) || 30;
            document.getElementById('alert-continuous-60').value = (ct.intervals && ct.intervals[1]) || 60;
            document.getElementById('alert-continuous-120').value = (ct.intervals && ct.intervals[2]) || 120;
            document.getElementById('alert-continuous-180').value = (ct.intervals && ct.intervals[3]) || 180;
            document.getElementById('alert-continuous-min').value = ct.min_change || 0.5;
            
            // 开盘/收盘
            const oc = config.open_close_push || {};
            document.getElementById('alert-open-enabled').checked = oc.push_open !== false;
            document.getElementById('alert-close-enabled').checked = oc.push_close !== false;
            
            document.getElementById('alertModal').classList.add('show');
        }
        
        function closeAlertModal() {
            document.getElementById('alertModal').classList.remove('show');
        }
        
        async function saveAlertConfig() {
            const config = {
                refresh_interval: parseInt(document.getElementById('alert-refresh-interval').value) || 60,
                price_change: {
                    enabled: document.getElementById('alert-price-change-enabled').checked,
                    threshold: parseFloat(document.getElementById('alert-price-change-threshold').value) || 5
                },
                rapid_change: {
                    enabled: document.getElementById('alert-rapid-enabled').checked,
                    minutes: parseInt(document.getElementById('alert-rapid-minutes').value) || 30,
                    threshold: parseFloat(document.getElementById('alert-rapid-threshold').value) || 3
                },
                volume_surge: {
                    enabled: document.getElementById('alert-volume-enabled').checked,
                    threshold: parseFloat(document.getElementById('alert-volume-threshold').value) || 50
                },
                trend_fit: {
                    enabled: document.getElementById('alert-trend-enabled').checked,
                    lookback: parseInt(document.getElementById('alert-trend-lookback').value) || 60
                },
                continuous_trend: {
                    enabled: document.getElementById('alert-continuous-enabled').checked,
                    intervals: [
                        parseInt(document.getElementById('alert-continuous-30').value) || 30,
                        parseInt(document.getElementById('alert-continuous-60').value) || 60,
                        parseInt(document.getElementById('alert-continuous-120').value) || 120,
                        parseInt(document.getElementById('alert-continuous-180').value) || 180
                    ],
                    min_change: parseFloat(document.getElementById('alert-continuous-min').value) || 0.5
                },
                open_close_push: {
                    enabled: true,
                    push_open: document.getElementById('alert-open-enabled').checked,
                    push_close: document.getElementById('alert-close-enabled').checked
                }
            };
            
            await fetch('/api/alerts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            
            alert('配置已保存！');
            closeAlertModal();
        }
        
        // 点击遮罩关闭
        document.getElementById('chartModal').addEventListener('click', e => {
            if (e.target.id === 'chartModal') closeModal();
        });
        
        document.getElementById('alertModal').addEventListener('click', e => {
            if (e.target.id === 'alertModal') closeAlertModal();
        });
        
        // Tab 切换
        function switchTab(tabName) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            if (tabName === 'stocks') {
                document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
                document.getElementById('tab-stocks').classList.add('active');
            } else {
                document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
                document.getElementById('tab-alerts').classList.add('active');
                loadAlertHistory();  // 切换到告警Tab时加载历史
            }
        }
        
        // 加载告警历史
        async function loadAlertHistory() {
            try {
                const res = await fetch('/api/alerts/history');
                const alerts = await res.json();
                const list = document.getElementById('alertList');
                
                if (!alerts || alerts.length === 0) {
                    list.innerHTML = '<div class="empty-state"><h2>暂无告警记录</h2><p>触发告警后会显示在这里</p></div>';
                    return;
                }
                
                // 按时间倒序排列
                alerts.reverse();
                
                list.innerHTML = alerts.map(alert => {
                    const severity = alert.severity || 'low';
                    const icon = alert.type === 'price_change' ? '📈' : 
                                 alert.type === 'rapid_change' ? '⚡' :
                                 alert.type === 'volume_surge' ? '📊' :
                                 alert.type === 'continuous_up' ? '📈📈' :
                                 alert.type === 'continuous_down' ? '📉📉' : '🚨';
                    return '<div class="alert-item ' + severity + '">' +
                        '<span class="alert-icon">' + icon + '</span>' +
                        '<div class="alert-info">' +
                        '<div class="alert-msg">' + alert.msg + '</div>' +
                        '<div class="alert-time">' + alert.time + '</div>' +
                        '</div></div>';
                }).join('');
            } catch (e) {
                console.error('加载告警历史失败:', e);
            }
        }
        
        // 清空告警历史
        async function clearAlertHistory() {
            if (!confirm('确定要清空所有告警记录吗？')) return;
            await fetch('/api/alerts/history?action=clear', {method: 'GET'});
            loadAlertHistory();
        }
        
        // 初始化
        loadStocks();
    </script>
</body>
</html>
'''

# ==================== API路由 ====================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, is_trading=is_trading_time())

@app.route('/api/stocks', methods=['GET'])
def api_get_stocks():
    """获取自选股列表"""
    stocks = get_stocks()
    return jsonify(stocks)

@app.route('/api/stocks', methods=['POST'])
def api_add_stock():
    """添加股票"""
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    
    if not code:
        return jsonify({'success': False, 'message': '股票代码不能为空'})
    
    if not code.isdigit() or len(code) != 6:
        return jsonify({'success': False, 'message': '请输入6位数字代码'})
    
    success = add_stock(code)
    return jsonify({'success': True, 'message': '添加成功' if success else '股票已存在'})

@app.route('/api/stocks/<code>', methods=['DELETE'])
def api_delete_stock(code):
    """删除股票"""
    success = remove_stock(code)
    return jsonify({'success': True})

@app.route('/api/realtime', methods=['GET'])
def api_realtime():
    """获取实时行情"""
    stocks = get_stocks()
    if not stocks:
        return jsonify([])
    
    client = EastMoneyClient()
    results = []
    
    for code in stocks:
        data = client.get_realtime(code)
        if data:
            results.append(data)
            # 同时获取并保存分时数据
            client.fetch_and_save(code)
        time.sleep(0.1)
    
    return jsonify(results)

@app.route('/api/minute/<code>', methods=['GET'])
def api_minute(code):
    """获取分时数据"""
    data = get_minute_data(code)
    return jsonify(data)

@app.route('/api/alerts', methods=['GET'])
def api_get_alerts():
    """获取告警配置"""
    from config import get_alerts_config
    return jsonify(get_alerts_config())

@app.route('/api/alerts', methods=['POST'])
def api_save_alerts():
    """保存告警配置"""
    from config import save_alerts_config
    data = request.get_json()
    save_alerts_config(data)
    return jsonify({'success': True})

@app.route('/api/alerts/history', methods=['GET'])
def api_get_alert_history():
    """获取告警历史"""
    from alerts import get_alert_history, clear_alert_history
    action = request.args.get('action')
    if action == 'clear':
        clear_alert_history()
        return jsonify({'success': True, 'message': '已清空'})
    return jsonify(get_alert_history())

# ==================== 主程序 ====================

def main():
    # 启动后台定时任务
    from scheduler import background_task
    from config import load_config
    config = load_config()
    interval = config.get("refresh_interval", 60)
    background_task.start(interval=interval)
    
    print("=" * 50)
    print("A股分时监控服务启动")
    print("=" * 50)
    print("访问 http://localhost:8000 管理自选股")
    print("点击卡片查看分时图")
    print("后台告警任务: 已启动")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=8000, debug=False)

if __name__ == '__main__':
    main()
