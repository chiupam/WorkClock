document.addEventListener('DOMContentLoaded', function() {
    // 自定义确认框函数
    function showCustomConfirm(message, confirmCallback, cancelCallback) {
        // 检查是否已存在确认框，避免重复创建
        if (document.getElementById('custom-confirm-modal')) {
            document.getElementById('custom-confirm-modal').remove();
        }
        
        // 创建模态框
        const modal = document.createElement('div');
        modal.id = 'custom-confirm-modal';
        modal.classList.add('modal');
        
        // 模态框内容
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>确认操作</h2>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button id="modal-cancel-btn" class="btn">取消</button>
                    <button id="modal-confirm-btn" class="btn btn-success">确认</button>
                </div>
            </div>
        `;
        
        // 添加到body
        document.body.appendChild(modal);
        
        // 显示模态框
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
        
        // 点击确认按钮
        document.getElementById('modal-confirm-btn').addEventListener('click', function() {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
                if (typeof confirmCallback === 'function') {
                    confirmCallback();
                }
            }, 300);
        });
        
        // 点击取消按钮
        document.getElementById('modal-cancel-btn').addEventListener('click', function() {
            modal.classList.remove('show');
            setTimeout(() => {
                modal.remove();
                if (typeof cancelCallback === 'function') {
                    cancelCallback();
                }
            }, 300);
        });
        
        // 点击模态框外部关闭
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.remove('show');
                setTimeout(() => {
                    modal.remove();
                    if (typeof cancelCallback === 'function') {
                        cancelCallback();
                    }
                }, 300);
            }
        });
    }

    // 检查更新按钮
    document.getElementById('check-update-btn').addEventListener('click', function() {
        const statusBox = document.getElementById('update-status');
        const messageEl = document.getElementById('update-message');
        const logEl = document.getElementById('update-log');
        
        statusBox.classList.remove('hidden');
        statusBox.classList.add('info');
        messageEl.textContent = '正在检查更新...';
        logEl.textContent = '';
        
        fetch('/api/check_update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.has_update) {
                statusBox.classList.remove('info');
                statusBox.classList.add('success');
                messageEl.textContent = `发现新版本: ${data.latest_version}`;
                logEl.textContent = data.changelog || '无更新日志';
            } else {
                statusBox.classList.remove('info');
                statusBox.classList.add('success');
                messageEl.textContent = '已是最新版本';
                logEl.textContent = '';
            }
        })
        .catch(error => {
            statusBox.classList.remove('info');
            statusBox.classList.add('error');
            messageEl.textContent = '检查更新失败';
            logEl.textContent = error.toString();
        });
    });
    
    // 更新系统按钮
    document.getElementById('update-btn').addEventListener('click', function() {
        // 使用自定义确认框替代原生confirm
        showCustomConfirm('确定要更新系统吗？更新过程中请勿关闭页面。', function() {
            // 确认后的操作
            const statusBox = document.getElementById('update-status');
            const messageEl = document.getElementById('update-message');
            const logEl = document.getElementById('update-log');
            const progressBar = document.getElementById('progress-bar');
            const progressContainer = document.getElementById('progress-container');
            
            statusBox.classList.remove('hidden', 'success', 'error');
            statusBox.classList.add('info');
            messageEl.textContent = '正在更新系统...';
            logEl.textContent = '准备更新...';
            progressContainer.style.display = 'block';
            progressBar.style.width = '0%';
            
            // 开始轮询更新状态
            let progress = 0;
            const progressInterval = setInterval(() => {
                if (progress < 90) {
                    progress += Math.random() * 5;
                    progressBar.style.width = `${progress}%`;
                }
            }, 1000);
            
            fetch('/api/update_system', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                clearInterval(progressInterval);
                return response.json();
            })
            .then(data => {
                progressBar.style.width = '100%';
                
                if (data.success) {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('success');
                    messageEl.textContent = '系统更新成功！3秒后刷新页面...';
                    logEl.textContent = data.log || '更新完成';
                    
                    // 3秒后刷新页面
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                } else {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('error');
                    messageEl.textContent = '系统更新失败';
                    logEl.textContent = data.log || '更新失败，请查看日志';
                }
            })
            .catch(error => {
                clearInterval(progressInterval);
                statusBox.classList.remove('info');
                statusBox.classList.add('error');
                messageEl.textContent = '系统更新出错';
                logEl.textContent = error.toString();
                progressBar.style.width = '100%';
            });
        });
    });
    
    // 备份数据按钮
    document.getElementById('backup-btn').addEventListener('click', function() {
        const statusBox = document.getElementById('backup-status');
        const messageEl = document.getElementById('backup-message');
        const logEl = document.getElementById('backup-log');
        
        statusBox.classList.remove('hidden', 'success', 'error');
        statusBox.classList.add('info');
        messageEl.textContent = '正在备份数据...';
        logEl.textContent = '';
        
        fetch('/api/backup_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.blob())
        .then(blob => {
            statusBox.classList.remove('info');
            statusBox.classList.add('success');
            messageEl.textContent = '数据备份成功！';
            
            // 创建下载链接
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            const date = new Date().toISOString().replace(/[:.]/g, '-');
            a.href = url;
            a.download = `workclock-backup-${date}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            statusBox.classList.remove('info');
            statusBox.classList.add('error');
            messageEl.textContent = '数据备份失败';
            logEl.textContent = error.toString();
        });
    });
    
    // 恢复数据按钮
    document.getElementById('restore-btn').addEventListener('click', function() {
        document.getElementById('backup-file').click();
    });
    
    // 文件选择处理
    document.getElementById('backup-file').addEventListener('change', function(e) {
        if (!e.target.files.length) return;
        
        // 使用自定义确认框替代原生confirm
        showCustomConfirm('确定要恢复数据吗？现有数据将被覆盖！', function() {
            const file = e.target.files[0];
            const statusBox = document.getElementById('backup-status');
            const messageEl = document.getElementById('backup-message');
            const logEl = document.getElementById('backup-log');
            
            statusBox.classList.remove('hidden', 'success', 'error');
            statusBox.classList.add('info');
            messageEl.textContent = '正在恢复数据...';
            logEl.textContent = '';
            
            const formData = new FormData();
            formData.append('backup_file', file);
            
            fetch('/api/restore_data', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('success');
                    messageEl.textContent = '数据恢复成功！5秒后刷新页面...';
                    logEl.textContent = '';
                    
                    // 5秒后刷新页面
                    setTimeout(() => {
                        window.location.reload();
                    }, 5000);
                } else {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('error');
                    messageEl.textContent = '数据恢复失败';
                    logEl.textContent = data.error || '未知错误';
                }
            })
            .catch(error => {
                statusBox.classList.remove('info');
                statusBox.classList.add('error');
                messageEl.textContent = '数据恢复请求失败';
                logEl.textContent = error.toString();
            });
        }, function() {
            // 取消时清空文件选择
            e.target.value = '';
        });
    });
    
    // 重启应用按钮
    document.getElementById('restart-btn').addEventListener('click', function() {
        // 使用自定义确认框替代原生confirm
        showCustomConfirm('确定要重启应用吗？', function() {
            const statusBox = document.getElementById('maintenance-status');
            const messageEl = document.getElementById('maintenance-message');
            const logEl = document.getElementById('maintenance-log');
            
            statusBox.classList.remove('hidden', 'success', 'error');
            statusBox.classList.add('info');
            messageEl.textContent = '正在重启应用...';
            logEl.textContent = '';
            
            fetch('/api/restart_app', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('success');
                    messageEl.textContent = '应用重启指令已发送，请等待10秒后刷新页面...';
                    logEl.textContent = '';
                    
                    // 10秒后刷新页面
                    setTimeout(() => {
                        window.location.reload();
                    }, 10000);
                } else {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('error');
                    messageEl.textContent = '应用重启失败';
                    logEl.textContent = data.error || '未知错误';
                }
            })
            .catch(error => {
                statusBox.classList.remove('info');
                statusBox.classList.add('error');
                messageEl.textContent = '应用重启请求失败';
                logEl.textContent = error.toString();
            });
        });
    });
    
    // 重置系统按钮
    document.getElementById('reset-btn').addEventListener('click', function() {
        // 第一次确认
        showCustomConfirm('确定要重置系统吗？所有数据将被删除，此操作不可恢复！', function() {
            // 第二次确认
            showCustomConfirm('再次确认：重置系统将删除所有数据，确定继续吗？', function() {
                const statusBox = document.getElementById('maintenance-status');
                const messageEl = document.getElementById('maintenance-message');
                const logEl = document.getElementById('maintenance-log');
                
                statusBox.classList.remove('hidden', 'success', 'error');
                statusBox.classList.add('info');
                messageEl.textContent = '正在重置系统...';
                logEl.textContent = '';
                
                fetch('/api/reset_system', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statusBox.classList.remove('info');
                        statusBox.classList.add('success');
                        messageEl.textContent = '系统已重置，5秒后将跳转到登录页...';
                        logEl.textContent = '';
                        
                        // 5秒后跳转到登录页
                        setTimeout(() => {
                            window.location.href = '/';
                        }, 5000);
                    } else {
                        statusBox.classList.remove('info');
                        statusBox.classList.add('error');
                        messageEl.textContent = '系统重置失败';
                        logEl.textContent = data.error || '未知错误';
                    }
                })
                .catch(error => {
                    statusBox.classList.remove('info');
                    statusBox.classList.add('error');
                    messageEl.textContent = '系统重置请求失败';
                    logEl.textContent = error.toString();
                });
            });
        });
    });

    // 页面加载时获取当前版本
    fetch('/api/system_info', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.info && data.info.app_version) {
            document.getElementById('current-version').textContent = data.info.app_version;
        }
    })
    .catch(error => {
        console.error('获取系统信息失败:', error);
    });

    // 命令执行功能相关代码
    const commandInput = document.getElementById('command-input');
    const executeBtn = document.getElementById('execute-btn');
    const stopBtn = document.getElementById('stop-btn');
    const commandOutput = document.getElementById('command-output');
    const commandMessage = document.getElementById('command-message');
    const timeoutRange = document.getElementById('timeout-range');
    const timeoutValue = document.getElementById('timeout-value');
    
    // 初始化Socket.IO连接
    const socket = io();
    let isCommandRunning = false;
    
    // 更新超时显示
    timeoutRange.addEventListener('input', function() {
        timeoutValue.textContent = this.value;
    });
    
    // 执行命令
    executeBtn.addEventListener('click', function() {
        const command = commandInput.value.trim();
        if (!command) {
            commandMessage.textContent = '请输入命令';
            return;
        }
        
        // 重置状态
        commandOutput.textContent = '';
        commandMessage.textContent = '正在执行...';
        
        // 更新按钮状态
        executeBtn.disabled = true;
        stopBtn.disabled = false;
        isCommandRunning = true;
        
        // 发送执行命令请求
        socket.emit('execute_command', {
            command: command,
            timeout: parseInt(timeoutRange.value)
        });
    });
    
    // 停止命令
    stopBtn.addEventListener('click', function() {
        if (isCommandRunning) {
            socket.emit('stop_command');
        }
    });
    
    // 监听命令开始执行
    socket.on('command_started', function(data) {
        commandMessage.textContent = data.message;
    });
    
    // 监听命令输出
    socket.on('command_output', function(data) {
        commandOutput.textContent += data.output;
        // 自动滚动到底部
        commandOutput.scrollTop = commandOutput.scrollHeight;
    });
    
    // 监听命令完成
    socket.on('command_completed', function(data) {
        commandMessage.textContent = data.message;
        resetCommandUI();
    });
    
    // 监听命令终止
    socket.on('command_terminated', function(data) {
        commandMessage.textContent = data.message;
        resetCommandUI();
    });
    
    // 监听命令错误
    socket.on('command_error', function(data) {
        commandMessage.textContent = data.message;
        resetCommandUI();
    });
    
    // 连接断开事件
    socket.on('disconnect', function() {
        if (isCommandRunning) {
            commandMessage.textContent = '连接已断开，命令可能已停止执行';
            resetCommandUI();
        }
    });
    
    // 重置命令UI状态
    function resetCommandUI() {
        executeBtn.disabled = false;
        stopBtn.disabled = true;
        isCommandRunning = false;
    }
    
    // 允许按Enter键执行命令
    commandInput.addEventListener('keyup', function(event) {
        if (event.key === 'Enter' && !executeBtn.disabled) {
            executeBtn.click();
        }
    });
}); 