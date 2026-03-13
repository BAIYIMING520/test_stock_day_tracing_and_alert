#!/usr/bin/env python3
"""
后台定时任务 - 定时检查告警并推送
"""

import sys
import time
import threading
import schedule
sys.path.append(__file__.rsplit('/', 1)[0])

from config import get_stocks, get_alerts_config, is_trading_time, is_market_open_time, is_market_close_time
from client import EastMoneyClient
from alerts import AlertChecker
from database import save_minute_data

class BackgroundTask:
    def __init__(self):
        self.client = EastMoneyClient()
        self.running = False
        self.interval = 60  # 默认60秒
    
    def start(self, interval=60):
        """启动后台任务"""
        self.interval = interval
        self.running = True
        
        # 启动定时任务
        schedule.every(self.interval).seconds.do(self.run_once)
        
        # 启动调度线程
        t = threading.Thread(target=self._run_schedule, daemon=True)
        t.start()
        
        print(f"后台任务已启动，每{self.interval}秒执行一次")
    
    def _run_schedule(self):
        """运行调度器"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def run_once(self):
        """执行一次检查"""
        # 非交易时间不执行告警检查（只记录）
        if not is_trading_time():
            print(f"[后台任务] 非交易时间，跳过")
            return
        
        stocks = get_stocks()
        alerts_config = get_alerts_config()
        
        print(f"[后台任务] 检查 {len(stocks)} 只股票...")
        
        for code in stocks:
            try:
                # 1. 获取实时数据
                realtime = self.client.get_realtime(code)
                if not realtime:
                    print(f"  {code}: 获取数据失败")
                    continue
                
                # 2. 保存分时数据
                self.client.fetch_and_save(code)
                
                # 3. 检查告警
                checker = AlertChecker()
                alerts = checker.check_all(code, realtime)
                
                # 4. 推送告警
                for alert in alerts:
                    print(f"  🚨 {alert['msg']}")
                    checker.push_to_quote0(alert['msg'])
                
                # 5. 开盘/收盘推送
                if alerts_config.get("open_close_push", {}).get("enabled"):
                    if is_market_open_time() and alerts_config["open_close_push"].get("push_open"):
                        # 开盘推送
                        msg = f"{code} 开盘 {realtime.get('price')}元"
                        checker.push_to_quote0(msg)
                        print(f"  📢 开盘推送: {msg}")
                    
                    if is_market_close_time() and alerts_config["open_close_push"].get("push_close"):
                        # 收盘推送
                        msg = f"{code} 收盘 {realtime.get('price')}元"
                        checker.push_to_quote0(msg)
                        print(f"  📢 收盘推送: {msg}")
                
            except Exception as e:
                print(f"  {code}: 错误 - {e}")
        
        print(f"[后台任务] 完成")
    
    def stop(self):
        """停止"""
        self.running = False


# 后台任务实例
background_task = BackgroundTask()


if __name__ == "__main__":
    # 测试
    background_task.start(interval=60)
    
    # 保持运行
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("停止后台任务")
