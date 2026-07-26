[app]

# ==================== 应用基本信息 ====================
title = LanPlayMonitor
package.name = monitor
package.domain = com.lanplay
source.dir = .
source.include_exts = py,kv,html,json,css,js
entrypoint = main.py
version = 1.0.0

# ==================== Python 依赖 ====================
# ✅ 极简依赖，只保留必须项
requirements = python3,kivy,pyjnius,libiconv,libffi

# ==================== 图标 & 启动图 ====================
icon.filename = icon.png
presplash.filename = presplash.png
presplash.color = #1a1a2e
android.icon_foreground_filename = icon_foreground.png
android.icon_background_filename = icon_background.png
android.icon_background_color = #1a1a2e

# ==================== 屏幕方向 ====================
orientation = portrait
fullscreen = 0

# ==================== Android 权限 ====================
android.permissions = INTERNET

# ==================== Android 安全配置 ====================
android.meta_data =
    android:usesCleartextTraffic="true"
    android:allowBackup="false"

# ==================== Android 构建环境 ====================
android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21

# ==================== Gradle 配置 ====================
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# ✅ 用 master 分支（不要用 develop）
p4a.branch = master

# ==================== 输出格式 ====================
# ✅ 只输出 APK，不碰 AAB
android.aab = False
android.release_artifact = apk

# ==================== APK 体积优化 ====================
p4a.archs = arm64-v8a,armeabi-v7a

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
