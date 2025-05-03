document.addEventListener('DOMContentLoaded', function() {
    // 侧边栏切换
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const adminLayout = document.querySelector('.admin-layout');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            adminLayout.classList.toggle('sidebar-collapsed');
            this.classList.toggle('active');
            
            // 保存状态
            localStorage.setItem('sidebarCollapsed', adminLayout.classList.contains('sidebar-collapsed'));
        });
    }
    
    // 点击遮罩层关闭侧边栏
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            adminLayout.classList.remove('sidebar-collapsed');
            if (sidebarToggle) {
                sidebarToggle.classList.remove('active');
            }
            localStorage.setItem('sidebarCollapsed', 'false');
        });
    }
    
    // 侧边栏中的链接点击后在移动设备上自动关闭侧边栏
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                adminLayout.classList.remove('sidebar-collapsed');
                if (sidebarToggle) {
                    sidebarToggle.classList.remove('active');
                }
            }
        });
    });
    
    // 保存用户侧边栏状态
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        adminLayout.classList.add('sidebar-collapsed');
        if (sidebarToggle) {
            sidebarToggle.classList.add('active');
        }
    }
    
    // 响应窗口大小变化
    window.addEventListener('resize', function() {
        if (window.innerWidth < 768 && !adminLayout.classList.contains('sidebar-collapsed')) {
            adminLayout.classList.add('sidebar-collapsed');
            if (sidebarToggle) {
                sidebarToggle.classList.add('active');
            }
            localStorage.setItem('sidebarCollapsed', 'true');
        }
    });
    
    // 自动检测小屏幕并折叠侧边栏
    if (window.innerWidth < 768 && !adminLayout.classList.contains('sidebar-collapsed')) {
        adminLayout.classList.add('sidebar-collapsed');
        if (sidebarToggle) {
            sidebarToggle.classList.add('active');
        }
    }
}); 