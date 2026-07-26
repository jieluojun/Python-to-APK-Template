#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kivy WebView Shell for LAN-Play Monitor
"""

import os
os.environ["KIVY_ORIENTATION"] = "Portrait"

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from jnius import autoclass
from android.runnable import run_on_ui_thread

PythonActivity = autoclass("org.kivy.android.PythonActivity")
WebView = autoclass("android.webkit.WebView")
WebViewClient = autoclass("android.webkit.WebViewClient")
LinearLayout = autoclass("android.widget.LinearLayout")
LayoutParams = autoclass("android.widget.LinearLayout$LayoutParams")

activity = PythonActivity.mActivity


class RootWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 白底，防黑屏
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # 延迟启动 HTTP Server + WebView
        Clock.schedule_once(self.start, 0.5)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    @run_on_ui_thread
    def start(self, *_):
        # 启动 HTTP Server（后台线程）
        import threading
        t = threading.Thread(target=self.run_server, daemon=True)
        t.start()

        # WebView
        webview = WebView(activity)
        settings = webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setAllowFileAccess(True)

        webview.setWebViewClient(WebViewClient())
        webview.loadUrl("http://127.0.0.1:5000")

        layout = LinearLayout(activity)
        layout.setOrientation(LinearLayout.VERTICAL)
        layout.addView(webview, LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT
        ))

        activity.addContentView(layout, LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT
        ))

    def run_server(self):
        import server  # ✅ 你原来的完整监控程序


class LanPlayApp(App):
    def build(self):
        return RootWidget()


if __name__ == "__main__":
    LanPlayApp().run()
