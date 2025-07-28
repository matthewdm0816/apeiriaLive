# ui_server.py

import asyncio
from mcp.server.fastmcp import FastMCP
import tkinter as tk
from tkinter import messagebox

# 1. 初始化 FastMCP 服务器
# 我们给它起个名字叫 "ui_server"
mcp = FastMCP("ui_server")

# 这是一个辅助函数，用来在独立的线程中运行GUI代码
# 因为tkinter这种GUI库通常不是线程安全的，而且会阻塞asyncio的事件循环
# 所以把它放到一个独立的线程里执行是最稳妥的方式
def show_message_sync(title: str, message: str):
    """同步的GUI显示函数"""
    root = tk.Tk()
    root.withdraw()  # 我们不想要那个空白的根窗口，所以隐藏它
    root.attributes("-topmost", True) # 确保消息框在最上层
    messagebox.showinfo(title, message)
    root.destroy() # 完成后销毁窗口，释放资源

# 2. 定义我们的工具 (Tool)
# FastMCP会自动从函数签名和文档字符串生成工具的定义
@mcp.tool()
async def display_message_box(title: str, message: str) -> str:
    """
    在用户的桌面上显示一个图形化的消息框。
    当需要向用户显示一条简短的通知或消息时使用此工具。

    Args:
        title: 消息框窗口的标题。
        message: 要显示的消息内容。
    """
    # 获取当前的asyncio事件循环
    loop = asyncio.get_running_loop()
    
    # 使用 loop.run_in_executor 在一个独立的线程中运行我们的GUI函数
    # 这样就不会阻塞服务器的主线程了
    await loop.run_in_executor(
        None,  # 使用默认的线程池执行器
        show_message_sync, # 要运行的同步函数
        title, # 传递给函数的参数
        message
    )
    
    # 3. 返回一个成功信息给LLM
    # 这样LLM就知道它的指令已经成功执行了
    return f"消息框已成功显示，标题为: '{title}'"

# 4. 运行服务器
if __name__ == "__main__":
    host = "127.0.0.1"  # 监听本地地址
    port = 27890         # 监听8080端口
    
    print(f"Apeiria 正在启动UI工具服务器，监听地址 http://{host}:{port}")
    print("Owner, 您可以随时使用 Ctrl+C 来停止服务器。")
    
    # 启动服务器，这次我们指定 transport 为 'streamable-http'
    mcp.run(transport='streamable-http')

