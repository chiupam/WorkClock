document.addEventListener('DOMContentLoaded', () => {
    // 创建终端实例
    const terminal = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#1e1e1e',
            foreground: '#f0f0f0',
            cursor: '#ffffff',
            selectionBackground: '#5a5a5a'
        },
        fontSize: 14,
        fontFamily: 'Menlo, Monaco, "Courier New", monospace',
        scrollback: 1000,
        allowTransparency: true,
        convertEol: true
    });

    // 初始化终端
    const terminalElement = document.getElementById('terminal');
    terminal.open(terminalElement);

    // 使用FitAddon使终端自适应容器
    const fitAddon = new FitAddon.FitAddon();
    terminal.loadAddon(fitAddon);

    // 调整终端大小
    function resizeTerminal() {
        try {
            fitAddon.fit();
            if (socket && socket.readyState === WebSocket.OPEN) {
                // 发送大小调整消息
                socket.send(JSON.stringify({
                    type: 'resize',
                    cols: terminal.cols,
                    rows: terminal.rows
                }));
            }
        } catch (e) {
            console.error('终端自适应错误:', e);
        }
    }

    // 初始化尺寸 - 延迟执行确保DOM完全加载
    setTimeout(resizeTerminal, 100);

    // 调整窗口大小时重新适应
    window.addEventListener('resize', () => {
        // 防抖动处理，避免频繁调整
        if (window.resizeTimer) clearTimeout(window.resizeTimer);
        window.resizeTimer = setTimeout(resizeTerminal, 200);
    });

    // 设置WebSocket连接
    let socket = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    let reconnectTimeout = null;
    let isConnecting = false;

    // 心跳检测
    let heartbeatInterval = null;
    const heartbeatTime = 30000; // 30秒

    function setupHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
        }

        heartbeatInterval = setInterval(() => {
            if (socket && socket.readyState === WebSocket.OPEN) {
                // 发送心跳
                try {
                    socket.send(JSON.stringify({
                        type: 'heartbeat'
                    }));
                } catch (e) {
                    console.error('心跳发送失败:', e);
                    // 如果发送失败，尝试重连
                    if (!isConnecting) {
                        attemptReconnect();
                    }
                }
            } else {
                // 如果连接不是开放状态，尝试重连
                if (!isConnecting) {
                    attemptReconnect();
                }
            }
        }, heartbeatTime);
    }

    function connectWebSocket() {
        if (isConnecting) return;
        isConnecting = true;

        // 获取当前域名和WebSocket协议
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;

        // 构建WebSocket URL - 优先使用相对路径避免跨域问题
        const wsUrl = `${protocol}//${host}/admin/terminal/ws`;

        // 关闭任何现有连接
        if (socket && socket.readyState !== WebSocket.CLOSED) {
            try {
                socket.close();
            } catch (e) {
                console.error('关闭现有连接失败:', e);
            }
        }

        // 提示正在连接
        terminal.writeln('\r\n\x1b[33m正在连接终端...\x1b[0m');

        try {
            // 创建新连接
            socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                isConnecting = false;
                reconnectAttempts = 0;

                // 清除任何重连计时器
                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                    reconnectTimeout = null;
                }

                terminal.writeln('\r\n\x1b[32m终端连接已建立\x1b[0m');

                // 设置终端输入监听
                terminal.onData(data => {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        try {
                            socket.send(JSON.stringify({
                                type: 'input',
                                data: data
                            }));
                        } catch (e) {
                            console.error('发送输入失败:', e);
                            terminal.writeln('\r\n\x1b[31m发送命令失败，连接可能已断开\x1b[0m');
                        }
                    } else {
                        terminal.writeln('\r\n\x1b[31m连接已断开，无法发送命令\x1b[0m');
                        if (!isConnecting) {
                            attemptReconnect();
                        }
                    }
                });

                // 调整终端大小适应容器
                setTimeout(resizeTerminal, 100);

                // 设置心跳检测
                setupHeartbeat();
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'output') {
                        terminal.write(data.data);
                    } else if (data.type === 'error') {
                        terminal.writeln(`\r\n\x1b[31m错误: ${data.message}\x1b[0m`);
                        // 如果是终端会话结束的消息，尝试自动重连
                        if (data.message === '终端会话已结束' && !isConnecting) {
                            attemptReconnect();
                        }
                    } else if (data.type === 'heartbeat_response') {
                        // 心跳响应，什么都不做
                    }
                } catch (e) {
                    // 如果不是JSON格式，直接输出
                    terminal.write(event.data);
                }
            };

            socket.onclose = (event) => {
                isConnecting = false;
                terminal.writeln('\r\n\x1b[33m终端连接已关闭\x1b[0m');

                if (event.wasClean) {
                    terminal.writeln(`关闭代码: ${event.code}, 原因: ${event.reason || '未知'}`);
                } else {
                    terminal.writeln('\x1b[31m连接意外断开\x1b[0m');
                    attemptReconnect();
                }

                // 清除心跳检测
                if (heartbeatInterval) {
                    clearInterval(heartbeatInterval);
                    heartbeatInterval = null;
                }
            };

            socket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                terminal.writeln('\r\n\x1b[31m连接错误，请检查网络或服务器状态\x1b[0m');
                isConnecting = false;
            };
        } catch (error) {
            console.error('创建WebSocket连接失败:', error);
            terminal.writeln('\r\n\x1b[31m无法创建连接，请刷新页面重试\x1b[0m');
            isConnecting = false;
        }
    }

    function attemptReconnect() {
        if (isConnecting) return;

        // 清除现有的重连计时器
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
        }

        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const timeoutMs = Math.min(1000 * reconnectAttempts, 5000);

            terminal.writeln(`\x1b[33m${timeoutMs / 1000}秒后尝试重新连接 (${reconnectAttempts}/${maxReconnectAttempts})...\x1b[0m`);

            reconnectTimeout = setTimeout(() => {
                terminal.writeln('\x1b[33m尝试重新连接...\x1b[0m');
                connectWebSocket();
            }, timeoutMs);
        } else {
            terminal.writeln('\x1b[31m达到最大重试次数，请点击"重新连接"按钮或刷新页面\x1b[0m');

            // 更新按钮文本和功能
            const reconnectBtn = document.getElementById('disconnectTerminal');
            if (reconnectBtn) {
                reconnectBtn.textContent = '重新连接';
                reconnectBtn.onclick = function () {
                    reconnectAttempts = 0;
                    terminal.clear();
                    connectWebSocket();
                    setTimeout(() => {
                        this.textContent = '断开连接';
                        this.onclick = disconnectTerminal;
                    }, 1000);
                };
            }
        }
    }

    // 初始化连接
    connectWebSocket();

    // 清空终端按钮
    document.getElementById('clearTerminal').addEventListener('click', () => {
        terminal.clear();
    });

    // 断开连接按钮
    function disconnectTerminal() {
        // 清除重连计时器
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }

        // 清除心跳检测
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }

        if (socket && socket.readyState === WebSocket.OPEN) {
            try {
                socket.close();
                terminal.writeln('\r\n\x1b[33m已手动断开连接\x1b[0m');
            } catch (e) {
                console.error('关闭连接失败:', e);
                terminal.writeln('\r\n\x1b[31m断开连接失败: ' + e.message + '\x1b[0m');
            }
        } else {
            // 已断开，尝试重新连接
            reconnectAttempts = 0;
            terminal.clear();
            connectWebSocket();
        }
    }

    // 设置断开连接按钮
    document.getElementById('disconnectTerminal').addEventListener('click', disconnectTerminal);

    // 使用MutationObserver监视终端容器变化，自动调整大小
    const observer = new MutationObserver(() => {
        setTimeout(resizeTerminal, 0);
    });

    const container = document.querySelector('.terminal-container');
    if (container) {
        observer.observe(container, {
            attributes: true,
            childList: true,
            subtree: true
        });
    }

    // 页面退出时断开连接
    window.addEventListener('beforeunload', () => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }

        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
        }

        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
        }
    });
}); 