[app]

# ===== 基本信息 =====
title = LanPlayMonitor
package.name = monitor
package.domain = com.lanplay
source.dir = .
source.include_exts = py,kv,html,json,css,js
entrypoint = main.py
version = 1.0.0

# ===== Python 依赖 =====
# 极简：只需要 Flask + jnius（调用原生 WebView）
# 不需要 Kivy！
requirements = python3,flask,jinja2,markupsafe,werkzeug,itsdangerous,click,pyjnius,libiconv,libffi

# ===== 图标 =====
icon.filename = icon.png
presplash.filename = presplash.png
presplash.color = #1a1a2e

# ===== 竖屏 =====
orientation = portrait
fullscreen = 0

# ===== 权限 =====
android.permissions = INTERNET

# ===== 安全配置 =====
android.meta_data =
    android:usesCleartextTraffic="true"
    android:allowBackup="false"

# ===== Android 构建环境 =====
android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21

# ===== Gradle =====
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# ===== 输出 APK =====
android.aab = False
android.release_artifact = apk
p4a.branch = master

# ===== 体积优化 =====
p4a.archs = arm64-v8a,armeabi-v7a

# Flask 需要 json，保留；其他可裁剪
android.exclude_pythonlib =
    idlelib,
    lib2to3,
    test,
    tests,
    tkinter,
    turtle,
    sqlite3,
    pydoc_data,
    ensurepip,
    venv,
    curses,
    email,
    mimetypes,
    xmlrpc,
    distutils,
    configparser,
    argparse,
    gettext,
    locale,
    optparse,
    pdb,
    profile,
    pstats,
    timeit,
    trace,
    tracemalloc,
    typing,
    unittest,
    zipapp,
    compileall,
    dis,
    inspect,
    pickletools

exclude_patterns =
    **/test/*,
    **/tests/*,
    **/*.pyc,
    **/__pycache__/*,
    **/*.md,
    **/*.txt,
    **/docs/*

android.debuggable = False

[buildozer]
log_level = 1
warn_on_root = 1
