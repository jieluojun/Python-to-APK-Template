#!/usr/bin/env python3
"""
LanPlay Monitor - Android WebView Shell
启动 Flask 服务 + 显示 WebView
"""
import os
import threading
import time

# ===== 启动 Flask 服务 =====
def start_flask():
    """在子线程中启动 Flask 服务"""
    # 等待 WebView 准备好再启动（给点时间让 Android 初始化）
    time.sleep(2)

    # 导入你的 Flask 应用
    # server.py 里应该有类似：
    #   from flask import Flask
    #   app = Flask(__name__)
    #   @app.route("/") ...
    #   if __name__ == "__main__":
    #       app.run(host="127.0.0.1", port=5000)
    #
    # 我们只 import server 模块，它会在 import 时启动 app
    # 然后用 app.run() 启动服务

    import server  # 你的 Flask 代码
    # 如果 server.py 里有 app = Flask(__name__)，直接用：
    if hasattr(server, 'app'):
        server.app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    else:
        # 兼容直接运行 server.py 的方式
        import subprocess
        subprocess.Popen(["python", "-c", "import server; server.app.run(host='127.0.0.1', port=5000)"])


# ===== 启动 WebView =====
def start_webview():
    """调用 Android 原生 WebView 加载本地 Flask 页面"""
    from jnius import autoclass
    from android.runnable import run_on_ui_thread

    # Android 原生类
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    LinearLayout = autoclass('android.widget.LinearLayout')
    LayoutParams = autoclass('android.widget.LinearLayout$LayoutParams')
    Settings = autoclass('android.webkit.WebSettings')

    activity = PythonActivity.mActivity

    @run_on_ui_thread
    def create():
        # 创建 WebView
        webview = WebView(activity)

        # 启用 JavaScript（Flask 页面通常需要）
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

        # 创建布局并添加 WebView
        layout = LinearLayout(activity)
        layout.setOrientation(LinearLayout.VERTICAL)
        params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
        layout.addView(webview, params)

        # 设置到 Activity 上
        activity.setContentView(layout)

    create()


# ===== 入口 =====
if __name__ == "__main__":
    # 后台线程启动 Flask
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    # 主线程启动 WebView
    start_webview()
