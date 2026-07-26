# main.py
from kivy.app import App
from kivy.uix.webview import WebView
from kivy.clock import Clock
from kivy.utils import platform
import time
import threading

# ✅ 导入你的服务器
from lan_play_monitor import start_server_in_thread


class LanPlayApp(App):
    def build(self):
        # 先启动本地 HTTP 服务器
        start_server_in_thread()

        self.webview = WebView(url="")

        # Android 上必须延迟加载，否则会闪退
        Clock.schedule_once(self.load_page, 1.5)
        return self.webview

    def load_page(self, dt):
        self.webview.url = "http://127.0.0.1:5000"


if __name__ == "__main__":
    LanPlayApp().run()
