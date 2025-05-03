/**
 * 特权登录嵌入页面脚本
 */
document.addEventListener('DOMContentLoaded', function() {
    // 获取URL参数中的用户ID
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');
    
    if (!userId) {
        document.getElementById('loading').innerHTML = '<div class="notice">错误：缺少用户ID参数</div>';
        return;
    }
    
    // 从localStorage获取用户信息
    let userInfo = null;
    try {
        const savedInfo = localStorage.getItem('selectedUserInfo');
        if (savedInfo) {
            userInfo = JSON.parse(savedInfo);
            console.log('从localStorage读取的用户信息:', userInfo);
        }
    } catch (e) {
        console.error('解析保存的用户信息失败', e);
    }
    
    // 准备发送到后端的数据
    const postData = {
        user_id: userId,
        userName: userInfo ? userInfo.userName : null,
        departmentId: userInfo ? userInfo.departmentId : null,
        departmentName: userInfo ? userInfo.departmentName : null,
        position: userInfo ? userInfo.position : null
    };
    
    // 发送POST请求获取用户数据
    axios.post('/admin/user/embed', postData)
    .then(function(response) {
        if (response.data.success) {
            // 渲染用户信息
            renderUserContent(response.data);
            
            // 隐藏加载提示
            document.getElementById('loading').style.display = 'none';
            document.getElementById('user-content').style.display = 'block';
        } else {
            document.getElementById('loading').innerHTML = 
                `<div class="notice">加载失败: ${response.data.message || '未知错误'}</div>`;
        }
    })
    .catch(function(error) {
        document.getElementById('loading').innerHTML = 
            `<div class="notice">请求失败: ${error.message}</div>`;
    });
    
    // 定时更新时间
    updateTime();
    setInterval(updateTime, 1000);
});

/**
 * 更新当前时间显示
 */
function updateTime() {
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        const now = new Date();
        const timeString = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        timeElement.textContent = timeString;
    }
}

/**
 * 渲染用户内容
 * @param {Object} data - 从服务器获取的用户数据
 */
function renderUserContent(data) {
    // 渲染用户基本信息
    const userInfo = data.user_info || {};
    
    // 从user_info获取字段，注意可能存在不同的字段名
    const userId = userInfo.user_id || userInfo.userId || "";
    const userName = userInfo.username || userInfo.userName || "未知用户";
    const departmentId = userInfo.department_id || userInfo.departmentId || "";
    const departmentName = userInfo.department_name || userInfo.departmentName || "未知部门";
    const position = userInfo.position || "职位未知";
    
    document.title = `用户信息 - ${userName}`; // 设置页面标题
    
    // 用户信息卡片
    let userInfoHTML = `
        <div class="user-card" data-user-id="${userId}" data-department-id="${departmentId}">
            <div>
                <span class="user-name">${userName}</span>
                <span class="user-position">${position}</span>
            </div>
            <div class="user-department">${departmentName} (${departmentId}/${userId})</div>
        </div>`;
    
    // 考勤记录
    let attendanceHTML = `<div class="attendance-card">
        <div class="attendance-header">
            <div class="attendance-title">今日考勤</div>
            <div class="current-date">${formatDate(new Date())}</div>
        </div>`;
    
    // 根据数据添加考勤信息
    if (!data.is_workday) {
        attendanceHTML += `<div class="notice" style="color:#333; background-color:#f8f9fa;">温馨提示：今天是休息日，无需打卡。祝您休息愉快！</div>`;
    } else if (data.attendance_data) {
        // 上班打卡记录
        if (data.attendance_data.clockInRecord) {
            attendanceHTML += `
                <div class="record-item">
                    <div class="record-title">上班 (09:00)</div>
                    <div class="record-time">
                        <svg class="record-icon" viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z"></path></svg>
                        ${data.attendance_data.clockInRecord.clockTime}
                    </div>
                    <div class="record-location">
                        <svg class="record-icon" viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12,11.5A2.5,2.5 0 0,1 9.5,9A2.5,2.5 0 0,1 12,6.5A2.5,2.5 0 0,1 14.5,9A2.5,2.5 0 0,1 12,11.5M12,2A7,7 0 0,0 5,9C5,14.25 12,22 12,22C12,22 19,14.25 19,9A7,7 0 0,0 12,2Z"></path></svg>
                        ${data.attendance_data.clockInRecord.location}
                    </div>
                </div>`;
        }
        
        // 下班打卡记录
        if (data.attendance_data.clockOutRecord) {
            attendanceHTML += `
                <div class="record-item">
                    <div class="record-title">下班 (17:00)</div>
                    <div class="record-time">
                        <svg class="record-icon" viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z"></path></svg>
                        ${data.attendance_data.clockOutRecord.clockTime}
                    </div>
                    <div class="record-location">
                        <svg class="record-icon" viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12,11.5A2.5,2.5 0 0,1 9.5,9A2.5,2.5 0 0,1 12,6.5A2.5,2.5 0 0,1 14.5,9A2.5,2.5 0 0,1 12,11.5M12,2A7,7 0 0,0 5,9C5,14.25 12,22 12,22C12,22 19,14.25 19,9A7,7 0 0,0 12,2Z"></path></svg>
                        ${data.attendance_data.clockOutRecord.location}
                    </div>
                </div>`;
        }
        
        // 签到按钮
        if (data.show_sign_button.show) {
            const buttonText = data.show_sign_button.message || "打卡";
            attendanceHTML += `
                <div class="sign-button-container">
                    <button id="sign-btn" class="sign-button" data-admin-view="true" data-user-id="${userId}" data-department-id="${departmentId}" data-user-name="${userName}" data-button-text="${buttonText}">
                        <span>${buttonText}</span>
                        <div class="sign-time" id="currentTime"></div>
                    </button>
                </div>`;
        } else if (data.show_sign_button.message) {
            attendanceHTML += `<div class="notice" style="color:#333; background-color:#f8f9fa;">${data.show_sign_button.message}</div>`;
        }
    } else {
        attendanceHTML += `
            <div class="notice" style="color:#333; background-color:#f8f9fa;">温馨提示：今天是工作日，请按时打卡。</div>
            ${data.show_sign_button.show ? `
                <div class="sign-button-container">
                    <button id="sign-btn" class="sign-button" data-admin-view="true" data-user-id="${userId}" data-department-id="${departmentId}" data-user-name="${userName}" data-button-text="${data.show_sign_button.message || '打卡'}">
                        <span>${data.show_sign_button.message || "打卡"}</span>
                        <div class="sign-time" id="currentTime"></div>
                    </button>
                </div>` : ''}`;
    }
    
    // 添加定时功能 - 下次打卡倒计时
    let nextClockTime = getNextClockTime(data);
    if (nextClockTime) {
        attendanceHTML += `
            <div class="next-clock-container">
                <div class="next-clock-label">距离${nextClockTime.type}打卡还有</div>
                <div class="next-clock-time" id="countdownTimer">${formatCountdown(nextClockTime.time)}</div>
            </div>`;
    }
    
    attendanceHTML += `</div>`;
    
    // 获取容器并渲染内容
    const container = document.getElementById('attendance-content');
    if (container) {
        container.innerHTML = `
            ${userInfoHTML}
            ${attendanceHTML}`;
    } else {
        console.error('找不到attendance-content容器');
    }
    
    // 添加签到按钮事件监听
    const signButton = document.getElementById('sign-btn');
    if (signButton) {
        console.log('找到签到按钮，添加事件监听器');
        signButton.addEventListener('click', function(event) {
            event.preventDefault(); // 阻止默认行为
            console.log('签到按钮被点击');
            
            const userId = this.getAttribute('data-user-id');
            const departmentId = this.getAttribute('data-department-id');
            const userName = this.getAttribute('data-user-name');
            const buttonText = this.getAttribute('data-button-text') || '';
            
            let signType = '上班打卡'; // 默认
            if (buttonText.includes('下班')) {
                signType = '下班打卡';
            }
            
            console.log(`执行签到操作: 用户ID=${userId}, 部门ID=${departmentId}, 用户名=${userName}, 类型=${signType}`);
            handleSignIn(userId, signType, this);
        });
    } else {
        console.log('未找到签到按钮，无法添加事件监听器');
    }
    
    // 更新当前时间和倒计时
    updateTime();
    if (nextClockTime) {
        setInterval(function() {
            updateCountdown(nextClockTime);
        }, 1000);
    }
}

/**
 * 格式化日期为 "YYYY年MM月DD日 星期几" 的格式
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(date) {
    const weekDays = ["日", "一", "二", "三", "四", "五", "六"];
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 星期${weekDays[date.getDay()]}`;
}

/**
 * 获取下一次打卡时间
 * @param {Object} data - 用户数据
 * @returns {Object|null} 下一次打卡信息，包含时间和类型
 */
function getNextClockTime(data) {
    if (!data.is_workday) return null;
    
    const now = new Date();
    const clockInTime = new Date();
    clockInTime.setHours(9, 0, 0, 0);
    
    const clockOutTime = new Date();
    clockOutTime.setHours(17, 0, 0, 0);
    
    // 检查是否有上班打卡记录
    const hasClockIn = data.attendance_data && data.attendance_data.clockInRecord;
    
    // 检查是否有下班打卡记录
    const hasClockOut = data.attendance_data && data.attendance_data.clockOutRecord;
    
    if (!hasClockIn && now < clockInTime) {
        return { time: clockInTime, type: "上班" };
    } else if (!hasClockOut && now < clockOutTime) {
        return { time: clockOutTime, type: "下班" };
    } else if (!hasClockOut && now >= clockOutTime) {
        return { time: clockOutTime, type: "下班" };
    }
    
    return null;
}

/**
 * 格式化倒计时
 * @param {Date} targetTime - 目标时间
 * @returns {string} 格式化后的倒计时字符串
 */
function formatCountdown(targetTime) {
    const now = new Date();
    let diff = Math.max(0, targetTime - now);
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    diff -= hours * 1000 * 60 * 60;
    
    const minutes = Math.floor(diff / (1000 * 60));
    diff -= minutes * 1000 * 60;
    
    const seconds = Math.floor(diff / 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * 更新倒计时
 * @param {Object} nextClockTime - 下一次打卡信息
 */
function updateCountdown(nextClockTime) {
    const countdownEl = document.getElementById('countdownTimer');
    if (countdownEl) {
        countdownEl.textContent = formatCountdown(nextClockTime.time);
    }
}

/**
 * 计算打卡记录状态
 * @returns {number} 打卡状态码 (0-3)
 */
function calculateSignStatus() {
    let signStatus = 0;
    const recordItems = document.querySelectorAll('.record-item');
    
    console.log(`找到 ${recordItems.length} 条打卡记录`);
    
    recordItems.forEach((item, index) => {
        const recordTitle = item.querySelector('.record-title').textContent;
        console.log(`记录 ${index + 1}: ${recordTitle}`);
        
        if (recordTitle.includes('上班')) {
            signStatus |= 1; // 设置第1位 (上午记录)
            console.log('上午打卡记录存在，设置状态位1');
        }
        if (recordTitle.includes('下班')) {
            signStatus |= 2; // 设置第2位 (下午记录)
            console.log('下午打卡记录存在，设置状态位2');
        }
    });
    
    console.log(`最终计算的打卡状态码: ${signStatus}`);
    return signStatus;
}

/**
 * 处理签到操作
 * @param {string} userId - 用户ID
 * @param {string} signType - 签到类型
 * @param {HTMLElement} button - 签到按钮元素
 */
function handleSignIn(userId, signType, button) {
    // 禁用按钮防止重复点击
    button.disabled = true;
    const originalHtml = button.innerHTML;
    button.innerHTML = `<span>处理中...</span><div class="sign-time" id="currentTime"></div>`;
    updateTime();
    
    // 计算打卡记录状态
    const signStatus = calculateSignStatus();
    
    // 获取用户ID和部门ID
    const departmentIdEl = document.getElementById('depId');
    let departmentId = '';
    if (departmentIdEl) {
        departmentId = departmentIdEl.textContent;
    }
    
    // 如果未能从记录中获取部门ID，则尝试从用户卡片获取
    if (!departmentId) {
        const userCard = document.querySelector('.user-card');
        if (userCard) {
            departmentId = userCard.getAttribute('data-department-id');
        }
    }
    
    // 获取用户名
    let userName = '';
    const userNameEl = document.querySelector('.user-name');
    if (userNameEl) {
        userName = userNameEl.textContent.trim();
    }
    
    // 准备签到请求数据
    const signData = {
        user_id: userId,
        sign_type: signType,
        sign_status: signStatus,
        department_id: departmentId,
        user_name: userName, // 添加用户名参数
        userName: userName    // 同时添加userName字段，确保兼容性
    };
    
    console.log('发送签到请求:', signData);
    
    // 发送签到请求
    axios.post('/admin/user/embed/sign', signData)
    .then(function(response) {
        if (response.data.success) {
            showToast('签到成功: ' + response.data.message, 'success');
            // 刷新页面
            setTimeout(function() {
                window.location.reload();
            }, 1500);
        } else {
            showToast('签到失败: ' + response.data.message, 'error');
            // 恢复按钮状态
            button.innerHTML = originalHtml;
            updateTime();
            button.disabled = false;
        }
    })
    .catch(function(error) {
        showToast('签到请求失败: ' + (error.response ? error.response.data.message : error.message), 'error');
        button.innerHTML = originalHtml;
        updateTime();
        button.disabled = false;
    });
}

/**
 * 显示提示消息
 * @param {string} message - 提示消息
 * @param {string} type - 提示类型 (success/error)
 */
function showToast(message, type) {
    // 检查是否已存在Toast元素
    let toast = document.getElementById('toast');
    
    if (!toast) {
        // 创建Toast元素
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(20px)';
        document.body.appendChild(toast);
    }
    
    // 设置样式和内容
    if (type === 'success') {
        toast.style.backgroundColor = '#4caf50';
        toast.style.color = 'white';
    } else {
        toast.style.backgroundColor = '#f44336';
        toast.style.color = 'white';
    }
    
    toast.textContent = message;
    
    // 显示Toast
    setTimeout(function() {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
    }, 10);
    
    // 3秒后自动隐藏
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(20px)';
    }, 3000);
} 