# A股分时监控与告警系统

A股实时行情监控、告警推送与分时图表展示。

## 功能特性

- 📊 **实时行情** - 自选股实时价格、涨跌幅监控
- 📈 **分时图表** - 点击股票卡片查看分时走势
- 🚨 **多种告警策略**
  - 涨跌幅告警（单日涨跌超过阈值）
  - 快速波动告警（N分钟内涨跌超过阈值）
  - 放量告警（成交量激增）
  - 趋势拟合告警（多项式拟合判断趋势）
  - 连续涨/跌监控（多时间窗口持续涨跌）
- 📢 **多渠道推送** - Quote/0 设备推送、邮件通知
- 🔄 **自动采集** - 交易时间自动抓取分时数据

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python app.py
```

访问 http://localhost:8000

### 配置

编辑 `config.json`：

```json
{
  "stocks": ["000001", "600519", "002050"],
  "alerts": {
    "price_change": {
      "enabled": true,
      "threshold": 5
    }
  },
  "quote0": {
    "enabled": true,
    "api_key": "your_api_key",
    "device_id": "your_device_id"
  }
}
```

## 接口说明

| 接口 | 说明 |
|------|------|
| `GET /api/realtime` | 获取自选股实时行情 |
| `GET /api/minute/<code>` | 获取分时数据（本地数据库） |
| `GET /api/stocks` | 获取自选股列表 |
| `POST /api/stocks` | 添加股票 |
| `DELETE /api/stocks/<code>` | 删除股票 |
| `GET /api/alerts` | 获取告警配置 |
| `POST /api/alerts` | 保存告警配置 |
| `GET /api/alerts/history` | 获取告警历史 |

## 数据来源

- 实时行情：东方财富 API（每30秒刷新）
- 分时数据：本地 SQLite 数据库（后台定时采集）
- 告警检查：每60秒执行一次

## 目录结构

```
.
├── app.py           # Flask Web 服务 + 前端页面
├── client.py       # 东方财富 API 客户端
├── config.py       # 配置管理
├── config.json     # 配置文件
├── database.py     # SQLite 数据库
├── alerts.py       # 告警检查逻辑
├── scheduler.py    # 后台定时任务
└── stock_data.db   # 分时数据存储
```

## License

MIT
