document.addEventListener('DOMContentLoaded', function() {
    // 初始加载数据
    loadSignLogs(1);
    loadStatistics();
    
    // 初始化当前页码
    let currentPage = 1;
    
    // 搜索按钮点击事件
    document.getElementById('sign-search').addEventListener('click', function() {
        loadSignLogs(1);
        loadStatistics();
    });
    
    // 重置按钮点击事件
    document.getElementById('sign-reset').addEventListener('click', function() {
        document.getElementById('sign-username').value = '';
        document.getElementById('sign-date-from').value = '';
        document.getElementById('sign-date-to').value = '';
        document.getElementById('sign-type').value = 'all';
        document.getElementById('sign-status').value = 'all';
        loadSignLogs(1);
        loadStatistics();
    });
    
    // 导出按钮点击事件
    document.getElementById('sign-export').addEventListener('click', function() {
        exportSignLogs();
    });
});

// 加载签到日志数据
function loadSignLogs(page) {
    const username = document.getElementById('sign-username').value;
    const dateFrom = document.getElementById('sign-date-from').value;
    const dateTo = document.getElementById('sign-date-to').value;
    const signType = document.getElementById('sign-type').value;
    const status = document.getElementById('sign-status').value;
    
    // 保存当前页码
    currentPage = page;
    
    // 构建查询参数
    const params = new URLSearchParams({
        page: page,
        limit: 50
    });
    
    if (username) params.append('username', username);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (signType !== 'all') params.append('sign_type', signType);
    if (status !== 'all') params.append('status', status);
    
    // 显示加载状态
    const tableBody = document.querySelector('#sign-logs-table tbody');
    tableBody.innerHTML = '<tr><td colspan="7" class="text-center">加载中...</td></tr>';
    
    // 发送请求
    axios.get(`/admin/sign-logs-api?${params.toString()}`)
        .then(function(response) {
            if (response.data.success) {
                renderSignLogsTable(response.data);
                renderPagination(response.data);
            } else {
                showError(tableBody, response.data.message || '获取签到日志失败');
            }
        })
        .catch(function(error) {
            showError(tableBody, '获取签到日志失败: ' + error.message);
        });
}

// 加载统计数据
function loadStatistics() {
    const username = document.getElementById('sign-username').value;
    const dateFrom = document.getElementById('sign-date-from').value;
    const dateTo = document.getElementById('sign-date-to').value;
    const signType = document.getElementById('sign-type').value;
    const status = document.getElementById('sign-status').value;
    
    // 构建查询参数 - 使用大量数据进行统计
    const params = new URLSearchParams({
        limit: 5000
    });
    
    if (username) params.append('username', username);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (signType !== 'all') params.append('sign_type', signType);
    if (status !== 'all') params.append('status', status);
    
    // 发送请求
    axios.get(`/admin/sign-logs-api?${params.toString()}`)
        .then(function(response) {
            if (response.data.success) {
                calculateStatistics(response.data.logs);
            }
        })
        .catch(function(error) {
            console.error('获取统计数据失败:', error);
        });
}

// 计算统计数据
function calculateStatistics(logs) {
    // 获取当前日期
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayTimestamp = today.getTime() / 1000;
    
    // 获取本月第一天
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    const firstDayTimestamp = firstDayOfMonth.getTime() / 1000;
    
    // 今日打卡次数
    const todaySignCount = logs.filter(log => log.sign_time >= todayTimestamp).length;
    
    // 成功率
    let successCount = 0;
    logs.forEach(log => {
        if (log.status === '成功') successCount++;
    });
    const successRate = logs.length > 0 ? (successCount / logs.length * 100).toFixed(2) : 0;
    
    // 本月打卡次数
    const thisMonthSignCount = logs.filter(log => log.sign_time >= firstDayTimestamp).length;
    
    // 计算日均打卡次数
    // 获取日期范围
    let startDate = new Date();
    let endDate = new Date();
    
    if (logs.length > 0) {
        // 找到最早和最晚的打卡记录
        let earliestTime = logs[logs.length - 1].sign_time;
        let latestTime = logs[0].sign_time;
        
        startDate = new Date(earliestTime * 1000);
        startDate.setHours(0, 0, 0, 0);
        
        endDate = new Date(latestTime * 1000);
        endDate.setHours(23, 59, 59, 999);
        
        // 计算天数差异
        const dayDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
        const avgPerDay = dayDiff > 0 ? (logs.length / dayDiff).toFixed(2) : logs.length;
        
        document.getElementById('avg-per-day').querySelector('.stats-value').textContent = avgPerDay;
    } else {
        document.getElementById('avg-per-day').querySelector('.stats-value').textContent = '0';
    }
    
    // 更新统计卡片
    document.getElementById('today-sign-count').querySelector('.stats-value').textContent = todaySignCount;
    document.getElementById('success-rate').querySelector('.stats-value').textContent = successRate + '%';
    document.getElementById('this-month-sign').querySelector('.stats-value').textContent = thisMonthSignCount;
}

// 渲染签到日志表格
function renderSignLogsTable(data) {
    const tableBody = document.querySelector('#sign-logs-table tbody');
    tableBody.innerHTML = '';
    
    if (data.logs.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">暂无数据</td></tr>';
        return;
    }
    
    data.logs.forEach(log => {
        const row = document.createElement('tr');
        
        // 设置行样式
        if (log.status === '成功') {
            row.classList.add('success-row');
        } else if (log.status === '失败') {
            row.classList.add('failure-row');
        }
        
        row.innerHTML = `
            <td>${log.id}</td>
            <td>${log.username}</td>
            <td>${log.sign_time_formatted || new Date(log.sign_time * 1000).toLocaleString()}</td>
            <td>${log.sign_type}</td>
            <td class="${log.status === '成功' ? 'success' : 'failure'}">${log.status}</td>
            <td>${log.remark || '-'}</td>
            <td>${log.ip_address || '-'}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

// 导出签到日志
function exportSignLogs() {
    const username = document.getElementById('sign-username').value;
    const dateFrom = document.getElementById('sign-date-from').value;
    const dateTo = document.getElementById('sign-date-to').value;
    const signType = document.getElementById('sign-type').value;
    const status = document.getElementById('sign-status').value;
    
    // 构建查询参数
    const params = new URLSearchParams({
        limit: 1000 // 导出更多记录
    });
    
    if (username) params.append('username', username);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (signType !== 'all') params.append('sign_type', signType);
    if (status !== 'all') params.append('status', status);
    
    // 发送请求获取所有符合条件的数据
    axios.get(`/admin/sign-logs-api?${params.toString()}`)
        .then(function(response) {
            if (response.data.success) {
                exportToCSV(response.data.logs, '签到日志', [
                    { key: 'id', label: 'ID' },
                    { key: 'username', label: '用户名' },
                    { key: 'sign_time_formatted', label: '签到时间' },
                    { key: 'sign_type', label: '签到类型' },
                    { key: 'status', label: '状态' },
                    { key: 'remark', label: '备注' },
                    { key: 'ip_address', label: 'IP地址' }
                ]);
            } else {
                alert('导出失败: ' + (response.data.message || '未知错误'));
            }
        })
        .catch(function(error) {
            alert('导出失败: ' + error.message);
        });
}

// 渲染分页控件
function renderPagination(data) {
    const paginationElement = document.getElementById(`sign-logs-pagination`);
    const totalPages = data.pages;
    const currentPageNum = data.page;
    
    if (totalPages <= 1) {
        paginationElement.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // 上一页按钮
    paginationHTML += `
        <button class="pagination-button ${currentPageNum === 1 ? 'disabled' : ''}" 
                ${currentPageNum === 1 ? 'disabled' : `onclick="changePage(${currentPageNum - 1})"`}>
            上一页
        </button>
    `;
    
    // 页码按钮
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPageNum - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    // 第一页
    if (startPage > 1) {
        paginationHTML += `
            <button class="pagination-button" onclick="changePage(1)">1</button>
        `;
        
        if (startPage > 2) {
            paginationHTML += '<span class="pagination-ellipsis">...</span>';
        }
    }
    
    // 页码
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="pagination-button ${i === currentPageNum ? 'active' : ''}" 
                    onclick="changePage(${i})">
                ${i}
            </button>
        `;
    }
    
    // 最后一页
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += '<span class="pagination-ellipsis">...</span>';
        }
        
        paginationHTML += `
            <button class="pagination-button" onclick="changePage(${totalPages})">
                ${totalPages}
            </button>
        `;
    }
    
    // 下一页按钮
    paginationHTML += `
        <button class="pagination-button ${currentPageNum === totalPages ? 'disabled' : ''}" 
                ${currentPageNum === totalPages ? 'disabled' : `onclick="changePage(${currentPageNum + 1})"`}>
            下一页
        </button>
    `;
    
    // 页码信息
    paginationHTML += `
        <span class="pagination-info">
            第 ${currentPageNum} 页 / 共 ${totalPages} 页 (${data.total} 条记录)
        </span>
    `;
    
    paginationElement.innerHTML = paginationHTML;
}

// 显示错误信息
function showError(tableBody, message) {
    tableBody.innerHTML = `<tr><td colspan="${tableBody.closest('table').querySelectorAll('th').length}" class="text-center text-danger">${message}</td></tr>`;
}

// 导出为CSV
function exportToCSV(data, title, columns) {
    // 准备CSV内容
    let csvContent = columns.map(col => `"${col.label}"`).join(',') + '\n';
    
    data.forEach(item => {
        csvContent += columns.map(col => {
            const value = item[col.key] || '';
            return `"${value.toString().replace(/"/g, '""')}"`;
        }).join(',') + '\n';
    });
    
    // 转换为Blob
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // 创建下载链接
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `${title}_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 暴露全局changePage函数供分页控件使用
window.changePage = function(page) {
    loadSignLogs(page);
};
