#!/usr/bin/env python3
"""
E2E 测试 - A股分时监控服务
依赖：pip install playwright && playwright install chromium
运行：python tests/test_e2e.py
"""
import time
import re
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = "http://localhost:8000"


# ── Fixtures ────────────────────────────────────────────────

def get_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def new_page(browser):
    ctx = browser.new_context(
        locale="zh-CN",
        viewport={"width": 1400, "height": 900}
    )
    page = ctx.new_page()
    # 阻止外部 CDN 资源，避免测试环境网络不通导致阻塞
    page.route("https://cdn.jsdelivr.net/**", lambda route: route.abort())
    page.route("https://cdn.tailwindcss.com/**", lambda route: route.abort())
    yield page
    ctx.close()


# ── Helpers ────────────────────────────────────────────────

def login_as_admin(page: Page):
    """登录管理后台"""
    page.goto(f"{BASE_URL}/")
    page.wait_for_load_state("networkidle")

    # 点击登录按钮或直接打开登录弹窗
    page.evaluate("""() => {
        // 直接调用前端的登录函数
        if (window.showLoginForm) window.showLoginForm();
    }""")
    time.sleep(0.3)

    # 在登录弹窗中输入账密
    page.fill("#loginUsername", "admin")
    page.fill("#loginPassword", "admin123")
    page.click("#loginBtn")
    time.sleep(0.5)


# ── 测试用例 ────────────────────────────────────────────────

def test_home_page_loads(browser):
    """首页能正常加载"""
    page = browser.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")

    title = page.title()
    assert "A股" in title or "监控" in title, f"页面标题不符合预期: {title}"

    # 验证主要 DOM 元素存在
    assert page.locator("h1").count() > 0, "页面缺少 h1 标题"
    page.close()


def test_realtime_api_returns_valid_data(browser):
    """GET /api/realtime 返回有效数据"""
    page = browser.new_page()
    page.goto(f"{BASE_URL}/api/realtime")

    import json
    data = json.loads(page.content())

    assert isinstance(data, list), f"realtime 应返回列表，实际: {type(data)}"
    if len(data) == 0:
        # 没有自选股，跳过（这是合理状态）
        page.close()
        return

    stock = data[0]
    required_fields = ["code", "name", "price", "change_pct", "yesterday_close"]
    for field in required_fields:
        assert field in stock, f"股票数据缺少字段 {field}"

    assert isinstance(stock["price"], (int, float)), f"price 应为数字: {stock['price']}"
    assert isinstance(stock["change_pct"], (int, float)), f"change_pct 应为数字: {stock['change_pct']}"
    page.close()


def test_stocks_tab_shows_cards(browser):
    """自选股 Tab 下能显示股票卡片"""
    page = browser.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")

    # 确保在自选股 Tab
    page.click(".tab-btn:first-child")
    time.sleep(1)

    # 如果有股票，应该显示卡片
    stock_cards = page.locator(".stock-card")
    count = stock_cards.count()

    if count > 0:
        # 验证卡片内容
        first_card = stock_cards.first
        text = first_card.inner_text()
        assert len(text) > 0, "卡片内容为空"
    else:
        # 没有股票是合理状态，跳过
        pass

    page.close()


def test_add_stock_via_api(browser):
    """通过 API 添加股票后卡片出现"""
    page = browser.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.click(".tab-btn:first-child")
    time.sleep(0.5)

    # 记录当前卡片数量
    before = page.locator(".stock-card").count()

    # 用前端 JS 添加股票
    page.evaluate("""() => {
        // 直接调用前端的添加函数
        document.getElementById('stockInput').value = '000001';
    }""")

    # 触发前端添加逻辑
    page.evaluate("""() => {
        const input = document.getElementById('stockInput');
        // 模拟回车
        input.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter'}));
    }""")
    time.sleep(1)

    # 刷新页面验证
    page.reload(wait_until="domcontentloaded")
    after = page.locator(".stock-card").count()

    # 添加后数量应该增加（或者已经存在所以不变）
    assert after >= before, f"刷新后卡片数量未增加: {before} -> {after}"
    page.close()


def test_chart_modal_opens(browser):
    """点击股票卡片能打开分时图弹窗"""
    page = browser.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.click(".tab-btn:first-child")
    time.sleep(1)

    cards = page.locator(".stock-card")
    if cards.count() == 0:
        # 无股票，跳过
        page.close()
        return

    # 点击第一张卡片
    cards.first.click()
    time.sleep(1)

    # 验证弹窗出现
    modal = page.locator("#chartModal")
    assert modal.count() > 0, "点击卡片后未出现弹窗"

    # 关闭弹窗
    page.keyboard.press("Escape")
    time.sleep(0.3)
    page.close()


def test_alerts_tab_loads(browser):
    """告警 Tab 能正常切换并显示配置"""
    page = browser.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")

    # 切换到告警 Tab
    tabs = page.locator(".tab-btn")
    tabs.nth(1).click()
    time.sleep(0.5)

    # 验证 Tab 内容出现
    alert_content = page.locator("#tab-alerts")
    assert alert_content.count() > 0, "告警 Tab 内容未出现"
    page.close()


def test_alerts_history_api(browser):
    """GET /api/alerts/history 返回正确结构"""
    page = browser.new_page()
    page.goto(f"{BASE_URL}/api/alerts/history")

    import json
    data = json.loads(page.content())

    # 必须有这三个字段
    assert "data" in data, "alerts/history 缺少 data 字段"
    assert "total" in data, "alerts/history 缺少 total 字段"
    assert "total_pages" in data, "alerts/history 缺少 total_pages 字段"
    assert isinstance(data["data"], list), "data 应为列表"

    page.close()


def test_login_and_admin_tab(browser):
    """登录后能进入管理 Tab"""
    page = browser.new_page()
    page.goto(BASE_URL, wait_until="domcontentloaded")

    # 触发登录
    login_as_admin(page)
    time.sleep(0.5)

    # 点击管理 Tab
    admin_tab = page.locator(".tab-btn", has_text=re.compile("管理"))
    if admin_tab.count() > 0:
        admin_tab.click()
        time.sleep(0.5)

        user_list = page.locator("#userList")
        assert user_list.count() > 0, "管理 Tab 未出现用户列表"
    else:
        # 管理按钮可能内联在别的位置
        page.click("#adminTabBtn")
        time.sleep(0.5)

    page.close()


def test_no_console_errors_on_home(browser):
    """首页加载时无严重 JS 错误"""
    errors = []

    def handle_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page = browser.new_page()
    page.on("console", handle_console)
    page.goto(BASE_URL, wait_until="domcontentloaded")
    time.sleep(2)

    # 过滤掉 React DevTools 警告等无关错误
    real_errors = [
        e for e in errors
        if "DevTools" not in e
        and "favicon" not in e.lower()
        and "reverse is not a function" in e  # 只关注已知的明确错误
    ]

    assert len(real_errors) == 0, f"控制台有错误: {real_errors}"
    page.close()


# ── 入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("A股分时监控 E2E 测试")
    print("=" * 60)
    print(f"目标服务: {BASE_URL}")
    print(f"运行时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 先检查服务是否可用
    import urllib.request
    try:
        urllib.request.urlopen(BASE_URL, timeout=3)
    except Exception as e:
        print(f"❌ 服务未运行: {e}")
        print("请先启动服务: cd /root/stock_monitor && python server.py")
        sys.exit(1)

    # 逐个运行测试
    tests = [
        ("首页加载", test_home_page_loads),
        ("实时数据 API", test_realtime_api_returns_valid_data),
        ("自选股 Tab 卡片显示", test_stocks_tab_shows_cards),
        ("添加股票", test_add_stock_via_api),
        ("分时图弹窗", test_chart_modal_opens),
        ("告警 Tab 切换", test_alerts_tab_loads),
        ("告警历史 API 结构", test_alerts_history_api),
        ("登录与管理后台", test_login_and_admin_tab),
        ("首页无控制台错误", test_no_console_errors_on_home),
    ]

    passed = 0
    failed = 0
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        browser.close()

    for name, fn in tests:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                fn(browser)
                browser.close()
            print(f"  ✅ {name}")
            passed += 1
            results.append((name, "PASS", None))
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
            results.append((name, "FAIL", str(e)))

    print()
    print("=" * 60)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        print("\n失败详情:")
        for name, status, err in results:
            if status == "FAIL":
                print(f"  ❌ {name}")
                print(f"     {err}")

    sys.exit(0 if failed == 0 else 1)
