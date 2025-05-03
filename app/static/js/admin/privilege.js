document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const departmentSelect = document.getElementById('department-select');
    const userSelect = document.getElementById('user-select');
    const queryButton = document.getElementById('query-button');
    const userInfoPanel = document.getElementById('user-info-panel');
    const messagePanel = document.getElementById('message-panel');
    const messageContent = document.getElementById('message-content');
    const userIframeContainer = document.getElementById('user-iframe-container');
    const userIframe = document.getElementById('user-iframe');
    
    // 签到相关DOM元素
    const morningSignStatus = document.getElementById('morning-sign-status');
    const morningSignTime = document.getElementById('morning-sign-time');
    const morningSignButton = document.getElementById('morning-sign-button');
    const afternoonSignStatus = document.getElementById('afternoon-sign-status');
    const afternoonSignTime = document.getElementById('afternoon-sign-time');
    const afternoonSignButton = document.getElementById('afternoon-sign-button');
    const signRecordsList = document.getElementById('sign-records-list');
    
    // 全局变量
    let selectedUserId = '';
    let selectedDepartmentId = '';
    let signSettings = null;
    let currentUserInfo = null;
    
    // 初始化 - 加载部门数据
    loadDepartments();
    
    // 部门选择变化事件
    departmentSelect.addEventListener('change', function() {
        const departmentId = this.value;
        selectedDepartmentId = departmentId;
        
        if (departmentId) {
            loadUsers(departmentId);
            userSelect.disabled = false;
        } else {
            userSelect.innerHTML = '<option value="">-- 请先选择部门 --</option>';
            userSelect.disabled = true;
            queryButton.disabled = true;
        }
    });
    
    // 用户选择变化事件
    userSelect.addEventListener('change', function() {
        const userId = this.value;
        selectedUserId = userId;
        
        if (userId) {
            queryButton.disabled = false;
        } else {
            queryButton.disabled = true;
        }
    });
    
    // 查询按钮点击事件
    queryButton.addEventListener('click', function() {
        if (selectedUserId) {
            // 在iframe中加载用户视图页面
            const iframeSrc = `/admin/user/embed?user_id=${selectedUserId}`;
            userIframe.src = iframeSrc;
            userIframeContainer.style.display = 'block';
            
            // 隐藏其他面板
            if (userInfoPanel) {
                userInfoPanel.style.display = 'none';
            }
            
            // 记录当前选中的用户信息
            const selectedUserName = userSelect.options[userSelect.selectedIndex].text;
            const selectedDeptName = departmentSelect.options[departmentSelect.selectedIndex].text;
            
            // 保存用户信息以备后续使用
            localStorage.setItem('selectedUserInfo', JSON.stringify({
                userId: selectedUserId,
                userName: selectedUserName,
                departmentId: selectedDepartmentId,
                departmentName: selectedDeptName,
                position: '' // 职位信息可能无法从下拉框获取，但为保持统一的数据结构
            }));
        }
    });
    
    // 上班打卡按钮点击事件
    morningSignButton.addEventListener('click', function() {
        if (selectedUserId) {
            signIn(selectedUserId, '上班打卡');
        }
    });
    
    // 下班打卡按钮点击事件
    afternoonSignButton.addEventListener('click', function() {
        if (selectedUserId) {
            signIn(selectedUserId, '下班打卡');
        }
    });
    
    // 加载部门数据
    function loadDepartments() {
        axios.post('/admin/departments')
            .then(function(response) {
                if (response.data.success) {
                    renderDepartments(response.data.departments);
                } else {
                    showMessage(response.data.message || '获取部门数据失败', true);
                }
            })
            .catch(function(error) {
                showMessage('获取部门数据失败: ' + error.message, true);
            });
    }
    
    // 渲染部门下拉框
    function renderDepartments(departments) {
        // 保留第一个默认选项
        departmentSelect.innerHTML = '<option value="">-- 请选择部门 --</option>';
        
        departments.forEach(function(dept) {
            const option = document.createElement('option');
            option.value = dept.department_id;
            option.textContent = dept.department_name;
            departmentSelect.appendChild(option);
        });
    }
    
    // 加载部门下的用户
    function loadUsers(departmentId) {
        axios.post('/admin/users', {
            department_id: departmentId
        })
            .then(function(response) {
                if (response.data.success) {
                    renderUsers(response.data.users);
                } else {
                    showMessage(response.data.message || '获取用户数据失败', true);
                }
            })
            .catch(function(error) {
                showMessage('获取用户数据失败: ' + error.message, true);
            });
    }
    
    // 渲染用户下拉框
    function renderUsers(users) {
        // 保留第一个默认选项
        userSelect.innerHTML = '<option value="">-- 请选择用户 --</option>';
        
        users.forEach(function(user) {
            const option = document.createElement('option');
            option.value = user.userid;
            option.textContent = user.username;
            userSelect.appendChild(option);
        });
    }
    
    // 加载用户详细信息
    function loadUserInfo(userId) {
        axios.post('/admin/user/info', {
            user_id: userId
        })
            .then(function(response) {
                if (response.data.success) {
                    currentUserInfo = response.data.user;
                    renderUserInfo(response.data.user);
                    loadUserSignStatus(userId);
                    loadTodaySignRecords(userId);
                    // 获取签到设置
                    loadSignSettings();
                    userInfoPanel.style.display = 'block';
                } else {
                    showMessage(response.data.message || '获取用户信息失败', true);
                    userInfoPanel.style.display = 'none';
                }
            })
            .catch(function(error) {
                showMessage('获取用户信息失败: ' + error.message, true);
                userInfoPanel.style.display = 'none';
            });
    }
    
    // 渲染用户信息
    function renderUserInfo(user) {
        document.getElementById('display-username').textContent = user.username;
        document.getElementById('display-department').querySelector('span').textContent = user.department_name || '未知部门';
        document.getElementById('display-position').querySelector('span').textContent = user.position || '未设置';
        
        const statusBadge = document.getElementById('display-status').querySelector('.status-badge');
        // 根据最后活跃时间判断状态（30分钟内活跃视为在线）
        const isOnline = user.last_activity && 
                         (Date.now() / 1000 - user.last_activity) < 1800;
        
        statusBadge.textContent = isOnline ? '在线' : '离线';
        statusBadge.className = 'status-badge ' + (isOnline ? 'online' : 'offline');
    }
    
    // 加载签到设置
    function loadSignSettings() {
        axios.post('/admin/sign/settings')
            .then(function(response) {
                if (response.data.success) {
                    signSettings = response.data.settings;
                    updateSignButtons();
                }
            })
            .catch(function(error) {
                console.error('获取签到设置失败:', error);
            });
    }
    
    // 加载用户签到状态
    function loadUserSignStatus(userId) {
        axios.post('/admin/user/sign/status', {
            user_id: userId
        })
            .then(function(response) {
                if (response.data.success) {
                    renderSignStatus(response.data);
                    updateSignButtons();
                } else {
                    showMessage('获取签到状态失败: ' + response.data.message, true);
                }
            })
            .catch(function(error) {
                showMessage('获取签到状态失败: ' + error.message, true);
            });
    }
    
    // 渲染签到状态
    function renderSignStatus(data) {
        // 上班打卡状态
        if (data.morning_signed) {
            morningSignStatus.textContent = '已打卡';
            morningSignStatus.className = 'sign-status success';
            morningSignTime.textContent = data.morning_time || '--:--:--';
        } else {
            morningSignStatus.textContent = '未打卡';
            morningSignStatus.className = 'sign-status pending';
            morningSignTime.textContent = '--:--:--';
        }
        
        // 下班打卡状态
        if (data.afternoon_signed) {
            afternoonSignStatus.textContent = '已打卡';
            afternoonSignStatus.className = 'sign-status success';
            afternoonSignTime.textContent = data.afternoon_time || '--:--:--';
        } else {
            afternoonSignStatus.textContent = '未打卡';
            afternoonSignStatus.className = 'sign-status pending';
            afternoonSignTime.textContent = '--:--:--';
        }
    }
    
    // 更新签到按钮状态
    function updateSignButtons() {
        if (!signSettings || !currentUserInfo) return;
        
        // 检查是否应该显示上班打卡按钮
        const shouldShowMorningButton = checkShouldShowSignButton('上班打卡');
        morningSignButton.disabled = !shouldShowMorningButton;
        
        // 检查是否应该显示下班打卡按钮
        const shouldShowAfternoonButton = checkShouldShowSignButton('下班打卡');
        afternoonSignButton.disabled = !shouldShowAfternoonButton;
    }
    
    // 检查是否应该显示签到按钮
    function checkShouldShowSignButton(signType) {
        if (!signSettings || !currentUserInfo) return false;
        
        const now = new Date();
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();
        const currentTime = currentHour * 60 + currentMinute; // 转换为分钟计数
        
        if (signType === '上班打卡') {
            const morningStartHour = parseInt(signSettings.morning_start_hour);
            const morningStartMinute = parseInt(signSettings.morning_start_minute);
            const morningEndHour = parseInt(signSettings.morning_end_hour);
            const morningEndMinute = parseInt(signSettings.morning_end_minute);
            
            const morningStartTime = morningStartHour * 60 + morningStartMinute;
            const morningEndTime = morningEndHour * 60 + morningEndMinute;
            
            // 在上班打卡时间范围内，且未打卡
            return currentTime >= morningStartTime && currentTime <= morningEndTime && 
                   morningSignStatus.textContent === '未打卡';
        } else if (signType === '下班打卡') {
            const afternoonStartHour = parseInt(signSettings.afternoon_start_hour);
            const afternoonStartMinute = parseInt(signSettings.afternoon_start_minute);
            const afternoonEndHour = parseInt(signSettings.afternoon_end_hour);
            const afternoonEndMinute = parseInt(signSettings.afternoon_end_minute);
            
            const afternoonStartTime = afternoonStartHour * 60 + afternoonStartMinute;
            const afternoonEndTime = afternoonEndHour * 60 + afternoonEndMinute;
            
            // 在下班打卡时间范围内，且未打卡
            return currentTime >= afternoonStartTime && currentTime <= afternoonEndTime && 
                   afternoonSignStatus.textContent === '未打卡';
        }
        
        return false;
    }
    
    // 签到操作
    function signIn(userId, signType) {
        axios.post('/admin/user/sign', {
            user_id: userId,
            sign_type: signType
        })
            .then(function(response) {
                if (response.data.success) {
                    showMessage(`${signType}成功: ${response.data.sign_time}`, false);
                    
                    // 更新签到状态
                    if (signType === '上班打卡') {
                        morningSignStatus.textContent = '已打卡';
                        morningSignStatus.className = 'sign-status success';
                        morningSignTime.textContent = response.data.sign_time;
                        morningSignButton.disabled = true;
                    } else if (signType === '下班打卡') {
                        afternoonSignStatus.textContent = '已打卡';
                        afternoonSignStatus.className = 'sign-status success';
                        afternoonSignTime.textContent = response.data.sign_time;
                        afternoonSignButton.disabled = true;
                    }
                    
                    // 重新加载打卡记录
                    loadTodaySignRecords(userId);
                } else {
                    showMessage(response.data.message || `${signType}失败`, true);
                }
            })
            .catch(function(error) {
                showMessage(`${signType}失败: ` + error.message, true);
            });
    }
    
    // 加载今日打卡记录
    function loadTodaySignRecords(userId) {
        axios.post('/admin/user/sign/records', {
            user_id: userId
        })
            .then(function(response) {
                if (response.data.success) {
                    renderSignRecords(response.data.records);
                } else {
                    console.error('获取打卡记录失败:', response.data.message);
                }
            })
            .catch(function(error) {
                console.error('获取打卡记录失败:', error);
            });
    }
    
    // 渲染签到记录
    function renderSignRecords(records) {
        if (!records || records.length === 0) {
            signRecordsList.innerHTML = '<div class="empty-records">暂无打卡记录</div>';
            return;
        }
        
        signRecordsList.innerHTML = '';
        
        records.forEach(function(record) {
            const recordItem = document.createElement('div');
            recordItem.className = 'record-item';
            
            const typeSpan = document.createElement('span');
            typeSpan.className = 'record-type';
            typeSpan.textContent = record.sign_type;
            
            const timeSpan = document.createElement('span');
            timeSpan.className = 'record-time';
            timeSpan.textContent = record.sign_time;
            
            const locationSpan = document.createElement('span');
            locationSpan.className = 'record-location';
            locationSpan.textContent = record.location || '未知位置';
            
            recordItem.appendChild(typeSpan);
            recordItem.appendChild(timeSpan);
            recordItem.appendChild(locationSpan);
            
            signRecordsList.appendChild(recordItem);
        });
    }
    
    // 显示消息
    function showMessage(message, isError) {
        messageContent.textContent = message;
        messagePanel.className = 'message-panel ' + (isError ? 'error' : 'success');
        messagePanel.style.display = 'block';
        
        // 5秒后自动隐藏消息
        setTimeout(function() {
            messagePanel.style.display = 'none';
        }, 5000);
    }
}); 