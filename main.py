from kivy.uix.webview import WebView
from kivy.base import runTouchApp

runTouchApp(
    WebView(url="http://127.0.0.1:5000")
)
