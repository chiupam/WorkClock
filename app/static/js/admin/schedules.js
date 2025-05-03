document.addEventListener('DOMContentLoaded', function() {
    // 显示当前时间并自动更新
    function updateClock() {
        const now = new Date();
        const timeDisplay = document.querySelector('.current-time');
        if (timeDisplay) {
            const formattedTime = now.getFullYear() + '-' + 
                                 padZero(now.getMonth() + 1) + '-' + 
                                 padZero(now.getDate()) + ' ' + 
                                 padZero(now.getHours()) + ':' + 
                                 padZero(now.getMinutes()) + ':' + 
                                 padZero(now.getSeconds());
            timeDisplay.textContent = '当前时间: ' + formattedTime;
        }
    }
    
    function padZero(num) {
        return num < 10 ? '0' + num : num;
    }
    
    // 初始更新并设置定时器
    updateClock();
    setInterval(updateClock, 1000);
    
    // 加载定时任务数据
    loadSchedulesData();
    
    // 刷新按钮事件
    document.getElementById('refreshBtn').addEventListener('click', function() {
        loadSchedulesData();
    });
    
    // 加载定时任务数据
    function loadSchedulesData() {
        const container = document.getElementById('schedulesTableContainer');
        
        // 显示加载中状态
        container.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
        `;
        
        // 使用axios获取数据
        axios.get('/admin/schedules-api')
            .then(function(response) {
                if (response.data.success) {
                    renderSchedulesTable(response.data.schedules);
                } else {
                    container.innerHTML = `
                        <div class="empty-state">
                            <p>加载数据失败: ${response.data.message}</p>
                        </div>
                    `;
                }
            })
            .catch(function(error) {
                console.error('获取定时任务数据失败:', error);
                container.innerHTML = `
                    <div class="empty-state">
                        <p>加载数据失败，请重试</p>
                    </div>
                `;
            });
    }
    
    // 渲染定时任务表格
    function renderSchedulesTable(schedules) {
        const container = document.getElementById('schedulesTableContainer');
        
        if (!schedules || schedules.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无定时任务数据</p>
                </div>
            `;
            return;
        }
        
        let tableHtml = `
            <table class="schedules-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>用户名</th>
                        <th>用户ID</th>
                        <th>部门</th>
                        <th>职位</th>
                        <th>上午打卡</th>
                        <th>下午打卡</th>
                        <th>选择状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        schedules.forEach(schedule => {
            const createdDate = new Date(schedule.created_at);
            const formattedDate = createdDate.getFullYear() + '-' + 
                                padZero(createdDate.getMonth() + 1) + '-' + 
                                padZero(createdDate.getDate()) + ' ' + 
                                padZero(createdDate.getHours()) + ':' + 
                                padZero(createdDate.getMinutes());
                                
            // 格式化上午打卡时间
            let morningTimesHtml = '';
            if (schedule.morning && schedule.morning_times.length > 0) {
                schedule.morning_times.forEach(time => {
                    morningTimesHtml += `<span class="time-badge">${time}</span>`;
                });
            } else {
                morningTimesHtml = `<span class="status-badge disabled">未设置</span>`;
            }
            
            // 格式化下午打卡时间
            let afternoonTimesHtml = '';
            if (schedule.afternoon && schedule.afternoon_times.length > 0) {
                schedule.afternoon_times.forEach(time => {
                    afternoonTimesHtml += `<span class="time-badge">${time}</span>`;
                });
            } else {
                afternoonTimesHtml = `<span class="status-badge disabled">未设置</span>`;
            }
            
            // 格式化选择状态
            let selectionStatusHtml = '';
            
            // 上午选择状态
            selectionStatusHtml += '<div class="selection-status">上午: ';
            if (Array.isArray(schedule.morning_selections)) {
                schedule.morning_selections.forEach((status, index) => {
                    selectionStatusHtml += `<span class="selection-dot ${status === 1 ? 'selected' : 'unselected'}" title="时间点${index+1}"></span>`;
                });
            }
            selectionStatusHtml += '</div>';
            
            // 下午选择状态
            selectionStatusHtml += '<div class="selection-status">下午: ';
            if (Array.isArray(schedule.afternoon_selections)) {
                schedule.afternoon_selections.forEach((status, index) => {
                    selectionStatusHtml += `<span class="selection-dot ${status === 1 ? 'selected' : 'unselected'}" title="时间点${index+1}"></span>`;
                });
            }
            selectionStatusHtml += '</div>';
            
            tableHtml += `
                <tr data-id="${schedule.id}">
                    <td>${schedule.id}</td>
                    <td>${schedule.username}</td>
                    <td>${schedule.user_id}</td>
                    <td>${schedule.department}</td>
                    <td>${schedule.position}</td>
                    <td>${morningTimesHtml}</td>
                    <td>${afternoonTimesHtml}</td>
                    <td>${selectionStatusHtml}</td>
                    <td>${formattedDate}</td>
                    <td>
                        <button class="action-btn delete-btn" data-id="${schedule.id}">删除</button>
                    </td>
                </tr>
            `;
        });
        
        tableHtml += `
                </tbody>
            </table>
        `;
        
        container.innerHTML = tableHtml;
        
        // 绑定删除按钮事件
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const scheduleId = this.getAttribute('data-id');
                if (confirm('确定要删除此定时任务吗？此操作不可恢复。')) {
                    deleteSchedule(scheduleId);
                }
            });
        });
    }
    
    // 删除定时任务
    function deleteSchedule(scheduleId) {
        axios.delete(`/admin/schedules/${scheduleId}`)
            .then(function(response) {
                if (response.data.success) {
                    // 刷新数据
                    loadSchedulesData();
                    alert('删除成功');
                } else {
                    alert(`删除失败: ${response.data.message}`);
                }
            })
            .catch(function(error) {
                console.error('删除定时任务失败:', error);
                alert('删除失败，请重试');
            });
    }
    
    function padZero(num) {
        return num < 10 ? '0' + num : num;
    }
});