let stocks = [];
let autoRefresh = null;
let minuteChart = null;
let authToken = null;

// 获取 token
function getToken() {
    if (!authToken) {
        const saved = localStorage.getItem('token');
        if (saved) {
            authToken = saved;
        }
    }
    return authToken;
}

// 设置 token
function setToken(token) {
    authToken = token;
    localStorage.setItem('token', token);
}

// 清空 token
function clearToken() {
    authToken = null;
    localStorage.removeItem('token');
}

// 带认证的 fetch
async function authFetch(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = getToken();
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }
    return fetch(url, { ...options, headers });
}

// 显示登录弹窗
function showLoginForm() {
    document.getElementById('loginModal').style.display = 'flex';
    document.getElementById('loginUsername').focus();
}

// 执行登录
async function doLogin() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    if (!username || !password) {
        alert('请输入用户名和密码');
        return;
    }

    const res = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });

    const data = await res.json();
    if (data.success) {
        setToken(data.token);
        document.getElementById('loginModal').style.display = 'none';
        loadStocks();
    } else {
        alert(data.error || '登录失败');
    }
}

// 回车登录
document.getElementById('loginPassword').addEventListener('keypress', e => {
    if (e.key === 'Enter') doLogin();
});

// 加载股票列表
async function loadStocks() {
    const res = await authFetch('/api/stocks');
    if (res.status === 401) {
        clearToken();
        showLoginForm();
        return;
    }
    stocks = await res.json();
    document.getElementById('stockCount').textContent = stocks.length;

    // 获取刷新间隔配置
    const alertsRes = await authFetch('/api/alerts');
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
    if (!/^\d{6}$/.test(code)) {
        alert('请输入6位股票代码');
        return;
    }

    const res = await authFetch('/api/stocks', {
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

    const res = await authFetch(`/api/stocks/${code}`, {method: 'DELETE'});
    const result = await res.json();
    if (result.success) {
        loadStocks();
    }
}

// 刷新数据
async function refreshData() {
    const res = await authFetch('/api/realtime');
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
    const res = await authFetch(`/api/minute/${code}`);
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
    const res = await authFetch('/api/alerts');
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

    await authFetch('/api/alerts', {
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
        // 停止告警刷新
        if (window.alertRefreshTimer) {
            clearInterval(window.alertRefreshTimer);
            window.alertRefreshTimer = null;
        }
    } else if (tabName === 'alerts') {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('tab-alerts').classList.add('active');
        loadAlertHistory();
        if (!window.alertRefreshTimer) {
            window.alertRefreshTimer = setInterval(loadAlertHistory, 30000);
        }
    } else if (tabName === 'heatmap') {
        document.querySelector('.tab-btn:nth-child(3)').classList.add('active');
        document.getElementById('tab-heatmap').classList.add('active');
    } else if (tabName === 'admin') {
        document.querySelector('.tab-btn:nth-child(4)').classList.add('active');
        document.getElementById('tab-admin').classList.add('active');
        loadUsers();
    }
}

let lastAlertCount = 0;
let alertCurrentPage = 1;

// 加载告警历史
async function loadAlertHistory() {
    try {
        const days = document.getElementById('alertFilterDays').value;
        const code = document.getElementById('alertFilterCode').value;

        let url = '/api/alerts/history?days=' + days + '&page=' + alertCurrentPage + '&page_size=30';
        if (code) url += '&code=' + code;

        const res = await authFetch(url);
        const result = await res.json();
        const list = document.getElementById('alertList');

        const alerts = result.data || result;
        const total = result.total || alerts.length;
        const totalPages = result.total_pages || 1;

        if (!alerts || alerts.length === 0) {
            list.innerHTML = '<div class="empty-state"><h2>暂无告警记录</h2><p>触发告警后会显示在这里</p></div>';
            document.getElementById('alertPagination').style.display = 'none';
            return;
        }

        document.getElementById('alertPagination').style.display = 'flex';
        document.getElementById('alertPageInfo').textContent = alertCurrentPage + '/' + totalPages + ' (共' + total + '条)';

        const today = new Date().toISOString().slice(0, 10);

        list.innerHTML = alerts.map(alert => {
            const isToday = alert.alert_time && alert.alert_time.slice(0, 10) === today;
            const severity = alert.severity || 'low';
            const icon = alert.type === 'price_change' ? '📈' :
                         alert.type === 'rapid_change' ? '⚡' :
                         alert.type === 'volume_surge' ? '📊' :
                         alert.type === 'continuous_up' ? '📈📈' :
                         alert.type === 'continuous_down' ? '📉📉' : '🚨';
            const typeDesc = {
                'price_change': '涨跌幅告警',
                'rapid_change': '快速波动',
                'volume_surge': '放量告警',
                'trend_fit': '趋势拟合',
                'continuous_up': '连续上涨',
                'continuous_down': '连续下跌'
            }[alert.type] || '告警';
            const todayClass = isToday ? ' today' : '';
            return '<div class="alert-item ' + severity + todayClass + '">' +
                '<span class="alert-icon">' + icon + '</span>' +
                '<div class="alert-info">' +
                '<div class="alert-msg">' + alert.msg + '</div>' +
                '<div class="alert-time">' + alert.alert_time + ' · ' + typeDesc + '</div>' +
                '</div></div>';
        }).join('');
    } catch (e) {
        console.error('加载告警历史失败:', e);
    }
}

// 告警分页
function goToAlertPage(delta) {
    const pageInfo = document.getElementById('alertPageInfo').textContent;
    const match = pageInfo.match(/(\d+)\/(\d+)/);
    if (match) {
        const currentPage = parseInt(match[1]);
        const totalPages = parseInt(match[2]);
        const newPage = currentPage + delta;
        if (newPage >= 1 && newPage <= totalPages) {
            alertCurrentPage = newPage;
            loadAlertHistory();
        }
    }
}

// 清空告警历史
async function clearAlertHistory() {
    const days = prompt('请输入要清理几天前的告警（输入数字，如 7 清理7天前的所有告警）：');
    if (days === null || days === '') return;
    const numDays = parseInt(days);
    if (isNaN(numDays) || numDays < 1) {
        alert('请输入有效的天数');
        return;
    }
    if (!confirm('确定要清空 ' + numDays + ' 天前的所有告警记录吗？')) return;

    await authFetch('/api/alerts/history?action=clear&days=' + numDays, {method: 'GET'});
    alert('已清理 ' + numDays + ' 天前的告警记录');
    loadAlertHistory();
}

// 用户管理
async function loadUsers() {
    try {
        const res = await authFetch('/api/admin/users');
        const users = await res.json();
        document.getElementById('userList').innerHTML = users.map(u =>
            '<tr style="border-bottom:1px solid #333">' +
            '<td style="padding:10px">' + u.id + '</td>' +
            '<td style="padding:10px">' + u.username + '</td>' +
            '<td style="padding:10px">' + u.created_at + '</td>' +
            '<td style="padding:10px">' +
            '<button onclick="editUser(\'' + u.username + '\')" style="background:#00d4ff;color:#000;padding:5px 10px;border:none;border-radius:4px;cursor:pointer;margin-right:5px">改密</button>' +
            (u.username !== 'admin' ?
            '<button onclick="deleteUser(\'' + u.username + '\')" style="background:#ff6b6b;color:#fff;padding:5px 10px;border:none;border-radius:4px;cursor:pointer">删除</button>' :
            '<span style="color:#888">管理员</span>') +
            '</td></tr>'
        ).join('');
    } catch(e) {
        console.error(e);
    }
}

// 修改用户密码
function editUser(username) {
    const newPassword = prompt('请输入用户 ' + username + ' 的新密码:');
    if (!newPassword) return;
    if (newPassword.length < 1) {
        alert('密码不能为空');
        return;
    }
    authFetch('/api/admin/users/' + username, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password: newPassword})
    }).then(r => r.json()).then(data => {
        alert(data.message || data.error);
    }).catch(e => {
        alert('修改失败');
    });
}

async function createUser() {
    const username = document.getElementById('newUsername').value;
    const password = document.getElementById('newPassword').value;
    if (!username || !password) {
        alert('请输入用户名和密码');
        return;
    }
    const res = await authFetch('/api/admin/users', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
    });
    const result = await res.json();
    alert(result.message || result.error);
    if (result.success) {
        document.getElementById('newUsername').value = '';
        document.getElementById('newPassword').value = '';
        loadUsers();
    }
}

async function deleteUser(username) {
    if (!confirm('确定要删除用户 ' + username + ' 吗？')) return;
    const res = await authFetch('/api/admin/users/' + username, {method: 'DELETE'});
    const result = await res.json();
    alert(result.message || result.error);
    if (result.success) {
        loadUsers();
    }
}

// 初始化 - 检查登录状态
async function init() {
    const token = getToken();
    if (!token) {
        showLoginForm();
    } else {
        // 验证 token 是否有效
        const res = await authFetch('/api/me');
        if (res.status === 200) {
            const user = await res.json();
            if (user.username === 'admin') {
                document.getElementById('adminTabBtn').style.display = 'inline-block';
            }
            loadStocks();
        } else {
            clearToken();
            showLoginForm();
        }
    }
}

// 启动
init();

// 导出函数到全局
window.doLogin = doLogin;
window.showLoginForm = showLoginForm;
window.addStock = addStock;
window.deleteStock = deleteStock;
window.showChart = showChart;
window.closeModal = closeModal;
window.openAlertConfig = openAlertConfig;
window.closeAlertModal = closeAlertModal;
window.saveAlertConfig = saveAlertConfig;
window.switchTab = switchTab;
window.loadAlertHistory = loadAlertHistory;
window.goToAlertPage = goToAlertPage;
window.clearAlertHistory = clearAlertHistory;
window.editUser = editUser;
window.createUser = createUser;
window.deleteUser = deleteUser;
