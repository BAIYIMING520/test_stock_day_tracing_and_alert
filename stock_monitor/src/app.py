#!/usr/bin/env python3
"""A股分时监控服务 - DDD 架构"""
from flask import Flask, jsonify, request
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.config import get_stocks, add_stock, remove_stock, load_data_fetcher_config
from src.data_driven import get_stock_data_driven

app = Flask(__name__)

@app.route('/')
def index():
    return '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>A股分时监控</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#1a1a2e;color:#eee;margin:0;padding:20px}.stock-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px}.stock-card{background:#16213e;border-radius:12px;padding:20px}.price-up{color:#ff4757}.price-down{color:#00ff88}</style></head>
<body><h1>🦞 A股分时监控</h1><div class="stock-grid" id="grid"></div>
<script>async function load(){const res=await fetch('/api/realtime');const data=await res.json();document.getElementById('grid').innerHTML=data.map(s=>`<div class="stock-card"><b>${s.name}</b><br>代码:${s.code}<br>价格:${s.price}<br><span class="${s.change_pct>=0?'price-up':'price-down'}">${s.change>=0?'+':''}${s.change}(${s.change_pct>=0?'+':''}${s.change_pct}%)</span></div>`).join('')}load();setInterval(load,10000);</script></body></html>'''

@app.route('/api/stocks', methods=['GET'])
def api_get_stocks():
    return jsonify(get_stocks())

@app.route('/api/stocks', methods=['POST'])
def api_add_stock():
    code = request.get_json().get('code', '').strip().upper()
    return jsonify({'success': True}) if add_stock(code) else jsonify({'success': False})

@app.route('/api/stocks/<code>', methods=['DELETE'])
def api_delete_stock(code):
    remove_stock(code)
    return jsonify({'success': True})

@app.route('/api/realtime', methods=['GET'])
def api_realtime():
    stocks = get_stocks()
    if not stocks:
        return jsonify([])
    driven = get_stock_data_driven()
    return jsonify([r.to_dict() for r in driven.get_realtime_batch(stocks)])

@app.route('/api/minute/<code>', methods=['GET'])
def api_minute(code):
    driven = get_stock_data_driven()
    return jsonify([m.to_dict() for m in driven.get_minute_data(code)])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
