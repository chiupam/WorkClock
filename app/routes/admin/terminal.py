import os
import pty
import select
import signal
import struct
import fcntl
import termios
import asyncio
import uuid
import sqlite3
import time
import subprocess
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from starlette.websockets import WebSocketState
from app import USER_DB_FILE, logger
from app.auth.dependencies import admin_required
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["终端"])

# 存储活跃终端进程
terminals: Dict[str, Dict[str, Any]] = {}
# 存储WebSocket连接
websocket_connections: Dict[str, WebSocket] = {}
# 防止重复清理
terminal_cleaning: Dict[str, bool] = {}

# 检查是否在Docker容器中运行
IN_DOCKER = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

@router.get("/terminal")
@admin_required
async def get_terminal_page(request: Request):
    """终端页面路由"""
    # 使用Jinja2模板渲染页面
    templates = Jinja2Templates(directory="app/static/templates")
    
    # 获取用户信息
    open_id = request.cookies.get("open_id", "")
    user_info = {"username": "管理员"}
    if open_id:
        try:
            conn = sqlite3.connect(USER_DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE open_id = ?", (open_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                user_info["username"] = result[0]
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
    
    # 获取系统统计信息
    from app.routes.admin.utils import get_admin_stats
    stats = await get_admin_stats()
    
    # 渲染模板
    return templates.TemplateResponse(
        "admin/terminal.html", 
        {"request": request, "user_info": user_info, "stats": stats}
    )

@router.websocket("/terminal/ws")
async def terminal_websocket(websocket: WebSocket):
    """处理终端WebSocket连接"""
    # 验证管理员权限
    await websocket.accept()
    
    # 从请求头中获取cookie
    cookies = websocket.cookies
    open_id = cookies.get("open_id")
    
    if not open_id:
        await websocket.send_json({
            "type": "error",
            "message": "未提供认证信息，请登录后重试"
        })
        await websocket.close(code=1008)
        return
        
    try:
        # 连接数据库验证管理员身份
        conn = sqlite3.connect(USER_DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_activity FROM users WHERE open_id = ? AND user_id = 'admin'", 
            (open_id,)
        )
        admin = cursor.fetchone()
        
        # 检查是否管理员
        if not admin:
            await websocket.send_json({
                "type": "error",
                "message": "非管理员用户无法访问终端"
            })
            await websocket.close(code=1008)
            conn.close()
            return
            
        # 更新管理员最后活跃时间
        current_time = int(time.time())
        cursor.execute(
            "UPDATE users SET last_activity = ? WHERE open_id = ?",
            (current_time, open_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"终端WebSocket认证失败: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": "认证失败，请重新登录"
        })
        await websocket.close(code=1008)
        return
    
    # 生成唯一终端ID
    term_id = str(uuid.uuid4())
    websocket_connections[term_id] = websocket
    terminal_cleaning[term_id] = False
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "output",
            "data": "\r\n\x1b[32m终端连接已建立。\x1b[0m\r\n欢迎使用Web终端。输入命令开始操作。\r\n"
        })
        
        # 创建终端
        cols = 80
        rows = 24
        success = await create_terminal(term_id, cols, rows)
        
        if not success:
            await websocket.send_json({
                "type": "error",
                "message": "无法创建终端进程，请检查系统配置"
            })
            await cleanup_terminal(term_id)
            return
        
        # 开始接收消息
        while term_id in terminals and term_id in websocket_connections:
            if websocket.client_state == WebSocketState.DISCONNECTED:
                break
                
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "input":
                    # 处理用户输入
                    if term_id in terminals:
                        cmd_data = data.get("data", "")
                        try:
                            if "fd" in terminals[term_id]:
                                os.write(terminals[term_id]["fd"], cmd_data.encode())
                        except Exception as e:
                            logger.error(f"写入终端失败: {str(e)}")
                            # 尝试重新创建终端
                            if "restart_count" not in terminals[term_id] or terminals[term_id]["restart_count"] < 3:
                                await websocket.send_json({
                                    "type": "output",
                                    "data": "\r\n\x1b[33m终端连接已断开，正在尝试重新连接...\x1b[0m\r\n"
                                })
                                terminals[term_id]["restart_count"] = terminals[term_id].get("restart_count", 0) + 1
                                await create_terminal(term_id, terminals[term_id].get("cols", 80), terminals[term_id].get("rows", 24))
                            else:
                                raise Exception("终端重连失败次数过多")
                
                elif data.get("type") == "resize":
                    # 处理终端大小调整
                    if term_id in terminals:
                        new_cols = data.get("cols", terminals[term_id].get("cols", 80))
                        new_rows = data.get("rows", terminals[term_id].get("rows", 24))
                        if "fd" in terminals[term_id]:
                            resize_terminal(terminals[term_id]["fd"], new_cols, new_rows)
                        terminals[term_id]["cols"] = new_cols
                        terminals[term_id]["rows"] = new_rows
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息错误: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"处理命令时出错: {str(e)}"
                })
                break
    
    except Exception as e:
        logger.error(f"终端WebSocket错误: {str(e)}")
    finally:
        # 清理资源
        await cleanup_terminal(term_id)

async def create_terminal(term_id: str, cols: int = 80, rows: int = 24):
    """创建一个新的终端进程"""
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    
    # 检测可用的shell
    def find_shell():
        # Docker中常用shell路径
        shell_paths = [
            "/bin/bash", 
            "/bin/sh",
            "/usr/bin/bash",
            "/usr/bin/sh", 
            "/usr/local/bin/bash",
            os.environ.get("SHELL", "")
        ]
        
        # 尝试获取默认shell
        try:
            # 获取当前用户的默认shell
            result = subprocess.run(["getent", "passwd", str(os.getuid())], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                shell = result.stdout.strip().split(":")[-1]
                if shell and os.path.exists(shell):
                    shell_paths.insert(0, shell)
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
            
        # 检查每个shell是否存在
        for shell in shell_paths:
            if shell and os.path.exists(shell) and os.access(shell, os.X_OK):
                return shell
                
        # 如果找不到bash或sh，尝试找任何可执行的shell
        for shell in ["bash", "sh"]:
            try:
                result = subprocess.run(["which", shell], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    shell_path = result.stdout.strip()
                    if shell_path and os.path.exists(shell_path):
                        return shell_path
            except (FileNotFoundError, subprocess.SubprocessError):
                pass
                
        return None
    
    shell = find_shell()
    
    if not shell:
        logger.error("找不到可用的shell")
        if term_id in websocket_connections:
            try:
                await websocket_connections[term_id].send_json({
                    "type": "error",
                    "message": "无法找到可用的shell，请联系管理员"
                })
            except Exception:
                pass
        return False
    
    logger.info(f"创建终端，使用shell: {shell}")
    
    try:
        # 在Docker容器中可能需要特殊处理
        if IN_DOCKER:
            # 确保权限正确
            try:
                subprocess.run(["chmod", "+x", shell], check=False)
            except Exception:
                pass
                
        # 创建伪终端
        pid, fd = pty.fork()
        
        if pid == 0:
            # 子进程
            try:
                # 设置环境变量
                os.chdir(os.path.expanduser("~"))
                
                # 执行shell
                os.execvpe(shell, [shell], env)
            except Exception as e:
                logger.error(f"子进程执行shell失败: {str(e)}")
                os._exit(1)
        else:
            # 父进程
            # 设置为非阻塞模式
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            
            # 设置终端大小
            resize_terminal(fd, cols, rows)
            
            # 保存终端信息
            terminals[term_id] = {
                "pid": pid,
                "fd": fd,
                "cols": cols,
                "rows": rows,
                "created_at": time.time(),
                "restart_count": 0,
                "shell": shell
            }
            
            # 启动读取循环
            asyncio.create_task(read_terminal_output(term_id))
            
            # 发送初始命令以显示当前路径
            try:
                # 为Docker环境优化的命令，优先进入/app目录
                cmd = (
                    "cd /app 2>/dev/null || cd $HOME 2>/dev/null || cd / && "
                    "clear && "
                    "echo \"Terminal Connected - $(pwd)\""
                )
                os.write(fd, f"{cmd}\n".encode())
            except Exception as e:
                logger.error(f"发送初始命令失败: {str(e)}")
            
            return True
    except Exception as e:
        logger.error(f"创建终端失败: {str(e)}")
        if term_id in websocket_connections:
            try:
                await websocket_connections[term_id].send_json({
                    "type": "error",
                    "message": f"创建终端失败: {str(e)}"
                })
            except Exception:
                pass
        return False

def resize_terminal(fd: int, cols: int, rows: int):
    """调整终端大小"""
    try:
        # 使用TIOCSWINSZ调整终端窗口大小
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except Exception as e:
        logger.error(f"调整终端大小失败: {str(e)}")

async def read_terminal_output(term_id: str):
    """后台任务：读取终端输出并发送到WebSocket"""
    if term_id not in terminals or term_id not in websocket_connections:
        logger.error(f"终端ID不存在: {term_id}")
        return
    
    try:
        term = terminals[term_id]
        websocket = websocket_connections[term_id]
        
        # 确保这些值存在
        if "fd" not in term or "pid" not in term:
            logger.error(f"终端信息不完整: {term_id}")
            return
        
        fd = term["fd"]
        pid = term["pid"]
        max_read_bytes = 1024 * 8  # 8KB
        
        # 检查进程是否存在
        process_exists = False
        try:
            os.kill(pid, 0)  # 不发送信号，只检查进程是否存在
            process_exists = True
        except OSError:
            logger.error(f"终端进程不存在: {term_id}, PID: {pid}")
        
        if not process_exists:
            await cleanup_terminal(term_id)
            return
        
        # 读取循环
        while term_id in terminals and term_id in websocket_connections:
            # 检查WebSocket连接
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.info(f"WebSocket已断开: {term_id}")
                break
            
            # 使用select确保数据可读，有超时保护
            try:
                await asyncio.sleep(0.05)  # 减少CPU使用率
                r, _, _ = select.select([fd], [], [], 0.1)
                if not r:
                    # 检查进程是否还存在
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        logger.info(f"终端进程已结束: {term_id}")
                        break
                    continue
                
                data = os.read(fd, max_read_bytes)
                if not data:
                    # 没有数据可能表示终端已关闭
                    await asyncio.sleep(0.2)  # 再等一下看看
                    try:
                        # 再次检查进程
                        os.kill(pid, 0)
                        # 再试一次读取
                        r, _, _ = select.select([fd], [], [], 0.1)
                        if r:
                            continue  # 有数据可读，继续循环
                    except OSError:
                        logger.info(f"终端进程已结束: {term_id}")
                        break
                
                # 发送数据到客户端
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({
                        "type": "output",
                        "data": data.decode("utf-8", errors="replace")
                    })
            
            except (OSError, select.error) as e:
                error_msg = str(e)
                if "Bad file descriptor" in error_msg:
                    logger.info(f"文件描述符已关闭: {term_id}")
                else:
                    logger.error(f"读取终端输出错误: {error_msg}")
                break
            except Exception as e:
                logger.error(f"处理终端输出时未知错误: {str(e)}")
                break
    
    except Exception as e:
        logger.error(f"终端读取任务错误: {str(e)}")
    
    # 终端已关闭，清理资源
    await cleanup_terminal(term_id)

async def cleanup_terminal(term_id: str):
    """清理终端资源"""
    # 防止重复清理
    if term_id in terminal_cleaning and terminal_cleaning[term_id]:
        return
    
    try:
        # 标记为正在清理
        terminal_cleaning[term_id] = True
        
        if term_id in terminals:
            term = terminals[term_id]
            
            # 结束进程
            if "pid" in term:
                pid = term["pid"]
                try:
                    # 检查进程是否存在
                    try:
                        os.kill(pid, 0)
                        # 进程存在，发送终止信号
                        logger.info(f"发送SIGTERM到进程: {pid}")
                        os.kill(pid, signal.SIGTERM)
                        
                        # 等待进程结束
                        for _ in range(3):  # 最多等待0.3秒
                            await asyncio.sleep(0.1)
                            try:
                                os.kill(pid, 0)
                            except OSError:
                                # 进程已终止
                                break
                        
                        # 如果进程仍然存在，强制结束
                        try:
                            os.kill(pid, 0)
                            logger.info(f"进程未响应SIGTERM，发送SIGKILL: {pid}")
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            # 进程已终止
                            pass
                    except OSError:
                        # 进程已不存在
                        pass
                except Exception as e:
                    logger.info(f"结束进程出错，可能已终止: {str(e)}")
            
            # 关闭文件描述符
            if "fd" in term:
                try:
                    fd = term["fd"]
                    os.close(fd)
                except OSError as e:
                    # 忽略"Bad file descriptor"错误
                    if "Bad file descriptor" not in str(e):
                        logger.info(f"关闭文件描述符错误: {str(e)}")
            
            # 从字典中删除终端
            del terminals[term_id]
        
        # 通知客户端
        if term_id in websocket_connections:
            ws = websocket_connections[term_id]
            if ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_json({
                        "type": "error",
                        "message": "终端会话已结束"
                    })
                except Exception as e:
                    logger.info(f"发送终端结束通知失败: {str(e)}")
            
            # 从字典中删除连接
            del websocket_connections[term_id]
            
        # 清理完成，移除标记
        if term_id in terminal_cleaning:
            del terminal_cleaning[term_id]
            
    except Exception as e:
        logger.error(f"清理终端资源失败: {str(e)}")
        # 清理失败也要移除标记
        if term_id in terminal_cleaning:
            del terminal_cleaning[term_id] 