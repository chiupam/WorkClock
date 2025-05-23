/**
 * 考勤统计页面脚本
 */
document.addEventListener('DOMContentLoaded', function () {
    // 获取URL参数
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');

    if (!userId) {
        alert('用户ID不能为空');
        return;
    }

    // 初始化月份选择器
    const monthSelect = document.getElementById('monthSelect');
    const currentDate = new Date();
    const currentMonth = currentDate.getMonth() + 1; // JavaScript月份从0开始

    // 填充月份选择器
    for (let i = 1; i <= 12; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = i + '月';
        option.selected = i === currentMonth;
        monthSelect.appendChild(option);
    }

    // 添加月份选择事件
    monthSelect.addEventListener('change', function () {
        loadStatsData(userId, this.value);
    });

    // 添加返回按钮事件
    const backBtn = document.getElementById('back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', function () {
            window.location.href = `/admin/user/embed?user_id=${userId}`;
        });
    }

    // 加载初始数据
    loadStatsData(userId, currentMonth);

    // 通知父级iframe调整高度，设置最大值1000px
    function notifyParentToResizeIframe() {
        const height = Math.min(document.body.scrollHeight, 1000);
        if (window.parent && window.parent.postMessage) {
            window.parent.postMessage({ type: 'resize-iframe', height: height }, '*');
        }
    }

    // 函数：加载统计数据
    function loadStatsData(userId, month) {
        const loading = document.getElementById('loading');
        const statsContent = document.getElementById('stats-content');

        loading.style.display = 'flex';
        statsContent.style.display = 'none';

        // 发送POST请求获取数据
        axios.post('/admin/user/embed/metrics', {
            user_id: userId,
            month: parseInt(month),
            year: currentDate.getFullYear()
        })
            .then(function (response) {
                // 请求成功，处理数据
                if (response.data.success) {
                    renderStatsData(response.data);
                } else {
                    alert('获取考勤统计失败: ' + response.data.message);
                }
            })
            .catch(function (error) {
                alert('请求失败: ' + (error.response ? error.response.data.message : error.message));
            })
            .finally(function () {
                loading.style.display = 'none';
                statsContent.style.display = 'block';
                notifyParentToResizeIframe();
            });
    }

    // 函数：渲染统计数据
    function renderStatsData(data) {
        // 更新统计摘要
        if (data.statistics) {
            document.getElementById('leaveDays').textContent = data.statistics.qjts || 0;
            document.getElementById('lateNumber').textContent = data.statistics.cdts || 0;
            document.getElementById('ztNumber').textContent = data.statistics.ztts || 0;
            document.getElementById('lackCarNumber').textContent = data.statistics.qtjcnums || 0;
        }

        // 生成日历表格
        generateCalendar(data.details, data.month, data.year, data.days);

        // 调整iframe高度
        notifyParentToResizeIframe();
    }

    // 函数：生成日历
    function generateCalendar(details, month, year, days) {
        const tableBody = document.getElementById('statsTableBody');
        tableBody.innerHTML = '';

        // 获取每月1号是星期几（0是星期日）
        const firstDay = new Date(year, month - 1, 1).getDay();

        // 计算行数
        const rows = Math.ceil((days + firstDay) / 7);

        // 图标定义
        const checkSvgGreen = `<span style="color: #52c41a;">✓</span>`;
        const checkSvgYellow = `<span style="color: #faad14;">✓</span>`;
        const crossSvgRed = `<span style="color: #ff4d4f;">✕</span>`;

        let dayCount = 1;

        // 创建表格行和单元格
        for (let row = 0; row < rows; row++) {
            const tr = document.createElement('tr');

            for (let col = 0; col < 7; col++) {
                const td = document.createElement('td');

                if ((row === 0 && col < firstDay) || dayCount > days) {
                    // 空单元格
                    td.innerHTML = '';
                } else {
                    // 获取当前日期的数据
                    const day = details[dayCount - 1] || {};

                    // 判断是否是未来日期
                    const selectedDate = new Date(year, month - 1, dayCount);
                    const today = new Date();
                    const isInFuture = selectedDate > today;

                    // 日期数字容器
                    const dayNumber = document.createElement('div');
                    dayNumber.style.fontWeight = 'bold';
                    dayNumber.textContent = dayCount;

                    // 状态容器
                    const statusContainer = document.createElement('div');
                    statusContainer.style.fontSize = '12px';

                    // 添加到单元格
                    td.appendChild(dayNumber);
                    td.appendChild(statusContainer);

                    // 处理休息日和工作日状态
                    if (!isInFuture) {
                        // 处理节假日和休息日
                        if (day.isholiday === 1) {
                            td.className = 'holiday';

                            if (day.jjr) {
                                let holidayName = day.jjr;
                                if (holidayName.length > 2) {
                                    holidayName = holidayName.substring(0, 2);
                                }
                                statusContainer.textContent = holidayName;
                                statusContainer.style.color = '#38a169';
                            } else {
                                statusContainer.textContent = '休';
                                statusContainer.style.color = '#38a169';
                            }
                        }
                        // 处理请假
                        else if (day.IsQj === 1) {
                            statusContainer.textContent = '假';
                            statusContainer.style.color = '#805ad5';
                        }
                        // 处理正常工作日
                        else {
                            // 上午打卡状态
                            const morningStatus = getMorningStatus(day);
                            // 下午打卡状态
                            const afternoonStatus = getAfternoonStatus(day);

                            // 如果上下午都缺卡
                            if (morningStatus === 'missing' && afternoonStatus === 'missing') {
                                statusContainer.textContent = '缺';
                                statusContainer.style.color = '#e53e3e';
                            } else {
                                // 根据上下午状态显示图标
                                let statusContent = '';

                                if (morningStatus === 'normal') {
                                    statusContent += checkSvgGreen;
                                } else if (morningStatus === 'makeup') {
                                    statusContent += checkSvgYellow;
                                } else if (morningStatus === 'missing') {
                                    statusContent += crossSvgRed;
                                }

                                if (afternoonStatus === 'normal') {
                                    statusContent += checkSvgGreen;
                                } else if (afternoonStatus === 'makeup') {
                                    statusContent += checkSvgYellow;
                                } else if (afternoonStatus === 'missing') {
                                    statusContent += crossSvgRed;
                                }

                                statusContainer.innerHTML = statusContent;
                            }
                        }
                    }

                    dayCount++;
                }

                tr.appendChild(td);
            }

            tableBody.appendChild(tr);
        }

        // 调整iframe高度
        notifyParentToResizeIframe();
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

    // 只在加载完成后调整一次高度
    window.addEventListener('load', function () {
        // 延迟执行，确保内容完全加载
        setTimeout(notifyParentToResizeIframe, 300);
    });
}); 