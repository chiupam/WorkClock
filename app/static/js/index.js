// 初始化页面信息
async function getInfo() {
  // 显示加载指示器
  document.getElementById('loading-spinner').style.display = 'flex';
  
  try {
    const response = await fetch('/getInfo', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': document.cookie
      }
    });
    
    const data = await response.json();
    
    if (data.success) {
      displayUserInfo(data.user);
      displayAttendanceData(data.attendance);
      if (data.attendance.isworkingday) {
        checkShowSignButton(data.button);
      }
    } else {
      console.error('获取考勤记录失败：', data.message);
      alert('获取考勤记录失败：' + data.message);
    }
  } catch (error) {
    console.error('获取考勤记录错误：', error);
    alert('获取考勤记录错误：' + error.message);
  } finally {
    // 隐藏加载指示器
    document.getElementById('loading-spinner').style.display = 'none';
  }
}

// 显示用户信息
async function displayUserInfo(data) {
  document.getElementById('userName').textContent = data.userName;
  document.getElementById('depId').textContent = data.depId;
  document.getElementById('userId').textContent = data.userId;
  document.getElementById('position').textContent = data.position || '未知';
  document.getElementById('depName').textContent = data.depName || '未知';

  // 保存用户数据到 localStorage
  localStorage.setItem('userData', JSON.stringify(data));
}

// 显示考勤数据
function displayAttendanceData(data) {
  const container = document.getElementById('attendanceData');
  
  // 如果今天是休息日，只显示休息提示
  if (!data.isworkingday) {
    container.innerHTML = `
      <div class="attendance-record" style="background-color: #f6ffed; border: 1px solid #b7eb8f;">
        <div class="record-content">
          <div style="color: #52c41a; padding: 10px;">
            <strong>温馨提示：</strong>今天是休息日，无需打卡。祝您休息愉快！
          </div>
        </div>
      </div>
    `;
    // 确保不显示打卡按钮
    document.querySelector('.sign-button').style.display = 'none';
    return;
  }
  
  // SVG 图标
  const clockSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`;
  const locationSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>`;
  const upSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>`;
  const downSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>`;
  
  let html = '';

  // 区分错误信息和补卡提醒
  if (data.errorMsg) {
    html += `
      <div class="attendance-record" style="background-color: #fff0f0; border: 1px solid #ffcdd2;">
        <div class="record-content">
          <div style="color: #d32f2f; padding: 10px;">
            <strong>请求出错：</strong>${data.errorMsg}
          </div>
        </div>
      </div>
    `;
  } else if (data.needReminder) {
    html += `
      <div class="attendance-record" style="background-color: #fff3cd; border: 1px solid #ffeeba;">
        <div class="record-content">
          <div style="color: #856404; padding: 10px;">
            <strong>温馨提示：</strong>今日上班未打卡，请尽快联系相关人员进行补卡。
          </div>
        </div>
      </div>
    `;
  }

  // 显示打卡记录
  const records = [data.clockInRecord, data.clockOutRecord].filter(Boolean);
  
  if (records.length > 0) {
    html += records.map(record => `
      <div class="attendance-record" id="${record.type === '上班' ? 'clockIn' : 'clockOut'}">
        <div class="standard-time">
          规定${record.type}时间 ${record.standardTime}
        </div>
        <div class="record-content">
          <div class="record-details">
            <div class="type-and-info">
              <div class="clock-type-badge">
                ${record.type === "上班" ? upSvg : downSvg}
              </div>
              <div class="info-group">
                <div class="time-info">
                  <span class="time-icon">${clockSvg}</span>
                  ${record.clockTime}
                </div>
                <div class="location-info">
                  <span class="location-icon">${locationSvg}</span>
                  ${record.location}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `).join('');
  } else if (!data.needReminder && !data.errorMsg) {
    html = '<p class="no-records">暂无打卡记录</p>';
  }
  
  container.innerHTML = html;
}

// 检查是否显示打卡按钮
function checkShowSignButton(data) {            
  const signButton = document.querySelector('.sign-button');
  lastButtonState = data; // 保存按钮状态
  if (data.show) {
    signButton.style.display = 'flex';

    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    const attType = currentTime >= 17 * 60 ? `下班` : `上班`;
    signButton.querySelector('span:not(.time)').textContent = `${attType}打卡`;

    return true;
  } else {
    signButton.style.display = 'none';
    return false;
  }
}

// 更新时间显示
function updateTime() {
  const now = new Date();
  const timeString = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  document.getElementById('currentTime').textContent = timeString;
}

// 签到功能
async function signIn() {
  // 显示加载指示器
  const loadingOverlay = document.createElement('div');
  loadingOverlay.className = 'alert-overlay';
  
  const loadingBox = document.createElement('div');
  loadingBox.className = 'loading-box';
  loadingBox.innerHTML = `
    <div class="spinner"></div>
    <div class="loading-text">正在打卡，请稍候...</div>
  `;
  
  loadingOverlay.appendChild(loadingBox);
  document.body.appendChild(loadingOverlay);

  const now = new Date();
  const currentTime = now.getHours() * 60 + now.getMinutes();
  try {
    const response = await fetch('/sign', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': document.cookie
      },
      body: JSON.stringify({
        depId: JSON.parse(localStorage.getItem('userData')).depId,
        attType: currentTime >= 17 * 60 ? `下班` : `上班`,
        clockIn: document.getElementById('clockIn') !== null,
        clockOut: document.getElementById('clockOut') !== null
      })
    });
    
    const result = await response.json();
    
    // 移除加载指示器
    loadingOverlay.remove();
    
    // 创建提示框
    const overlay = document.createElement('div');
    overlay.className = 'alert-overlay';
    
    const alertBox = document.createElement('div');
    alertBox.className = `alert-box ${result.success ? 'alert-success' : 'alert-error'}`;
    
    if (result.success) {
      // 成功提示，显示倒计时
      alertBox.innerHTML = `
        <div class="alert-icon">✓</div>
        <div class="alert-message">
          ${result.message}
        </div>
        <div class="countdown" style="color: #666; margin-top: 10px;">3 秒后自动刷新</div>
      `;
      
      overlay.appendChild(alertBox);
      document.body.appendChild(overlay);
      
      // 倒计时并自动刷新
      let countdown = 3;
      const countdownEl = alertBox.querySelector('.countdown');
      const timer = setInterval(() => {
        countdown--;
        countdownEl.textContent = `${countdown} 秒后自动刷新`;
        if (countdown <= 0) {
          clearInterval(timer);
          overlay.remove();
          getInfo();
        }
      }, 1000);
    } else {
      // 失败提示，保持原样
      alertBox.innerHTML = `
        <div class="alert-icon">✕</div>
        <div class="alert-message">
          打卡失败：${result.message}
        </div>
        <button class="alert-button" onclick="closeAlert(this)">确定</button>
      `;
      
      overlay.appendChild(alertBox);
      document.body.appendChild(overlay);
    }
  } catch (error) {
    // 移除加载指示器
    document.querySelector('.alert-overlay')?.remove();
    
    // 显示错误提示
    const overlay = document.createElement('div');
    overlay.className = 'alert-overlay';
    
    const alertBox = document.createElement('div');
    alertBox.className = 'alert-box alert-error';
    
    alertBox.innerHTML = `
      <div class="alert-icon">✕</div>
      <div class="alert-message">
        签到错误：${error.message}
      </div>
      <button class="alert-button" onclick="closeAlert(this)">确定</button>
    `;
    
    overlay.appendChild(alertBox);
    document.body.appendChild(overlay);
  }
}

// 添加关闭提示框的函数
function closeAlert(button) {
  const overlay = button.closest('.alert-overlay');
  if (overlay) {
    overlay.remove();
  }
}

// 登出功能
async function logout() {
  localStorage.removeItem('userData');
  window.location.href = '/logout';
}

// 添加 SVG 图标
const checkSvgGreen = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#52c41a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
const checkSvgYellow = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#faad14" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
const crossSvgRed = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ff4d4f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;

// 添加返回打卡页面的函数
function showAttendanceList() {
  const attendanceList = document.querySelector('.attendance-list');
  const attendanceStats = document.querySelector('.attendance-stats');
  const signButton = document.querySelector('.sign-button');
  
  attendanceStats.style.display = 'none';
  attendanceList.style.display = 'block';
  if (signButton && checkShowSignButton(lastButtonState)) signButton.style.display = 'flex';
}

// 保存按钮状态的变量
let lastButtonState = null;

async function showAttendanceStats() {
  const attendanceList = document.querySelector('.attendance-list');
  const attendanceStats = document.querySelector('.attendance-stats');
  const signButton = document.querySelector('.sign-button');
  
  // 显示加载指示器
  document.getElementById('loading-spinner').style.display = 'flex';
  
  try {
    const response = await fetch('/getYueTjList?' + new URLSearchParams({
      month: document.getElementById('monthSelect').value
    }));
    const data = await response.json();
    const statistics = data.statistics
    const details = data.details

    // 更新统计数据
    if (statistics) {
      document.getElementById('leaveDays').textContent = statistics.LeaveDays || 0;
      document.getElementById('lateNumber').textContent = statistics.LateNumber || 0;
      document.getElementById('ztNumber').textContent = statistics.ZtNumber || 0;
      document.getElementById('lackCarNumber').textContent = statistics.LackCarNumber || 0;
    }
    
    const tbody = document.getElementById('statsTableBody');
    const today = new Date();
    const currentMonth = today.getMonth() + 1;
    const selectedMonth = parseInt(document.getElementById('monthSelect').value);
    const selectedYear = today.getFullYear();
    
    // 获取选中月份的第一天是星期几（0-6，0代表星期日）
    const firstDay = new Date(selectedYear, selectedMonth - 1, 1).getDay();
    // 获取选中月份的总天数
    const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
    
    let html = '';
    let dayCounter = 1;
    
    // 生成日历表格
    for (let week = 0; dayCounter <= daysInMonth; week++) {
      html += '<tr>';
      
      for (let weekday = 0; weekday < 7; weekday++) {
        if (week === 0 && weekday < firstDay || dayCounter > daysInMonth) {
          html += '<td></td>';
        } else {
          const day = details[dayCounter - 1];
          let dayContent = `<div class="calendar-day">${dayCounter}`;
          
          // 判断是否是未来日期
          const selectedDate = new Date(selectedYear, selectedMonth - 1, dayCounter);
          const isInFuture = selectedDate > today;
          
          if (isInFuture) {
            // 未来日期不显示任何状态
            dayContent += '</div>';
            html += `<td>${dayContent}</td>`;
            dayCounter++;
            continue;
          }
          
          // 添加上下班状态
          if (day) {
            if (day.isholiday === 1 && day.jjr) {
              dayContent += `<div class="holiday-name">${
                day.jjr.includes("节") && day.jjr.length > 2 ? day.jjr.replace("节", "") : day.jjr
              }</div>`;
            } else if (day.IsQj === 1) {
              dayContent += `<div class="leave-day">请假</div>`;
            } else if (selectedMonth === currentMonth && dayCounter === today.getDate()) {
              // 当天的打卡状态
              dayContent += `<div class="day-status">`;
              if (today.getHours() >= 9) {
                dayContent += day.SWSBDKCS === 0 ? crossSvgRed :
                  (day.IsSwSbbuka === 1 ? checkSvgYellow : checkSvgGreen);
              } else {
                dayContent += `<span class="pending-sign">待</span>`;
              }
              if (today.getHours() >= 17) {
                dayContent += day.XWXBDKCS === 0 ? crossSvgRed :
                  (day.IsXwXbbuka === 1 ? checkSvgYellow : checkSvgGreen);
              } else {
                dayContent += `<span class="pending-sign">待</span>`;
              }
              dayContent += `</div>`;
            } else if (day.isholiday === 1) {
              dayContent += `<div class="rest-day">休息</div>`;
            } else {
              dayContent += `<div class="day-status">`;
              dayContent += day.SWSBDKCS === 0 ? crossSvgRed :
                (day.IsSwSbbuka === 1 ? checkSvgYellow : checkSvgGreen);
              dayContent += day.XWXBDKCS === 0 ? crossSvgRed :
                (day.IsXwXbbuka === 1 ? checkSvgYellow : checkSvgGreen);
              dayContent += `</div>`;
            }
          }
          
          dayContent += '</div>';
          html += `<td>${dayContent}</td>`;
          dayCounter++;
        }
      }
      
      html += '</tr>';
    }
    
    tbody.innerHTML = html;
    
    attendanceList.style.display = 'none';
    if (signButton) signButton.style.display = 'none';
    attendanceStats.style.display = 'block';
  } catch (error) {
    console.error('获取考勤统计失败：', error);
    alert('获取考勤统计失败：' + error.message);
  } finally {
    document.getElementById('loading-spinner').style.display = 'none';
  }
}

// 显示定时打卡模态框
function showScheduleModal() {
  // 首先获取当前用户的定时任务设置
  fetchScheduleSettings();
  // 显示模态框
  document.getElementById('scheduleModal').style.display = 'block';
}

// 关闭定时打卡模态框
function closeScheduleModal() {
  document.getElementById('scheduleModal').style.display = 'none';
}

// 获取用户当前的定时任务设置
async function fetchScheduleSettings() {
  try {
    const response = await fetch('/getScheduleSettings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': document.cookie
      }
    });
    
    const data = await response.json();
    
    if (data.success) {
      // 设置复选框状态
      document.getElementById('scheduleMorning').checked = data.settings.scheduleMorning;
      document.getElementById('scheduleAfternoon').checked = data.settings.scheduleAfternoon;
      
      // 显示用户的定时打卡时间
      updateScheduleTimes(data.schedule_times, data.current_users, data.max_users);
    } else {
      console.error('获取定时设置失败：', data.message);
    }
  } catch (error) {
    console.error('获取定时设置错误：', error);
  }
}

// 更新定时打卡时间显示
function updateScheduleTimes(scheduleTimes, currentUsers, maxUsers) {
  const scheduleTimesDiv = document.getElementById('schedule-times');
  const morningTimesSpan = document.querySelector('#morning-times .time-values');
  const afternoonTimesSpan = document.querySelector('#afternoon-times .time-values');
  const warningDiv = document.getElementById('user-limit-warning');
  
  // 显示时间区域
  scheduleTimesDiv.style.display = 'block';
  
  // 显示打卡时间
  if (scheduleTimes.user_position >= 0 && scheduleTimes.user_position <= 2) {
    morningTimesSpan.textContent = scheduleTimes.morning_times.join('、');
    afternoonTimesSpan.textContent = scheduleTimes.afternoon_times.join('、');
    
    // 如果已有定时任务设置，隐藏警告
    warningDiv.style.display = 'none';
  } else if (currentUsers >= maxUsers) {
    // 如果定时任务已满，显示警告
    warningDiv.style.display = 'block';
    warningDiv.querySelector('p').textContent = `目前定时任务名额已满 (${currentUsers}/${maxUsers})，暂无法添加。`;
    
    // 隐藏时间显示
    document.querySelector('.time-details').style.display = 'none';
  }
}

// 保存定时打卡设置
async function saveSchedule() {
  // 显示加载指示器
  document.getElementById('loading-spinner').style.display = 'flex';
  
  try {
    const scheduleMorning = document.getElementById('scheduleMorning').checked;
    const scheduleAfternoon = document.getElementById('scheduleAfternoon').checked;
    
    const response = await fetch('/saveScheduleSettings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': document.cookie
      },
      body: JSON.stringify({
        scheduleMorning: scheduleMorning,
        scheduleAfternoon: scheduleAfternoon
      })
    });
    
    const result = await response.json();
    
    // 关闭模态框
    closeScheduleModal();
    
    // 创建提示框
    const overlay = document.createElement('div');
    overlay.className = 'alert-overlay';
    
    const alertBox = document.createElement('div');
    alertBox.className = `alert-box ${result.success ? 'alert-success' : 'alert-error'}`;
    
    if (result.success) {
      alertBox.innerHTML = `
        <div class="alert-icon">✓</div>
        <div class="alert-message">
          ${result.message}
        </div>
        <button class="alert-button" onclick="closeAlert(this)">确定</button>
      `;
    } else {
      alertBox.innerHTML = `
        <div class="alert-icon">✕</div>
        <div class="alert-message">
          保存失败：${result.message}
        </div>
        <button class="alert-button" onclick="closeAlert(this)">确定</button>
      `;
    }
    
    overlay.appendChild(alertBox);
    document.body.appendChild(overlay);
    
  } catch (error) {
    console.error('保存定时设置错误：', error);
    
    // 显示错误提示
    const overlay = document.createElement('div');
    overlay.className = 'alert-overlay';
    
    const alertBox = document.createElement('div');
    alertBox.className = 'alert-box alert-error';
    
    alertBox.innerHTML = `
      <div class="alert-icon">✕</div>
      <div class="alert-message">
        保存错误：${error.message}
      </div>
      <button class="alert-button" onclick="closeAlert(this)">确定</button>
    `;
    
    overlay.appendChild(alertBox);
    document.body.appendChild(overlay);
  } finally {
    // 隐藏加载指示器
    document.getElementById('loading-spinner').style.display = 'none';
  }
}

// 初始化时设置当前月份
function initMonthSelect() {
  const currentMonth = new Date().getMonth() + 1;
  document.getElementById('monthSelect').value = currentMonth;
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  // 初始化
  getInfo();
  setInterval(updateTime, 1000);
  updateTime();
  initMonthSelect();
}); 