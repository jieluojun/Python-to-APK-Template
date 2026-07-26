from kivy.uix.webview import WebView
from kivy.base import runTouchApp
import time
import urllib.request

def is_server_ready():
    try:
        urllib.request.urlopen("http://127.0.0.1:5000", timeout=1)
        return True
    except:
        return False

# 等待最多 5 秒
for i in range(10):
    if is_server_ready():
        break
    time.sleep(0.5)

runTouchApp(WebView(url="http://127.0.0.1:5000"))
