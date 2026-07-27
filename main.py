# main.py
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.webview import WebView
from kivy.utils import platform

import threading
import os
import sys

# 把 lan_play_monitor 加入路径
sys.path.append(os.path.dirname(__file__))


class LanPlayRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.status = Label(
            text="🎮 正在启动 LAN-Play Monitor...",
            size_hint_y=0.08,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.status)

        self.webview = WebView(size_hint_y=0.92)
        self.add_widget(self.webview)

        # 后台启动 HTTP Server
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        try:
            # 启动 lan_play_monitor.py 里的主逻辑
            from lan_play_monitor import APP_NAME, SERVERS

            self.status.text = (
                f"✅ {APP_NAME} 已启动\n"
                f"服务器数量: {len(SERVERS)}"
            )

            # 加载本地 WebView
            self.webview.url = "http://127.0.0.1:5000/"

        except Exception as e:
            self.status.text = f"❌ 启动失败: {e}"


class LanPlayApp(App):
    def build(self):
        return LanPlayRoot()

    def on_pause(self):
        # Android 切后台不杀进程
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    LanPlayApp().run()
