import importlib.util
import sys
import os

APP_PATH = "/sdcard/lanplay/app_core.py"

def load_app():
    if os.path.exists(APP_PATH):
        spec = importlib.util.spec_from_file_location("app_core", APP_PATH)
        app = importlib.util.module_from_spec(spec)
        sys.modules["app_core"] = app
        spec.loader.exec_module(app)
        app.run_app()
    else:
        # fallback：使用打包内的版本
        from app_core import run_app
        run_app()

if __name__ == "__main__":
    load_app()
