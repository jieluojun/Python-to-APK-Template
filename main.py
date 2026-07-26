#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LanPlay Monitor - Kivy WebView Shell
====================================
启动 HTTP 监控服务 → WebView 加载 http://127.0.0.1:5000
竖屏 / 白底防黑屏 / 不跳外部浏览器
"""

import os
# 强制竖屏（必须在 import App 之前）
os.environ["KIVY_ORIENTATION"] = "Portrait"

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.logger import Logger

from jnius import autoclass
from android.runnable import run_on_ui_thread

# ===== Android 原生类 =====
PythonActivity = autoclass("org.kivy.android.PythonActivity")
WebView = autoclass("android.webkit.WebView")
WebViewClient = autoclass("android.webkit.WebViewClient")
LinearLayout = autoclass("android.widget.LinearLayout")
LayoutParams = autoclass("android.widget.LinearLayout$LayoutParams")
Settings = autoclass("android.webkit.WebSettings")

activity = PythonActivity.mActivity


class RootWidget(Widget):
    """Kivy 根控件：白底 + 启动 HTTP Server + 加载 WebView"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 白底防黑屏
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        Logger.info("LanPlay: RootWidget init, scheduling start...")
        # 延迟启动，确保 Kivy 先渲染完
        Clock.schedule_once(self._start_all, 0.8)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _start_all(self, dt):
        """在子线程启动 HTTP Server，在主线程创建 WebView"""
        import threading
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()
        Logger.info("LanPlay: HTTP Server thread started")

        # 等一小会儿让 Server 起来再加载 WebView
        Clock.schedule_once(self._create_webview, 1.5)

    def _run_server(self):
        """启动你原来的监控 HTTP 服务"""
        try:
            # 直接 import 你原来的 server 模块
            import server
            Logger.info("LanPlay: server module loaded")
            # 如果你的 server 有 main() 或 run() 函数，在这里调用
            # 例如：server.main()
            # 如果 server.py 在 import 时自动启动，就不用额外调用
        except Exception as e:
            Logger.error(f"LanPlay: Server error: {e}")
            #  fallback: 启动一个最小 HTTP Server 显示错误
            from http.server import HTTPServer, BaseHTTPRequestHandler
            class ErrHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    msg = f"<h2>LanPlay Monitor</h2><p>Server error: {e}</p>"
                    self.wfile.write(msg.encode("utf-8"))
            HTTPServer(("127.0.0.1", 5000), ErrHandler).serve_forever()

    @run_on_ui_thread
    def _create_webview(self, dt):
        """在 Android UI 线程创建原生 WebView"""
        try:
            webview = WebView(activity)

            # 开启 JS / DOM / 数据库（网页需要）
            s = webview.getSettings()
            s.setJavaScriptEnabled(True)
            s.setDomStorageEnabled(True)
            s.setDatabaseEnabled(True)
            s.setAllowFileAccess(True)
            s.setAllowContentAccess(True)
            s.setLoadsImagesAutomatically(True)
            s.setCacheMode(Settings.LOAD_DEFAULT)

            # 关键：拦截链接点击，强制在 App 内打开
            webview.setWebViewClient(WebViewClient())

            # 加载本地 HTTP Server
            webview.loadUrl("http://127.0.0.1:5000")
            Logger.info("LanPlay: WebView loading http://127.0.0.1:5000")

            # 添加到 Activity 布局
            layout = LinearLayout(activity)
            layout.setOrientation(LinearLayout.VERTICAL)
            lp = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
            layout.addView(webview, lp)
            activity.addContentView(layout, lp)
            Logger.info("LanPlay: WebView added to activity")

        except Exception as e:
            Logger.error(f"LanPlay: WebView error: {e}")


class LanPlayApp(App):
    def build(self):
        return RootWidget()


if __name__ == "__main__":
    LanPlayApp().run()
