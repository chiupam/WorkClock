// 用户信息页面的交互逻辑
document.addEventListener('DOMContentLoaded', function () {
    // 初始化时间显示
    updateTime();
    // 设置时间更新间隔
    setInterval(updateTime, 1000);

    // 登出按钮事件
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            document.getElementById('logout-form').submit();
        });
    }

    // 考勤统计按钮点击事件
    const statsBtn = document.getElementById('stats-btn');
    if (statsBtn) {
        statsBtn.addEventListener('click', function () {
            // 设置月份选择器为当前月份
            const monthSelect = document.getElementById('monthSelect');
            const currentMonth = new Date().getMonth() + 1; // 月份从0开始，所以+1
            monthSelect.value = currentMonth;

            showAttendanceStats();
        });
    }

    // 添加定时按钮点击事件
    const scheduleBtn = document.getElementById('schedule-btn');
    if (scheduleBtn) {
        scheduleBtn.addEventListener('click', function () {
            showScheduleModal();
        });
    }

    // 签到按钮事件
    const signBtn = document.getElementById('sign-btn');
    if (signBtn) {
        signBtn.addEventListener('click', function () {
            signIn();
        });
    }
});

// 更新时间显示
function updateTime() {
    const timeElement = document.getElementById('currentTime');
    if (!timeElement) return;

    const now = new Date();
    const timeString = now.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    timeElement.textContent = timeString;

    // 根据当前时间更新打卡按钮文本
    updateSignButtonText();
}

// 更新打卡按钮文本
function updateSignButtonText() {
    const signButton = document.getElementById('sign-btn');
    if (!signButton) return;

    const textSpan = signButton.querySelector('span:not(.time)');
    if (!textSpan) return;

    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    const attType = currentTime >= 17 * 60 ? '下班' : '上班';

    textSpan.textContent = `${attType}打卡`;
}

// 显示考勤统计
async function showAttendanceStats() {
    const attendanceList = document.querySelector('.attendance-list');
    const attendanceStats = document.querySelector('.attendance-stats');
    const signButton = document.querySelector('.sign-button');

    // 显示加载中
    document.getElementById('loading-spinner').style.display = 'flex';

    try {
        // 获取当前选择的月份，如果没有选择，则使用当前月份
        const monthSelect = document.getElementById('monthSelect');
        if (!monthSelect.value) {
            const currentMonth = new Date().getMonth() + 1; // 月份从0开始，所以+1
            monthSelect.value = currentMonth;
        }
        const selectedMonth = monthSelect.value;
        const selectedYear = new Date().getFullYear();

        // 调用统计API
        const response = await axios.post('/stats/monthly', {
            month: parseInt(selectedMonth),
            year: selectedYear
        });

        const data = response.data;

        if (data.success) {
            // 更新统计摘要
            const statistics = data.statistics;
            document.getElementById('leaveDays').textContent = statistics.LeaveDays || 0;
            document.getElementById('lateNumber').textContent = statistics.LateNumber || 0;
            document.getElementById('ztNumber').textContent = statistics.ZtNumber || 0;
            document.getElementById('lackCarNumber').textContent = statistics.LackCarNumber || 0;

            // 生成日历
            generateCalendar(data.details, data.month, data.year, data.days);

            // 切换显示
            attendanceList.style.display = 'none';
            attendanceStats.style.display = 'block';
            if (signButton) signButton.style.display = 'none';
        } else {
            showAlert('获取失败', '无法获取考勤统计数据', 'error');
        }
    } catch (error) {
        console.error('获取考勤统计出错:', error);
        showAlert('获取失败', '获取考勤统计数据失败', 'error');
    } finally {
        // 隐藏加载中
        document.getElementById('loading-spinner').style.display = 'none';
    }
}

// 生成日历表格
function generateCalendar(details, month, year, daysInMonth) {
    const tbody = document.getElementById('statsTableBody');
    const today = new Date();
    const currentMonth = today.getMonth() + 1;
    const currentDay = today.getDate();

    // 获取选中月份的第一天是星期几（0-6，0代表星期日）
    const firstDay = new Date(year, month - 1, 1).getDay();

    // SVG图标定义（保留原始颜色，但减小大小）
    const checkSvgGreen = `<span style="color: #52c41a; font-size: 12px;">✓</span>`;
    const checkSvgYellow = `<span style="color: #faad14; font-size: 12px;">✓</span>`;
    const crossSvgRed = `<span style="color: #ff4d4f; font-size: 12px;">✕</span>`;

    let html = '';
    let dayCounter = 1;

    // 生成日历表格
    for (let week = 0; dayCounter <= daysInMonth; week++) {
        html += '<tr>';

        for (let weekday = 0; weekday < 7; weekday++) {
            if (week === 0 && weekday < firstDay) {
                html += '<td></td>';
            } else if (dayCounter > daysInMonth) {
                html += '<td></td>';
            } else {
                // 判断是否有当天的考勤记录
                const day = details && details[dayCounter - 1];

                // 所有日期都使用相同的基本结构，确保高度一致
                let dayContent = `<div class="calendar-day"><div class="day-number">${dayCounter}</div>`;

                // 判断是否是未来日期
                const selectedDate = new Date(year, month - 1, dayCounter);
                const isInFuture = selectedDate > today;

                if (!isInFuture && day) {
                    // 处理节假日（特殊显示）
                    if (day.isholiday === 1 && day.jjr) {
                        let holidayName = day.jjr;
                        if (holidayName.length >= 3) {
                            holidayName = holidayName.substring(0, 2);
                        }
                        // 将节假日名称字符垂直排列
                        let verticalText = '';
                        for (let i = 0; i < holidayName.length; i++) {
                            verticalText += `<div class="vertical-char">${holidayName[i]}</div>`;
                        }
                        dayContent += `<div class="rest-day vertical-text">${verticalText}</div>`;
                    }
                    // 处理请假
                    else if (day.IsQj === 1) {
                        dayContent += `<div class="leave-day vertical-text"><div class="vertical-char">请</div><div class="vertical-char">假</div></div>`;
                    }
                    // 处理休息日
                    else if (day.isholiday === 1) {
                        dayContent += `<div class="rest-day vertical-text"><div class="vertical-char">休</div><div class="vertical-char">息</div></div>`;
                    }
                    // 处理正常工作日
                    else {
                        const morningStatus = getMorningStatus(day);
                        const afternoonStatus = getAfternoonStatus(day);

                        // 如果上下午都缺卡
                        if (morningStatus === 'missing' && afternoonStatus === 'missing') {
                            dayContent += `<div class="absent-day vertical-text"><div class="vertical-char">缺</div><div class="vertical-char">卡</div></div>`;
                        }
                        // 如果上下午状态不同
                        else {
                            dayContent += `<div class="status-icons">`;
                            // 添加上午状态
                            if (morningStatus === 'normal') {
                                dayContent += checkSvgGreen;
                            } else if (morningStatus === 'makeup') {
                                dayContent += checkSvgYellow;
                            } else if (morningStatus === 'missing') {
                                dayContent += crossSvgRed;
                            }

                            // 添加下午状态
                            if (afternoonStatus === 'normal') {
                                dayContent += checkSvgGreen;
                            } else if (afternoonStatus === 'makeup') {
                                dayContent += checkSvgYellow;
                            } else if (afternoonStatus === 'missing') {
                                dayContent += crossSvgRed;
                            }
                            dayContent += `</div>`;
                        }
                    }
                } else {
                    // 未来日期添加占位符，确保与有内容的日期高度一致
                    dayContent += `<div class="future-placeholder"></div>`;
                }

                dayContent += '</div>';
                html += `<td>${dayContent}</td>`;
                dayCounter++;
            }
        }

        html += '</tr>';
    }

    tbody.innerHTML = html;
}

// 获取上午打卡状态
function getMorningStatus(dayRecord) {
    if (!dayRecord) return 'missing';

    // 上午打卡次数
    const morningClockCount = dayRecord.SWSBDKCS || 0;
    // 上午是否补卡
    const isMorningMakeup = dayRecord.IsSwSbbuka === 1;

    if (morningClockCount === 0) {
        return 'missing';  // 缺卡
    } else if (isMorningMakeup) {
        return 'makeup';   // 补卡
    } else {
        return 'normal';   // 正常打卡
    }
}

// 获取下午打卡状态
function getAfternoonStatus(dayRecord) {
    if (!dayRecord) return 'missing';

    // 下午打卡次数
    const afternoonClockCount = dayRecord.XWXBDKCS || 0;
    // 下午是否补卡
    const isAfternoonMakeup = dayRecord.IsXwXbbuka === 1;

    if (afternoonClockCount === 0) {
        return 'missing';  // 缺卡
    } else if (isAfternoonMakeup) {
        return 'makeup';   // 补卡
    } else {
        return 'normal';   // 正常打卡
    }
}

// 显示定时打卡模态框
function showScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (modal) {
        // 清空之前的时间框
        document.getElementById('morningTimeGrid').innerHTML = '<div class="loading-box">加载中...</div>';
        document.getElementById('afternoonTimeGrid').innerHTML = '<div class="loading-box">加载中...</div>';

        // 显示模态框
        modal.style.display = 'block';

        // 加载用户定时设置状态并显示
        loadUserSchedule();
    }
}

// 初始化时间框点击事件
function initTimeBoxes() {
    const timeBoxes = document.querySelectorAll('.time-box');

    timeBoxes.forEach(box => {
        // 移除已有的点击事件（避免重复绑定）
        box.removeEventListener('click', toggleTimeBoxSelection);
        // 添加点击事件
        box.addEventListener('click', toggleTimeBoxSelection);
    });
}

// 时间框点击事件处理函数
function toggleTimeBoxSelection() {
    this.classList.toggle('selected');
}

// 动态生成时间框
function generateTimeBoxes(times, period, containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }

    container.innerHTML = ''; // 清空容器

    // 如果没有时间选项，显示提示信息
    if (!times || !times.length) {
        container.innerHTML = '<div class="no-times-message">无可用时间选项</div>';
        return;
    }

    times.forEach((time, index) => {
        // 创建时间框
        const timeBox = document.createElement('div');
        timeBox.className = 'time-box';
        timeBox.setAttribute('data-time', time);
        timeBox.setAttribute('data-period', period);
        timeBox.setAttribute('data-index', index);

        // 添加时间文本
        const timeSpan = document.createElement('span');
        timeSpan.textContent = time;

        // 组装DOM
        timeBox.appendChild(timeSpan);
        container.appendChild(timeBox);

        // 添加点击事件
        timeBox.addEventListener('click', toggleTimeBoxSelection);
    });
}

// 加载用户定时设置
async function loadUserSchedule() {
    try {
        // 显示加载中
        document.getElementById('loading-spinner').style.display = 'flex';

        // 从服务器获取用户ID
        const userId = getUserId();

        if (!userId) {
            showAlert('错误', '无法获取用户ID', 'error');
            return;
        }

        // 从服务器获取定时状态
        const response = await axios.get(`/schedules/tasks`);
        const data = response.data;

        // 动态生成时间框
        if (data.morning_times && data.morning_times.length > 0) {
            generateTimeBoxes(data.morning_times, 'morning', 'morningTimeGrid');
        } else {
            document.getElementById('morningTimeGrid').innerHTML = '<div class="no-times-message">无可用时间选项</div>';
        }

        if (data.afternoon_times && data.afternoon_times.length > 0) {
            generateTimeBoxes(data.afternoon_times, 'afternoon', 'afternoonTimeGrid');
        } else {
            document.getElementById('afternoonTimeGrid').innerHTML = '<div class="no-times-message">无可用时间选项</div>';
        }

        // 清除所有现有的选中状态
        document.querySelectorAll('.time-box').forEach(box => {
            box.classList.remove('selected');
        });

        // 设置时间框选中状态
        setTimeout(() => {
            // 根据用户的选择状态标记时间框
            if (data.morning_selections && data.morning_selections.length > 0) {
                const morningTimeBoxes = document.querySelectorAll('.time-box[data-period="morning"]');

                data.morning_selections.forEach((selected, index) => {
                    if (selected === 1 && index < morningTimeBoxes.length) {
                        morningTimeBoxes[index].classList.add('selected');
                    }
                });
            }

            if (data.afternoon_selections && data.afternoon_selections.length > 0) {
                const afternoonTimeBoxes = document.querySelectorAll('.time-box[data-period="afternoon"]');

                data.afternoon_selections.forEach((selected, index) => {
                    if (selected === 1 && index < afternoonTimeBoxes.length) {
                        afternoonTimeBoxes[index].classList.add('selected');
                    }
                });
            }
        }, 100); // 短暂延迟确保DOM已更新
    } catch (error) {
        showAlert('获取失败', '无法获取定时打卡设置', 'error');

        // 在错误情况下显示提示信息
        document.getElementById('morningTimeGrid').innerHTML = '<div class="no-times-message">获取时间选项失败</div>';
        document.getElementById('afternoonTimeGrid').innerHTML = '<div class="no-times-message">获取时间选项失败</div>';
    } finally {
        // 隐藏加载中
        document.getElementById('loading-spinner').style.display = 'none';
    }
}

// 保存定时打卡设置
async function saveSchedule() {
    try {
        // 显示加载中
        document.getElementById('loading-spinner').style.display = 'flex';

        // 初始化选择状态数组（默认全部为0）
        const morningSelections = [0, 0, 0];
        const afternoonSelections = [0, 0, 0];

        // 获取上午时间框
        const morningTimeBoxes = document.querySelectorAll('.time-box[data-period="morning"]');
        // 获取下午时间框
        const afternoonTimeBoxes = document.querySelectorAll('.time-box[data-period="afternoon"]');

        // 根据选中状态设置对应的值
        morningTimeBoxes.forEach((box, index) => {
            if (index < 3 && box.classList.contains('selected')) {
                morningSelections[index] = 1;
            }
        });

        afternoonTimeBoxes.forEach((box, index) => {
            if (index < 3 && box.classList.contains('selected')) {
                afternoonSelections[index] = 1;
            }
        });

        const hasMorning = morningSelections.includes(1);
        const hasAfternoon = afternoonSelections.includes(1);

        // 获取用户ID
        const userId = getUserId();

        if (!userId) {
            showAlert('错误', '无法获取用户ID', 'error');
            return;
        }

        // 保存设置到服务器
        const response = await axios.post(`/schedules/tasks`, {
            morning: hasMorning,
            afternoon: hasAfternoon,
            morning_times: morningSelections,
            afternoon_times: afternoonSelections
        });

        // 重新加载用户定时设置
        await loadUserSchedule();

        // 显示成功消息
        showAlert('设置已保存', "定时设置已成功保存", 'success');

        // 短暂延迟后关闭模态框
        setTimeout(() => {
            closeScheduleModal();
        }, 1000);
    } catch (error) {
        let errorMsg = '保存定时打卡设置失败';

        if (error.response && error.response.data) {
            errorMsg = error.response.data.message || errorMsg;
        }

        showAlert('保存失败', errorMsg, 'error');
    } finally {
        // 隐藏加载中
        document.getElementById('loading-spinner').style.display = 'none';
    }
}

// 获取用户ID
function getUserId() {
    // 从页面元素中获取用户ID
    const userIdElement = document.getElementById('userId');
    if (userIdElement) {
        return userIdElement.textContent.trim();
    }
    return null;
}

// 签到功能
function signIn() {
    // 显示加载中
    document.getElementById('loading-spinner').style.display = 'flex';

    // 获取当前打卡状态
    const attendanceData = getAttendanceStatus();

    // 使用axios发送打卡请求到后端
    axios.post('/sign', { attendance: attendanceData })
        .then(response => {
            // 隐藏加载器
            document.getElementById('loading-spinner').style.display = 'none';

            const data = response.data;

            if (data.success) {
                showAlert(data.clockType, data.message, data.success ? 'success' : 'error');

                // 刷新页面显示最新打卡信息
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showAlert(data.clockType, data.message || '打卡请求失败，请稍后再试。', 'error');
            }
        })
        .catch(error => {
            // 隐藏加载器
            document.getElementById('loading-spinner').style.display = 'none';
            console.error('打卡请求出错:', error);

            // 获取错误信息
            const errorMsg = error.response ? error.response.data.message : '网络错误，请稍后再试';
            showAlert('打卡失败', errorMsg, 'error');
        });
}

// 获取当前打卡状态
function getAttendanceStatus() {
    // 检查页面上的打卡记录元素
    const attendanceData = document.getElementById('attendanceData');

    // 获取上午和下午打卡记录
    const hasMorningRecord = attendanceData.querySelector('.attendance-record:nth-child(1)') !== null;
    const hasAfternoonRecord = attendanceData.querySelector('.attendance-record:nth-child(2)') !== null;

    // 根据记录情况返回状态码
    if (!hasMorningRecord && !hasAfternoonRecord) {
        return 0; // 不存在任何打卡记录
    } else if (hasMorningRecord && !hasAfternoonRecord) {
        return 1; // 存在上午打卡但不存在下午打卡
    } else if (!hasMorningRecord && hasAfternoonRecord) {
        return 2; // 只存在下午打卡
    } else {
        return 3; // 存在上午打卡又存在下午打卡
    }
}

// 显示提示框
function showAlert(title, message, type) {
    // 创建提示框元素
    const alertOverlay = document.createElement('div');
    alertOverlay.className = 'alert-overlay';

    const alertBox = document.createElement('div');
    alertBox.className = `alert-box alert-${type}`;

    const iconClass = type === 'success' ? '✓' : '✕';

    alertBox.innerHTML = `
        <div class="alert-icon">${iconClass}</div>
        <h3>${title}</h3>
        <div class="alert-message">${message}</div>
        <button class="alert-button">确定</button>
    `;

    alertOverlay.appendChild(alertBox);
    document.body.appendChild(alertOverlay);

    // 绑定关闭事件
    alertBox.querySelector('.alert-button').addEventListener('click', function () {
        document.body.removeChild(alertOverlay);
    });
}

// 返回今日打卡视图
function showAttendanceList() {
    const statsArea = document.querySelector('.attendance-stats');
    const attendanceList = document.querySelector('.attendance-list');
    const signButton = document.querySelector('.sign-button');

    if (statsArea && attendanceList) {
        attendanceList.style.display = 'block';
        statsArea.style.display = 'none';

        // 检查是否应该显示打卡按钮
        if (signButton) {
            const notices = document.querySelectorAll('.notice');
            let shouldShow = true;

            for (let notice of notices) {
                if (notice.textContent.includes('已完成') ||
                    notice.textContent.includes('非打卡时间') ||
                    notice.textContent.includes('上班期间严禁打卡')) {
                    shouldShow = false;
                    break;
                }
            }

            signButton.style.display = shouldShow ? 'flex' : 'none';
        }
    }
}

// 关闭定时打卡模态框
function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (modal) {
        modal.style.display = 'none';
    }
} 