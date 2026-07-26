[app]

# ===== 基本信息 =====
title = LanPlay Monitor
package.name = lanplaymonitor
package.domain = org.lanplay
source.dir = .
source.include_exts = py,kv,html,json,css,js,md,txt
entrypoint = main.py
version = 1.0.0

# ===== Python 依赖 =====
# Kivy（提供稳定构建环境）+ Flask（你的监控服务）
requirements = python3,kivy,flask,jinja2,markupsafe,werkzeug,itsdangerous,click,pyjnius,libiconv,libffi

# ===== 图标 =====
icon.filename = icon.png
presplash.filename = presplash.png
presplash.color = #1a1a2e
android.icon_foreground_filename = icon_foreground.png
android.icon_background_filename = icon_background.png
android.icon_background_color = #1a1a2e

# ===== 竖屏 =====
orientation = portrait
fullscreen = 0

# ===== 权限 =====
android.permissions = INTERNET
android.meta_data = android:usesCleartextTraffic="true"
android.allow_backup = 0

# ===== Android 构建环境 =====
android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 34
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21

# ===== Gradle =====
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# ===== 输出 APK（不是 AAB！）=====
android.aab = False
android.release_artifact = apk

# ===== p4a 配置 =====
p4a.branch = master
p4a.archs = arm64-v8a,armeabi-v7a

# ===== 体积优化 =====
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

# ===== 签名（由 CI 注入）=====
# android.keystore = com.lanplay.monitor.keystore
# android.keystore_storepass = android
# android.keystore_keypass = android
# android.keystore_alias = com.lanplay.monitor

[buildozer]
log_level = 2
warn_on_root = 1
