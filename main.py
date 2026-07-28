import sys
import os
import traceback

APP_CORE_PATH = "/sdcard/lanplay/app_core.py"

def run_app():
    # 优先加载外部脚本
    if os.path.exists(APP_CORE_PATH):
        try:
            with open(APP_CORE_PATH, "r", encoding="utf-8") as f:
                code = compile(f.read(), APP_CORE_PATH, "exec")
                g = {"__name__": "__main__", "__file__": APP_CORE_PATH}
                exec(code, g)
            return
        except Exception:
            print("❌ 加载 /sdcard/lanplay/app_core.py 失败：")
            traceback.print_exc()
            # 失败后 fallback 到内置版本

    # fallback：使用打包内的 app_core
    print("ℹ️ 使用内置 app_core")
    from app_core import run_app as _run
    _run()

if __name__ == "__main__":
    run_app()
