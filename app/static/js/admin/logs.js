// 日志管理页面JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 全局变量 - 当前页码
    const currentPage = {
        'sign-logs': 1,
        'operation-logs': 1,
        'login-logs': 1
    };
    
    // 初始化页面
    initTabSystem();
    initOperationLogsTab(); // 先初始化操作日志选项卡
    initLoginLogsTab();
    initSignLogsTab();
    
    // ===== 选项卡系统 =====
    function initTabSystem() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                // 移除所有活动状态
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                // 为当前点击的选项卡设置活动状态
                this.classList.add('active');
                const tabId = this.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }
    
    // ===== 签到日志相关功能 =====
    function initSignLogsTab() {
        // 首次加载数据
        loadSignLogs(1);
        
        // 搜索按钮点击事件
        document.getElementById('sign-search').addEventListener('click', function() {
            loadSignLogs(1);
        });
        
        // 重置按钮点击事件
        document.getElementById('sign-reset').addEventListener('click', function() {
            document.getElementById('sign-username').value = '';
            document.getElementById('sign-date-from').value = '';
            document.getElementById('sign-date-to').value = '';
            document.getElementById('sign-type').value = 'all';
            document.getElementById('sign-status').value = 'all';
            loadSignLogs(1);
        });
        
        // 导出按钮点击事件
        document.getElementById('sign-export').addEventListener('click', function() {
            exportSignLogs();
        });
    }
    
    // 加载签到日志数据
    function loadSignLogs(page) {
        const username = document.getElementById('sign-username').value;
        const dateFrom = document.getElementById('sign-date-from').value;
        const dateTo = document.getElementById('sign-date-to').value;
        const signType = document.getElementById('sign-type').value;
        const status = document.getElementById('sign-status').value;
        
        // 保存当前页码
        currentPage['sign-logs'] = page;
        
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
                    renderPagination('sign-logs', response.data);
                } else {
                    showError(tableBody, response.data.message || '获取签到日志失败');
                }
            })
            .catch(function(error) {
                showError(tableBody, '获取签到日志失败: ' + error.message);
            });
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
    
    // ===== 操作日志相关功能 =====
    function initOperationLogsTab() {
        // 首次加载数据
        loadOperationLogs(1);
        
        // 搜索按钮点击事件
        document.getElementById('operation-search').addEventListener('click', function() {
            loadOperationLogs(1);
        });
        
        // 重置按钮点击事件
        document.getElementById('operation-reset').addEventListener('click', function() {
            document.getElementById('operation-username').value = '';
            document.getElementById('operation-date-from').value = '';
            document.getElementById('operation-date-to').value = '';
            document.getElementById('operation-type').value = 'all';
            document.getElementById('operation-status').value = 'all';
            loadOperationLogs(1);
        });
        
        // 导出按钮点击事件
        document.getElementById('operation-export').addEventListener('click', function() {
            exportOperationLogs();
        });
    }
    
    // 加载操作日志数据
    function loadOperationLogs(page) {
        const username = document.getElementById('operation-username').value;
        const dateFrom = document.getElementById('operation-date-from').value;
        const dateTo = document.getElementById('operation-date-to').value;
        const operationType = document.getElementById('operation-type').value;
        const status = document.getElementById('operation-status').value;
        
        // 保存当前页码
        currentPage['operation-logs'] = page;
        
        // 构建查询参数
        const params = new URLSearchParams({
            page: page,
            limit: 50
        });
        
        if (username) params.append('username', username);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (operationType !== 'all') params.append('operation_type', operationType);
        if (status !== 'all') params.append('status', status);
        
        // 显示加载状态
        const tableBody = document.querySelector('#operation-logs-table tbody');
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center">加载中...</td></tr>';
        
        // 发送请求
        axios.get(`/admin/operation-logs-api?${params.toString()}`)
            .then(function(response) {
                if (response.data.success) {
                    renderOperationLogsTable(response.data);
                    renderPagination('operation-logs', response.data);
                } else {
                    showError(tableBody, response.data.message || '获取操作日志失败');
                }
            })
            .catch(function(error) {
                showError(tableBody, '获取操作日志失败: ' + error.message);
            });
    }
    
    // 渲染操作日志表格
    function renderOperationLogsTable(data) {
        const tableBody = document.querySelector('#operation-logs-table tbody');
        tableBody.innerHTML = '';
        
        if (data.logs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center">暂无数据</td></tr>';
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
                <td>${log.operation_time_formatted || new Date(log.operation_time * 1000).toLocaleString()}</td>
                <td>${log.operation_type}</td>
                <td>${log.operation_detail || '-'}</td>
                <td class="${log.status === '成功' ? 'success' : 'failure'}">${log.status}</td>
                <td>${log.ip_address || '-'}</td>
                <td>${log.remarks || '-'}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    // 导出操作日志
    function exportOperationLogs() {
        const username = document.getElementById('operation-username').value;
        const dateFrom = document.getElementById('operation-date-from').value;
        const dateTo = document.getElementById('operation-date-to').value;
        const operationType = document.getElementById('operation-type').value;
        const status = document.getElementById('operation-status').value;
        
        // 构建查询参数
        const params = new URLSearchParams({
            limit: 1000 // 导出更多记录
        });
        
        if (username) params.append('username', username);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (operationType !== 'all') params.append('operation_type', operationType);
        if (status !== 'all') params.append('status', status);
        
        // 发送请求获取所有符合条件的数据
        axios.get(`/admin/operation-logs-api?${params.toString()}`)
            .then(function(response) {
                if (response.data.success) {
                    exportToCSV(response.data.logs, '操作日志', [
                        { key: 'id', label: 'ID' },
                        { key: 'username', label: '用户名' },
                        { key: 'operation_time_formatted', label: '操作时间' },
                        { key: 'operation_type', label: '操作类型' },
                        { key: 'operation_detail', label: '操作详情' },
                        { key: 'status', label: '状态' },
                        { key: 'ip_address', label: 'IP地址' },
                        { key: 'remarks', label: '备注' }
                    ]);
                } else {
                    alert('导出失败: ' + (response.data.message || '未知错误'));
                }
            })
            .catch(function(error) {
                alert('导出失败: ' + error.message);
            });
    }
    
    // ===== 登录日志相关功能 =====
    function initLoginLogsTab() {
        // 首次加载数据
        loadLoginLogs(1);
        
        // 搜索按钮点击事件
        document.getElementById('login-search').addEventListener('click', function() {
            loadLoginLogs(1);
        });
        
        // 重置按钮点击事件
        document.getElementById('login-reset').addEventListener('click', function() {
            document.getElementById('login-username').value = '';
            document.getElementById('login-user-id').value = '';
            document.getElementById('login-date-from').value = '';
            document.getElementById('login-date-to').value = '';
            document.getElementById('login-status').value = 'all';
            loadLoginLogs(1);
        });
        
        // 导出按钮点击事件
        document.getElementById('login-export').addEventListener('click', function() {
            exportLoginLogs();
        });
    }
    
    // 加载登录日志数据
    function loadLoginLogs(page) {
        const username = document.getElementById('login-username').value;
        const userId = document.getElementById('login-user-id').value;
        const dateFrom = document.getElementById('login-date-from').value;
        const dateTo = document.getElementById('login-date-to').value;
        const status = document.getElementById('login-status').value;
        
        // 保存当前页码
        currentPage['login-logs'] = page;
        
        // 构建查询参数
        const params = new URLSearchParams({
            page: page,
            limit: 50
        });
        
        if (username) params.append('username', username);
        if (userId) params.append('user_id', userId);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (status !== 'all') params.append('status', status);
        
        // 显示加载状态
        const tableBody = document.querySelector('#login-logs-table tbody');
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center">加载中...</td></tr>';
        
        // 发送请求
        axios.get(`/admin/login-logs-api?${params.toString()}`)
            .then(function(response) {
                if (response.data.success) {
                    renderLoginLogsTable(response.data);
                    renderPagination('login-logs', response.data);
                } else {
                    showError(tableBody, response.data.message || '获取登录日志失败');
                }
            })
            .catch(function(error) {
                showError(tableBody, '获取登录日志失败: ' + error.message);
            });
    }
    
    // 渲染登录日志表格
    function renderLoginLogsTable(data) {
        const tableBody = document.querySelector('#login-logs-table tbody');
        tableBody.innerHTML = '';
        
        if (data.logs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">暂无数据</td></tr>';
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
                <td>${log.user_id}</td>
                <td>${log.username || '-'}</td>
                <td>${log.login_time_formatted || new Date(log.login_time * 1000).toLocaleString()}</td>
                <td>${log.ip_address || '-'}</td>
                <td class="${log.status === '成功' ? 'success' : 'failure'}">${log.status}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    // 导出登录日志
    function exportLoginLogs() {
        const username = document.getElementById('login-username').value;
        const userId = document.getElementById('login-user-id').value;
        const dateFrom = document.getElementById('login-date-from').value;
        const dateTo = document.getElementById('login-date-to').value;
        const status = document.getElementById('login-status').value;
        
        // 构建查询参数
        const params = new URLSearchParams({
            limit: 1000 // 导出更多记录
        });
        
        if (username) params.append('username', username);
        if (userId) params.append('user_id', userId);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (status !== 'all') params.append('status', status);
        
        // 发送请求获取所有符合条件的数据
        axios.get(`/admin/login-logs-api?${params.toString()}`)
            .then(function(response) {
                if (response.data.success) {
                    exportToCSV(response.data.logs, '登录日志', [
                        { key: 'id', label: 'ID' },
                        { key: 'user_id', label: '用户ID' },
                        { key: 'username', label: '用户名' },
                        { key: 'login_time_formatted', label: '登录时间' },
                        { key: 'ip_address', label: 'IP地址' },
                        { key: 'status', label: '状态' }
                    ]);
                } else {
                    alert('导出失败: ' + (response.data.message || '未知错误'));
                }
            })
            .catch(function(error) {
                alert('导出失败: ' + error.message);
            });
    }
    
    // ===== 通用工具函数 =====
    
    // 渲染分页控件
    function renderPagination(tabId, data) {
        const paginationElement = document.getElementById(`${tabId}-pagination`);
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
                    ${currentPageNum === 1 ? 'disabled' : `onclick="changePage('${tabId}', ${currentPageNum - 1})"`}>
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
                <button class="pagination-button" onclick="changePage('${tabId}', 1)">1</button>
            `;
            
            if (startPage > 2) {
                paginationHTML += '<span class="pagination-ellipsis">...</span>';
            }
        }
        
        // 页码
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <button class="pagination-button ${i === currentPageNum ? 'active' : ''}" 
                        onclick="changePage('${tabId}', ${i})">
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
                <button class="pagination-button" onclick="changePage('${tabId}', ${totalPages})">
                    ${totalPages}
                </button>
            `;
        }
        
        // 下一页按钮
        paginationHTML += `
            <button class="pagination-button ${currentPageNum === totalPages ? 'disabled' : ''}" 
                    ${currentPageNum === totalPages ? 'disabled' : `onclick="changePage('${tabId}', ${currentPageNum + 1})"`}>
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
    window.changePage = function(tabId, page) {
        if (tabId === 'sign-logs') {
            loadSignLogs(page);
        } else if (tabId === 'operation-logs') {
            loadOperationLogs(page);
        } else if (tabId === 'login-logs') {
            loadLoginLogs(page);
        }
    };
}); 