document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const loginButton = document.getElementById('login-button');
    const phoneInput = document.getElementById('phone');
    const passwordInput = document.getElementById('password');
    const errorMessage = document.getElementById('error-message');
    const loadingIndicator = document.getElementById('loading');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault(); // 阻止默认表单提交
            
            // 验证表单
            if (!phoneInput.value.trim()) {
                showError('请输入账号');
                return;
            }
            
            if (!passwordInput.value.trim()) {
                showError('请输入密码');
                return;
            }
            
            // 显示加载中状态
            loadingIndicator.style.display = 'block';
            errorMessage.style.display = 'none';
            loginButton.disabled = true;
            
            // 准备登录数据
            const loginData = {
                phone: phoneInput.value.trim(),
                password: passwordInput.value.trim()
            };
            
            // 使用Axios发送登录请求
            axios.post('/auth/login', loginData)
                .then(response => {
                    // 登录成功，跳转到首页
                    window.location.href = '/';
                })
                .catch(error => {
                    // 处理错误
                    let errorMsg = '登录失败，请稍后重试';
                    
                    if (error.response) {
                        // 服务器返回了错误状态码
                        if (error.response.data && error.response.data.message) {
                            errorMsg = error.response.data.message;
                        }
                    } else if (error.request) {
                        // 请求发送成功，但没有收到响应
                        errorMsg = '无法连接到服务器，请检查网络';
                    }
                    
                    showError(errorMsg);
                })
                .finally(() => {
                    // 恢复登录按钮状态
                    loginButton.disabled = false;
                    loadingIndicator.style.display = 'none';
                });
        });
    }
    
    // 显示错误信息的辅助函数
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        loadingIndicator.style.display = 'none';
        loginButton.disabled = false;
    }
}); 