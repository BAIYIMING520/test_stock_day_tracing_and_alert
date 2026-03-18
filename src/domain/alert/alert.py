#!/usr/bin/env python3
"""
告警领域 - 检查行情数据，触发各类告警规则，推送到各渠道
"""
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from src.infrastructure.database import (
    get_minute_data, save_alert_to_db,
    get_alert_history_from_db, clear_alert_history_from_db
)
from src.services.config import get_alerts_config, get_quote0_config, load_config
from src.infrastructure.client import EastMoneyClient


# 模块级状态：Quote 推送去重
_quote_push_history = defaultdict(list)
_QUOTE_COOLDOWN_SECONDS = 300  # 5分钟
_QUOTE_MAX_PUSHES = 3          # 最多3次


# ── 公开函数 ────────────────────────────────────────────────

def get_alert_history(days: int = 5, code: str = None, alert_type: str = None,
                      page: int = 1, page_size: int = 30):
    """从数据库读取告警历史"""
    return get_alert_history_from_db(
        days=days, code=code, alert_type=alert_type,
        page=page, page_size=page_size
    )


def clear_alert_history(days: int = 0):
    """清空告警历史（days=0 清全部）"""
    clear_alert_history_from_db(days)


# ── AlertChecker ─────────────────────────────────────────────

class AlertChecker:
    def __init__(self):
        self.client = EastMoneyClient()
        self.alerts = get_alerts_config()
        self.quote0 = get_quote0_config()
        self.email = load_config().get("email", {})

    def get_email_config(self):
        return self.email

    def check_all(self, code: str, realtime_data: dict):
        alerts_triggered = []
        name = realtime_data.get('name', '')[:4]

        # 1. 涨跌幅告警
        cfg = self.alerts.get("price_change", {})
        if cfg.get("enabled"):
            threshold = cfg.get("threshold", 5.0)
            pct = abs(realtime_data.get("change_pct", 0))
            if pct >= threshold:
                alerts_triggered.append({
                    "type": "price_change",
                    "code": code,
                    "name": name,
                    "msg": f"{code}{name} 涨跌{pct:.2f}%",
                    "severity": "high"
                })

        # 2. 快速波动告警
        cfg = self.alerts.get("rapid_change", {})
        if cfg.get("enabled"):
            minutes = cfg.get("minutes", 30)
            threshold = cfg.get("threshold", 3.0)
            change = self._check_rapid_change(code, minutes)
            if change and abs(change) >= threshold:
                direction = "涨" if change > 0 else "跌"
                alerts_triggered.append({
                    "type": "rapid_change",
                    "code": code,
                    "name": name,
                    "msg": f"{code}{name} {minutes}分{direction}{abs(change):.2f}%",
                    "severity": "high"
                })

        # 3. 放量告警
        cfg = self.alerts.get("volume_surge", {})
        if cfg.get("enabled"):
            threshold = cfg.get("threshold", 50.0)
            surge = self._check_volume_surge(code)
            if surge and surge >= threshold:
                alerts_triggered.append({
                    "type": "volume_surge",
                    "code": code,
                    "name": name,
                    "msg": f"{code}{name} 放量{surge:.1f}%",
                    "severity": "medium"
                })

        # 4. 趋势拟合告警
        cfg = self.alerts.get("trend_fit", {})
        if cfg.get("enabled"):
            lookback = cfg.get("lookback", 60)
            trend_result = self._check_trend_fit(code, lookback)
            if trend_result:
                alerts_triggered.append({
                    "type": "trend_fit",
                    "code": code,
                    "name": name,
                    "msg": f"{code}{name} {trend_result}",
                    "severity": "high"
                })

        # 5. 连续涨/跌监控
        cfg = self.alerts.get("continuous_trend", {})
        if cfg.get("enabled"):
            intervals = cfg.get("intervals", [30, 60, 120, 180])
            min_change = cfg.get("min_change", 0.5)
            continuous_alerts = self._check_continuous_trend(code, name, intervals, min_change)
            alerts_triggered.extend(continuous_alerts)

        return alerts_triggered

    def _check_trend_fit(self, code: str, lookback: int = 60) -> str:
        """多函数拟合趋势判断"""
        data = get_minute_data(code)
        if not data or len(data) < 12:
            return None

        prices = np.array([d['close'] for d in data[-lookback:]])
        x = np.arange(len(prices))

        coef1 = np.polyfit(x, prices, 1)
        linear_down = coef1[0] < 0

        coef2 = np.polyfit(x, prices, 2)
        quadratic_down = coef2[0] < 0

        cubic_down = prices[-1] < prices[0]

        if linear_down and quadratic_down and cubic_down:
            return "下跌趋势确认 ⬇️ 可做反T(卖出)"
        if not linear_down and not quadratic_down and not cubic_down:
            return "上涨趋势确认 ⬆️ 可做正T(买入)"
        return None

    def _check_rapid_change(self, code: str, minutes: int) -> float:
        data = get_minute_data(code)
        if not data or len(data) < 2:
            return None

        idx = max(0, len(data) - minutes)
        old_price = data[idx].get("close")
        new_price = data[-1].get("close")

        if old_price and new_price and old_price > 0:
            return (new_price - old_price) / old_price * 100
        return None

    def _check_volume_surge(self, code: str) -> float:
        data = get_minute_data(code)
        if not data or len(data) < 30:
            return None

        recent_volume = sum(d.get("volume", 0) for d in data[-30:])
        earlier_volume = sum(d.get("volume", 0) for d in data[-60:-30]) \
            if len(data) >= 60 else recent_volume

        if earlier_volume > 0:
            return (recent_volume - earlier_volume) / earlier_volume * 100
        return None

    def _check_continuous_trend(self, code: str, name: str, intervals: list, min_change: float) -> list:
        data = get_minute_data(code)
        if not data or len(data) < 5:
            return []

        trends = []
        for minutes in intervals:
            if len(data) < minutes:
                continue

            start_price = data[-minutes].get("close")
            end_price = data[-1].get("close")

            if start_price and end_price and start_price > 0:
                change_pct = (end_price - start_price) / start_price * 100

                if change_pct >= min_change:
                    trends.append({
                        "type": "continuous_up",
                        "code": code,
                        "name": name,
                        "msg": f"{code}{name} 连涨{minutes//60}h {change_pct:.2f}%",
                        "severity": "high"
                    })
                elif change_pct <= -min_change:
                    trends.append({
                        "type": "continuous_down",
                        "code": code,
                        "name": name,
                        "msg": f"{code}{name} 连跌{minutes//60}h {abs(change_pct):.2f}%",
                        "severity": "high"
                    })

        return trends

    # ── 推送 ─────────────────────────────────────────────────

    def push_to_quote0(self, message: str, delay: float = 2.0,
                       code: str = None, alert_type: str = None):
        """推送到 Quote/0（去重：5分钟内同股票同类型最多3次）"""
        if code and alert_type:
            key = (code, alert_type)
            now = datetime.now()
            _quote_push_history[key] = [
                t for t in _quote_push_history[key]
                if now - t < timedelta(seconds=_QUOTE_COOLDOWN_SECONDS)
            ]
            if len(_quote_push_history[key]) >= _QUOTE_MAX_PUSHES:
                print(f"  ⏭️ Quote推送跳过（{code} {alert_type} 5分钟内已达3次）")
                return False
            _quote_push_history[key].append(now)

        import time as time_mod
        time_mod.sleep(delay)

        if not self.quote0.get("enabled"):
            return

        api_key = self.quote0.get("api_key")
        device_id = self.quote0.get("device_id")
        if not api_key or not device_id:
            return

        try:
            import subprocess
            cmd = [
                "node", "quote0.js", "text",
                "--apiKey", api_key,
                "--deviceId", device_id,
                "--title", "",
                "--message", message,
                "--signature", ""
            ]
            result = subprocess.run(
                cmd,
                cwd="/root/.openclaw/workspace/skills/quote0",
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Quote/0 push error: {e}")
            return False

    def push_to_email(self, alert: dict):
        """发送邮件通知"""
        import smtplib
        from email.mime.text import MIMEText
        from email.header import Header

        email_cfg = self.email
        if not email_cfg.get("enabled"):
            return False

        enabled_types = email_cfg.get("enabled_types", [])
        if enabled_types and alert.get("type") not in enabled_types:
            return False

        try:
            smtp_host = email_cfg.get("smtp_host", "smtp.qq.com")
            smtp_port = email_cfg.get("smtp_port", 587)
            username = email_cfg.get("username", "")
            password = email_cfg.get("password", "")
            to_addrs = email_cfg.get("to_addrs", [])

            if not username or not password or not to_addrs:
                print("Email config incomplete")
                return False

            subject = f"股票告警 - {alert.get('type', 'unknown')}"
            body = f"""【{alert.get('severity', 'info').upper()}】{alert.get('msg', '')}

类型: {alert.get('type', '')}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

来自 A股监控系统"""

            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = username
            msg['To'] = ','.join(to_addrs)

            server = smtplib.SMTP(smtp_host, smtp_port)
            if email_cfg.get("use_tls", True):
                server.starttls()
            server.login(username, password)
            server.sendmail(username, to_addrs, msg.as_string())
            server.quit()

            print(f"📧 Email sent: {alert.get('msg')}")
            return True
        except Exception as e:
            print(f"Email send error: {e}")
            return False

    def push_all(self, alert: dict):
        """推送告警到所有渠道"""
        alert_with_time = {
            **alert,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_alert_to_db(alert_with_time)
        self.push_to_quote0(
            alert.get("msg", ""),
            code=alert.get("code"),
            alert_type=alert.get("type")
        )
        self.push_to_email(alert)


def check_and_push(code: str, realtime_data: dict):
    """检查并推送告警（快捷函数）"""
    checker = AlertChecker()
    alerts = checker.check_all(code, realtime_data)
    if alerts:
        for alert in alerts:
            print(f"🚨 {alert['msg']}")
            checker.push_all(alert)
    return alerts
