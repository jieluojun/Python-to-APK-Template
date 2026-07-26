#!/usr/bin/env python3
"""
LanPlay Monitor - Android WebView Shell
启动 server.py（子进程）+ 显示 WebView
⚠️ 不修改 server.py，原样启动
"""
import os
import sys
import time
import subprocess
import threading

# ===== 启动 server.py =====
def start_server():
    """把 server.py 作为子进程启动，完全不动它的代码"""
    time.sleep(2)

    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

    if not os.path.exists(server_path):
        print(f"❌ server.py not found at {server_path}")
        return

    print(f"🚀 Starting server.py: {server_path}")

    try:
        proc = subprocess.Popen(
            [sys.executable, server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print(f"✅ server.py PID: {proc.pid}")

        def read_output():
            for line in proc.stdout:
                print(f"[server] {line.decode('utf-8', errors='replace').strip()}")
            for line in proc.stderr:
                print(f"[server ERR] {line.decode('utf-8', errors='replace').strip()}")

        t = threading.Thread(target=read_output, daemon=True)
        t.start()

    except Exception as e:
        print(f"❌ Failed to start server.py: {e}")
        # 兜底：尝试 import 方式
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

        webview.setWebViewClient(WebViewClient())
        webview.loadUrl("http://127.0.0.1:5000")

        layout = LinearLayout(activity)
        layout.setOrientation(LinearLayout.VERTICAL)
        params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
        layout.addView(webview, params)

        activity.setContentView(layout)

    create()

# ===== 入口 =====
if __name__ == "__main__":
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    start_webview()
