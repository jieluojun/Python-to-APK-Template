import threading
import webview
# 导入你现有的 Flask/FastAPI 应用
from lan-play-monitor import app  # 替换成你实际的应用入口

def run_server():
    """在后台线程启动 Web 服务"""
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # 先启动 Web 服务（后台线程）
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 创建嵌入式浏览器窗口，直接加载本地 Web 服务
    webview.create_window(
        title="LanPlayMonitor",       # 窗口标题
        url="http://127.0.0.1:5000",  # 直接指向你的 Web 服务
        width=1000,
        height=700,
        resizable=True,
        min_size=(800, 600),
        text_select=True,
        confirm_close=True            # 关闭时确认
    )
    webview.start()
