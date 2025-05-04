// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
    // 获取当前设置
    loadSettings();
});

// 加载设置
function loadSettings() {
    axios.get('/admin/settings-api')
        .then(function (response) {
            if (response.data.success) {
                const settings = response.data.settings;

                // 填充表单
                document.getElementById('system_name').value = settings.system_name ? settings.system_name.value : '';
                document.getElementById('api_host').value = settings.api_host ? settings.api_host.value : '';
                // 密码字段不回显
            } else {
                showAlert('danger', '加载设置失败: ' + response.data.message);
            }
        })
        .catch(function (error) {
            console.error('获取设置失败:', error);
            showAlert('danger', '获取设置失败，请检查网络连接');
        });
}

// 保存设置
function saveSettings() {
    // 显示正在保存的提示
    showAlert('info', '正在保存设置...');

    // 禁用保存按钮，防止重复提交
    const saveButton = document.querySelector('.btn-primary');
    if (saveButton) saveButton.disabled = true;

    // 获取表单数据
    const formData = {
        system_name: document.getElementById('system_name').value,
        api_host: document.getElementById('api_host').value
    };

    // 仅当密码不为空时才包含密码字段
    const adminPassword = document.getElementById('admin_password').value;
    if (adminPassword) {
        formData.admin_password = adminPassword;
    }

    const fuckPassword = document.getElementById('fuck_password').value;
    if (fuckPassword) {
        formData.fuck_password = fuckPassword;
    }

    // 打印要发送的数据
    console.log('发送设置数据:', formData);

    // 发送请求
    axios.post('/admin/settings-api', formData)
        .then(function (response) {
            console.log('服务器响应:', response.data);
            if (response.data.success) {
                let message = response.data.message;

                // 显示成功消息
                showAlert('success', message);

                // 清空密码字段
                document.getElementById('admin_password').value = '';
                document.getElementById('fuck_password').value = '';

                // 如果后端返回重启标记，显示提示并开始轮询服务器状态
                if (response.data.restart) {
                    showAlert('info', '系统正在重启，请稍候，页面将在服务器重启后自动刷新...');
                    // 等待几秒后开始检查服务器状态
                    setTimeout(function () {
                        checkServerStatus();
                    }, 3000);
                }
            } else {
                showAlert('danger', '保存设置失败: ' + response.data.message);
                // 重新启用保存按钮
                if (saveButton) saveButton.disabled = false;
            }
        })
        .catch(function (error) {
            console.error('保存设置失败:', error);
            if (error.response) {
                console.error('错误响应数据:', error.response.data);
                console.error('错误状态码:', error.response.status);
                showAlert('danger', `保存设置失败: ${error.response.status} - ${error.response.data.message || '未知错误'}`);
            } else if (error.request) {
                // 请求已发送但未收到响应，可能是服务器正在重启
                console.error('未收到响应:', error.request);
                showAlert('info', '服务器可能正在重启，页面将在服务器恢复后自动刷新...');
                // 开始轮询检查服务器状态
                setTimeout(function () {
                    checkServerStatus();
                }, 3000);
            } else {
                console.error('请求配置错误:', error.message);
                showAlert('danger', '保存设置失败: ' + error.message);
            }

            // 重新启用保存按钮（如果是重启情况，按钮会保持禁用状态）
            if (error.response) {
                if (saveButton) saveButton.disabled = false;
            }
        });
}

// 更新项目代码
function updateCode(event) {
    // 显示正在更新的提示
    showAlert('info', '正在更新项目代码...');

    // 禁用更新按钮，防止重复提交
    const updateButton = document.querySelector('.btn-warning');
    if (updateButton) updateButton.disabled = true;

    // 获取是否强制更新
    const forceUpdate = document.getElementById('force_update') ? document.getElementById('force_update').checked : false;

    // 如果选择了强制更新，显示确认提示
    if (forceUpdate && !confirm('强制更新将清除本地所有修改并获取最新代码，是否继续？')) {
        // 用户取消了操作
        showAlert('info', '已取消更新操作');
        if (updateButton) updateButton.disabled = false;
        return;
    }

    // 显示正在执行的操作
    if (forceUpdate) {
        showAlert('info', '正在执行强制更新，可能需要较长时间...');
    }

    // 防止表单默认提交
    event.preventDefault();

    // 发送更新代码请求，包含强制更新选项
    axios.post('/admin/update-code',
        JSON.stringify({ force_update: forceUpdate }),
        {
            headers: {
                'Content-Type': 'application/json'
            }
        }
    )
        .then(function (response) {
            console.log('服务器响应:', response.data);
            if (response.data.success) {
                // 显示成功消息
                showAlert('success', response.data.message);

                // 如果需要重启，显示提示并开始轮询服务器状态
                if (response.data.restart) {
                    showAlert('info', '代码已更新，系统正在重启，请稍候，页面将在服务器重启后自动刷新...');
                    // 等待几秒后开始检查服务器状态
                    setTimeout(function () {
                        checkServerStatus();
                    }, 3000);
                } else {
                    // 5秒后重新启用更新按钮
                    setTimeout(function () {
                        if (updateButton) updateButton.disabled = false;
                    }, 5000);
                }
            } else {
                showAlert('danger', '更新代码失败: ' + response.data.message);
                // 重新启用更新按钮
                if (updateButton) updateButton.disabled = false;
            }
        })
        .catch(function (error) {
            console.error('更新代码失败:', error);
            if (error.response) {
                console.error('错误响应数据:', error.response.data);
                console.error('错误状态码:', error.response.status);
                showAlert('danger', `更新代码失败: ${error.response.status} - ${error.response.data.message || '未知错误'}`);
            } else if (error.request) {
                // 请求已发送但未收到响应，可能是服务器正在重启
                console.error('未收到响应:', error.request);
                showAlert('info', '服务器可能正在重启，页面将在服务器恢复后自动刷新...');
                // 开始轮询检查服务器状态
                setTimeout(function () {
                    checkServerStatus();
                }, 3000);
            } else {
                console.error('请求配置错误:', error.message);
                showAlert('danger', '更新代码失败: ' + error.message);
            }

            // 重新启用更新按钮（如果是重启情况，按钮会保持禁用状态）
            if (error.response) {
                if (updateButton) updateButton.disabled = false;
            }
        });
}

// 检查服务器状态
function checkServerStatus() {
    console.log('检查服务器状态...');

    // 发送一个简单的GET请求到任何可用的端点
    axios.get('/admin/settings')
        .then(function () {
            console.log('服务器已恢复！');
            showAlert('success', '服务器重启完成，正在刷新页面...');
            // 服务器已恢复，刷新页面
            setTimeout(function () {
                window.location.reload();
            }, 1500);
        })
        .catch(function (error) {
            console.log('服务器仍在重启中...', error.message);
            // 服务器仍未恢复，继续轮询
            setTimeout(checkServerStatus, 2000);
        });
}

// 重置表单
function resetForm() {
    document.getElementById('settings-form').reset();
    loadSettings();
}

// 显示提示
function showAlert(type, message) {
    const alertEl = document.getElementById('alert');
    alertEl.className = 'alert alert-' + type;
    alertEl.textContent = message;

    // 只有在非持续性消息时（非info类型）才自动隐藏
    if (type !== 'info') {
        // 3秒后自动隐藏
        setTimeout(function () {
            alertEl.className = 'alert alert-hidden';
        }, 3000);
    }
}