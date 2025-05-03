document.addEventListener('DOMContentLoaded', function() {
    const setupForm = document.getElementById('setup-form');
    const submitBtn = document.getElementById('submit-btn');
    const successMessage = document.getElementById('success-message');
    const errorMessage = document.getElementById('error-message');
    
    setupForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // 清除所有错误信息
        document.querySelectorAll('.error-message').forEach(el => {
            el.style.display = 'none';
            el.textContent = '';
        });
        
        // 获取表单数据
        const apiHost = document.getElementById('api_host').value.trim();
        const adminPassword = document.getElementById('admin_password').value;
        const adminPasswordConfirm = document.getElementById('admin_password_confirm').value;
        const fuckPassword = document.getElementById('fuck_password').value;
        
        // 验证数据
        let hasError = false;
        
        if (!apiHost) {
            showError('api_host_error', 'API主机地址不能为空');
            hasError = true;
        }
        
        if (adminPassword.length < 6) {
            showError('admin_password_error', '管理员密码长度不能少于6个字符');
            hasError = true;
        }
        
        if (adminPassword !== adminPasswordConfirm) {
            showError('admin_password_confirm_error', '两次输入的密码不一致');
            hasError = true;
        }
        
        if (!fuckPassword) {
            showError('fuck_password_error', 'FuckDaka密码不能为空');
            hasError = true;
        }
        
        if (hasError) {
            return;
        }
        
        // 禁用提交按钮
        submitBtn.disabled = true;
        submitBtn.textContent = '正在提交...';
        
        try {
            // 发送数据到服务器
            const response = await fetch('/setup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_host: apiHost,
                    admin_password: adminPassword,
                    admin_password_confirm: adminPasswordConfirm,
                    fuck_password: fuckPassword
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 显示成功消息
                successMessage.textContent = result.message;
                successMessage.style.display = 'block';
                
                // 禁用按钮
                submitBtn.disabled = true;
                submitBtn.textContent = '配置已保存';
                
                // 设置更长的等待时间，并显示倒计时
                const waitSeconds = 30; // 增加到30秒
                let remainingSeconds = waitSeconds;
                
                // 更新倒计时消息
                const updateCountdown = () => {
                    successMessage.textContent = `${result.message} 页面将在 ${remainingSeconds} 秒后刷新...`;
                    if (remainingSeconds <= 0) {
                        clearInterval(countdownInterval);
                        window.location.reload();
                    }
                    remainingSeconds--;
                };
                
                // 初始更新
                updateCountdown();
                
                // 设置倒计时
                const countdownInterval = setInterval(updateCountdown, 1000);
            } else {
                // 显示错误消息
                errorMessage.textContent = result.message;
                errorMessage.style.display = 'block';
                
                // 恢复提交按钮
                submitBtn.disabled = false;
                submitBtn.textContent = '完成设置';
            }
        } catch (error) {
            console.error('提交过程中发生错误:', error);
            
            // 处理可能是由于服务器重启导致的连接中断
            // 创建一个警告消息，而不是错误消息
            const warningMessage = document.createElement('div');
            warningMessage.className = 'message warning-message';
            warningMessage.id = 'warning-message';
            warningMessage.innerHTML = `
                提交过程中连接断开，这可能是因为系统正在重启。<br>
                系统配置可能已保存成功，页面将在 <span id="auto-refresh-countdown">30</span> 秒后自动刷新。<br>
                <button id="manual-refresh">立即刷新</button>
            `;
            
            // 隐藏错误消息，显示警告消息
            errorMessage.style.display = 'none';
            // 找到表单的父元素并添加警告消息
            const container = document.querySelector('.setup-container');
            
            // 检查是否已存在警告消息
            if (!document.getElementById('warning-message')) {
                container.appendChild(warningMessage);
            } else {
                document.getElementById('warning-message').style.display = 'block';
            }
            
            // 禁用提交按钮，避免重复提交
            submitBtn.disabled = true;
            submitBtn.textContent = '系统可能正在重启';
            
            // 设置自动刷新倒计时
            let refreshSeconds = 30;
            const countdownElement = document.getElementById('auto-refresh-countdown');
            
            const refreshCountdown = setInterval(() => {
                refreshSeconds--;
                if (countdownElement) {
                    countdownElement.textContent = refreshSeconds;
                }
                
                if (refreshSeconds <= 0) {
                    clearInterval(refreshCountdown);
                    window.location.reload();
                }
            }, 1000);
            
            // 添加手动刷新按钮事件
            setTimeout(() => {
                document.getElementById('manual-refresh').addEventListener('click', () => {
                    window.location.reload();
                });
            }, 100);
        }
    });
    
    function showError(elementId, message) {
        const errorElement = document.getElementById(elementId);
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
});