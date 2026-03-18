#!/usr/bin/env python3
"""
定时调度领域 - 交易时间内自动抓取行情并检查告警
"""
import sys
import time
import threading
import schedule
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.config import get_stocks, get_alerts_config, is_trading_time, is_market_open_time, is_market_close_time
from src.infrastructure.client import EastMoneyClient
from src.domain.alert import AlertChecker


class BackgroundTask:
    def __init__(self):
        self.client = EastMoneyClient()
        self.running = False
        self.interval = 60

    def start(self, interval=60):
        self.interval = interval
        self.running = True
        schedule.every(self.interval).seconds.do(self.run_once)
        t = threading.Thread(target=self._run_schedule, daemon=True)
        t.start()
        print(f"后台任务已启动，每{self.interval}秒执行一次")

    def _run_schedule(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def run_once(self):
        if not is_trading_time():
            print("[后台任务] 非交易时间，跳过")
            return

        stocks = get_stocks()
        alerts_config = get_alerts_config()

        print(f"[后台任务] 检查 {len(stocks)} 只股票...")

        for code in stocks:
            try:
                realtime = self.client.get_realtime(code)
                if not realtime:
                    print(f"  {code}: 获取数据失败")
                    continue

                # 保存分时数据
                self.client.fetch_and_save(code)

                # 检查告警
                checker = AlertChecker()
                alerts = checker.check_all(code, realtime)

                for alert in alerts:
                    print(f"  🚨 {alert['msg']}")
                    checker.push_all(alert)

                # 开盘/收盘推送
                oc_cfg = alerts_config.get("open_close_push", {})
                if oc_cfg.get("enabled"):
                    if is_market_open_time() and oc_cfg.get("push_open"):
                        msg = f"{code} 开盘 {realtime.get('price')}元"
                        checker.push_to_quote0(msg)
                        print(f"  📢 开盘推送: {msg}")

                    if is_market_close_time() and oc_cfg.get("push_close"):
                        msg = f"{code} 收盘 {realtime.get('price')}元"
                        checker.push_to_quote0(msg)
                        print(f"  📢 收盘推送: {msg}")

            except Exception as e:
                print(f"  {code}: 错误 - {e}")

        print("[后台任务] 完成")

    def stop(self):
        self.running = False
