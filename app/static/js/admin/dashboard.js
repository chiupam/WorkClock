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
    
    // 统计卡片动画效果
    const statsCards = document.querySelectorAll('.stats-card');
    statsCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
        });
    });
});
