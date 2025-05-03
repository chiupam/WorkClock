let users = [];
let filteredUsers = [];
let currentPage = 1;
const usersPerPage = 10;

document.addEventListener('DOMContentLoaded', function() {
    // 加载用户数据
    loadUsers();
    
    // 添加搜索框事件监听
    document.getElementById('search-input').addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            searchUsers();
        }
    });
});

// 加载用户数据
function loadUsers() {
    axios.get('/admin/users-api')
        .then(function(response) {
            if (response.data.success) {
                users = response.data.users;
                filteredUsers = [...users]; // 复制用户数据
                
                // 更新统计信息
                updateStats();
                
                // 渲染用户表格
                renderUserTable();
                
                // 渲染分页
                renderPagination();
            } else {
                document.getElementById('users-table-body').innerHTML = 
                    `<tr><td colspan="7" class="no-users">加载用户失败: ${response.data.message}</td></tr>`;
            }
        })
        .catch(function(error) {
            console.error('获取用户数据失败:', error);
            document.getElementById('users-table-body').innerHTML = 
                `<tr><td colspan="7" class="no-users">获取用户数据失败，请检查网络连接</td></tr>`;
        });
}

// 更新统计信息
function updateStats() {
    const totalUsers = users.length;
    
    // 计算最近一周活跃用户
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    const oneWeekAgoTimestamp = Math.floor(oneWeekAgo.getTime() / 1000);
    
    const activeUsers = users.filter(user => user.last_activity >= oneWeekAgoTimestamp).length;
    const inactiveUsers = totalUsers - activeUsers;
    
    document.getElementById('total-users').textContent = totalUsers;
    document.getElementById('active-users').textContent = activeUsers;
    document.getElementById('inactive-users').textContent = inactiveUsers;
}

// 搜索用户
function searchUsers() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    if (searchTerm.trim() === '') {
        filteredUsers = [...users]; // 清空搜索词，显示所有用户
    } else {
        filteredUsers = users.filter(user => 
            user.username.toLowerCase().includes(searchTerm) || 
            user.department_name.toLowerCase().includes(searchTerm) || 
            user.position.toLowerCase().includes(searchTerm) ||
            user.user_id.toLowerCase().includes(searchTerm)
        );
    }
    
    currentPage = 1; // 重置到第一页
    renderUserTable();
    renderPagination();
}

// 渲染用户表格
function renderUserTable() {
    const tableBody = document.getElementById('users-table-body');
    const start = (currentPage - 1) * usersPerPage;
    const end = start + usersPerPage;
    const pageUsers = filteredUsers.slice(start, end);
    
    if (pageUsers.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" class="no-users">没有找到匹配的用户</td></tr>`;
        return;
    }
    
    let html = '';
    pageUsers.forEach(user => {
        const firstLogin = new Date(user.first_login * 1000).toLocaleString();
        const lastActivity = new Date(user.last_activity * 1000).toLocaleString();
        
        html += `
            <tr>
                <td>${user.username}</td>
                <td>${user.user_id}</td>
                <td>${user.department_name}</td>
                <td>${user.position}</td>
                <td>${firstLogin}</td>
                <td>${lastActivity}</td>
                <td class="user-actions">
                    <button class="action-view" onclick="viewUserDetails(${user.id})">查看</button>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

// 渲染分页
function renderPagination() {
    const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
    const pagination = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let html = `
        <button onclick="changePage(1)" ${currentPage === 1 ? 'disabled' : ''}>首页</button>
        <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>上一页</button>
    `;
    
    // 显示当前页码周围的页码
    const maxPagesToShow = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
    
    if (endPage - startPage + 1 < maxPagesToShow) {
        startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button onclick="changePage(${i})" class="${i === currentPage ? 'active' : ''}">${i}</button>`;
    }
    
    html += `
        <button onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>下一页</button>
        <button onclick="changePage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>末页</button>
    `;
    
    pagination.innerHTML = html;
}

// 切换页面
function changePage(page) {
    currentPage = page;
    renderUserTable();
    renderPagination();
    
    // 滚动到顶部
    window.scrollTo(0, 0);
}

// 查看用户详情
function viewUserDetails(userId) {
    const user = users.find(u => u.id === userId);
    if (user) {
        alert(`用户详情将在此显示: ${user.username}`);
        // 这里可以实现显示用户详情的逻辑，例如弹出模态框或跳转到用户详情页
    }
}