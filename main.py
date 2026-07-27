# main.py
"""
Kivy WebView 入口 —— 加载 lan_play_monitor.py 的 HTTP Server
"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.webview import WebView
from kivy.utils import platform

import threading
import os
import sys

# 把当前目录加入 path，确保能 import lan_play_monitor
sys.path.append(os.path.dirname(__file__))


class LanPlayRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.status = Label(
            text="🎮 正在启动 LAN-Play Monitor...",
            size_hint_y=0.08,
            color=(1, 1, 1, 1),
            font_size="14sp",
        )
        self.add_widget(self.status)

        self.webview = WebView(size_hint_y=0.92)
        self.add_widget(self.webview)

        # 后台启动 HTTP Server（非阻塞）
        threading.Thread(target=self._start_server, daemon=True).start()

    def _start_server(self):
        try:
            # ✅ import 并启动 lan_play_monitor 的 HTTP Server
            import lan_play_monitor
            lan_play_monitor.start_server(host="127.0.0.1", port=5000)

            self.status.text = (
                f"✅ LAN-Play Monitor 已启动 | "
                f"服务器: {len(lan_play_monitor.SERVERS)} 个"
            )

            # 加载本地 WebView
            self.webview.url = "http://127.0.0.1:5000/"

        except Exception as e:
            self.status.text = f"❌ 启动失败: {e}"


class LanPlayApp(App):
    def build(self):
        self.title = "Direct LDN"
        return LanPlayRoot()

    def on_pause(self):
        # Android 切后台不杀进程
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    LanPlayApp().run()
