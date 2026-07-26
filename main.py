import threading
import webview
from lan_play_monitor import app


def run_server():
    """在后台线程启动 Web 服务"""
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False  # ⚠️ PyInstaller 下必须关
    )


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    webview.create_window(
        title="LanPlay Monitor",
        url="http://127.0.0.1:5000",
        width=1000,
        height=700,
        resizable=True,
        min_size=(800, 600),
        text_select=True,
        confirm_close=True
    )

    webview.start()
