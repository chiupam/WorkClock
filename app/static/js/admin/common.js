document.addEventListener('DOMContentLoaded', function () {
    // 侧边栏切换 - 仅通过按钮控制
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const adminLayout = document.querySelector('.admin-layout');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');

    // 只有点击按钮时才切换侧边栏
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function (e) {
            e.stopPropagation(); // 阻止事件冒泡
            adminLayout.classList.toggle('sidebar-collapsed');
            this.classList.toggle('active');
        });
    }

    // 点击遮罩层关闭侧边栏
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function (e) {
            e.stopPropagation(); // 阻止事件冒泡
            adminLayout.classList.remove('sidebar-collapsed');
            if (sidebarToggle) {
                sidebarToggle.classList.remove('active');
            }
        });
    }

    // 侧边栏中的链接点击后自动关闭侧边栏
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            adminLayout.classList.remove('sidebar-collapsed');
            if (sidebarToggle) {
                sidebarToggle.classList.remove('active');
            }
        });
    });

    // 防止触摸事件干扰侧边栏状态
    document.addEventListener('touchstart', function (e) {
        // 不执行任何操作
    }, { passive: true });

    document.addEventListener('touchmove', function (e) {
        // 不执行任何操作
    }, { passive: true });

    document.addEventListener('touchend', function (e) {
        // 不执行任何操作
    }, { passive: true });
}); 