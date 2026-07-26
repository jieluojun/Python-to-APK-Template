#!/usr/bin/env python3
"""
LanPlay Monitor - Android WebView Shell
启动 server.py（你的 Flask 服务）+ 显示 WebView
⚠️ 不修改 server.py，直接当子进程运行
"""
import os
import sys
import time
import subprocess
import threading

# ===== 启动 server.py（你的监控服务）=====
def start_server():
    """把 server.py 作为子进程启动，完全不动它的代码"""
    time.sleep(2)  # 等 Android 环境就绪

    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

    if not os.path.exists(server_path):
        print(f"❌ server.py not found at {server_path}")
        return

    print(f"🚀 Starting server.py: {server_path}")

    # 直接运行 python server.py
    # 这样 server.py 里写的 app.run() 或任何启动方式都能正常工作
    try:
        proc = subprocess.Popen(
            [sys.executable, server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print(f"✅ server.py PID: {proc.pid}")

        # 读取输出（调试用）
        def read_output():
            for line in proc.stdout:
                print(f"[server] {line.decode('utf-8', errors='replace').strip()}")
            for line in proc.stderr:
                print(f"[server ERR] {line.decode('utf-8', errors='replace').strip()}")

        t = threading.Thread(target=read_output, daemon=True)
        t.start()

    except Exception as e:
        print(f"❌ Failed to start server.py: {e}")
        # 如果子进程方式失败，尝试直接 import 运行
        try:
            import server
            if hasattr(server, 'app'):
                server.app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")

# ===== 启动 WebView =====
def start_webview():
    """调用 Android 原生 WebView 加载本地 Flask 页面"""
    from jnius import autoclass
    from android.runnable import run_on_ui_thread

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    LinearLayout = autoclass('android.widget.LinearLayout')
    LayoutParams = autoclass('android.widget.LinearLayout$LayoutParams')

    activity = PythonActivity.mActivity

    @run_on_ui_thread
    def create():
        webview = WebView(activity)
        settings = webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setAllowFileAccess(True)
        settings.setAllowContentAccess(True)

        # 禁止跳浏览器
        webview.setWebViewClient(WebViewClient())

        # 加载本地 Flask 服务
        webview.loadUrl("http://127.0.0.1:5000")

        layout = LinearLayout(activity)
        layout.setOrientation(LinearLayout.VERTICAL)
        params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
        layout.addView(webview, params)

        activity.setContentView(layout)

    create()

# ===== 入口 =====
if __name__ == "__main__":
    # 后台线程启动 server.py（原样不动）
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # 主线程启动 WebView
    start_webview()
