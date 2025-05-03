/**
 * embed.html页面UI控制脚本
 */
document.addEventListener('DOMContentLoaded', function() {
    // 获取考勤统计按钮并添加点击事件
    const statsBtn = document.getElementById('stats-btn');
    if (statsBtn) {
        statsBtn.addEventListener('click', function() {
            // 获取当前URL中的user_id参数
            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('user_id');
            
            if (userId) {
                // 重定向到考勤统计页面
                window.location.href = `/admin/user/embed/metrics?user_id=${userId}`;
            }
        });
    }
    
    // 获取添加定时按钮并添加点击事件
    const scheduleBtn = document.getElementById('schedule-btn');
    if (scheduleBtn) {
        scheduleBtn.addEventListener('click', function() {
            // 这里可以添加定时功能逻辑
            alert('定时功能即将推出，敬请期待！');
        });
    }
    
    // 通知父级iframe调整高度，设置最大值1000px
    function notifyParentToResizeIframe() {
        const height = Math.min(document.body.scrollHeight, 1000);
        if (window.parent && window.parent.postMessage) {
            window.parent.postMessage({ type: 'resize-iframe', height: height }, '*');
        }
    }
    
    // 只在加载完成后调整一次高度
    window.addEventListener('load', function() {
        // 延迟执行，确保内容完全加载
        setTimeout(notifyParentToResizeIframe, 300);
    });
}); 