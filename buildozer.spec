[app]

# ==================== 应用基本信息 ====================

# 应用在手机桌面上显示的名字（支持中文）
title = LanPlayMonitor

# 包名后半段，最终包名为：com.lanplay.monitor
package.name = monitor

# 包名前半段（反向域名格式，不要用 org.test）
package.domain = com.lanplay

# 项目根目录（当前目录）
source.dir = .

# 需要打包进 APK 的文件类型
# py = 代码，kv = Kivy 布局，html/css/js/json = WebView 页面
source.include_exts = py,kv,html,json,css,js

# 应用入口文件（Kivy WebView 壳）
entrypoint = main.py

# 应用版本号
version = 1.0.0

# ==================== Python 依赖 ====================

# python3        : 运行时
# kivy           : UI 框架
# pyjnius        : 调用 Android 原生 WebView
# libiconv/libffi: Kivy 底层依赖
requirements = python3,kivy,pyjnius,libiconv,libffi

# ==================== 图标 & 启动图 ====================

# 桌面图标
icon.filename = icon.png

# 启动页（黑屏过渡画面）
presplash.filename = presplash.png

# 启动页背景色（深蓝黑，防白闪）
presplash.color = #1a1a2e

# Android 8+ 自适应图标前景
android.icon_foreground_filename = icon_foreground.png

# 自适应图标背景
android.icon_background_filename = icon_background.png
android.icon_background_color = #1a1a2e

# ==================== 屏幕方向 ====================

# 强制竖屏（非常重要）
orientation = portrait

# 不全屏，保留状态栏（调试阶段更安全）
fullscreen = 0

# ==================== Android 权限 ====================

# INTERNET：WebView + HTTP Server 必须
android.permissions = INTERNET

# ==================== Android 安全配置 ====================

# 允许 HTTP 明文流量（127.0.0.1:5000 是 HTTP）
android.meta_data =
    android:usesCleartextTraffic="true"

# ==================== Android 构建环境 ====================

# 自动同意 SDK License（CI 必须）
android.accept_sdk_license = True

# 最低支持的 Android 版本（Android 5.0）
android.allow_api_min = 21
android.minapi = 21

# 编译 SDK 版本（Android 13）
android.api = 33
android.sdk = 33

# NDK 版本（稳定版，不要乱改）
android.ndk = 25b
android.ndk_api = 21

# ==================== Gradle 配置 ====================

# Gradle 下载地址（固定版本，防止 CI 随机失败）
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip

# Android Gradle Plugin 版本
android.gradle_plugin = 7.4.2

# Gradle 依赖声明
p4a.gradle_dependencies = gradle:7.6.4

# 使用 SDL2 作为 Kivy 的 Android 后端
p4a.bootstrap = sdl2

# 强制使用 Java 17（Ubuntu CI 环境）
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# 指定 python-for-android 分支（稳定）
p4a.branch = develop

# ==================== 输出格式控制 ====================

# ✅ 强制输出 APK（不是 AAB）
# ❌ 千万不要写 android.release = True（那是 AAB 开关）
android.aab = False

# ==================== APK 体积优化 ====================

# 只保留 ARM 真机架构（去掉 x86 模拟器，省 30%~40%）
p4a.archs = arm64-v8a,armeabi-v7a

# 裁剪不需要的 Python 标准库（大幅减小体积）
# ⚠️ 保留 http.* / json，否则 WebView / HTTP Server 会崩
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

# 排除非必要文件（进一步减小体积）
exclude_patterns =
    **/test/*,
    **/tests/*,
    **/*.pyc,
    **/__pycache__/*,
    **/*.md,
    **/*.txt,
    **/docs/*

# 关闭调试符号（Release 包不需要）
android.debuggable = False

# ==================== Release 签名 ====================
# 以下内容由 GitHub Actions 自动注入，本地不需要写
# android.keystore = com.lanplay.monitor.keystore
# android.keystore_storepass = android
# android.keystore_keypass = android
# android.keystore_alias = com.lanplay.monitor

[buildozer]

# 日志级别：1 = 详细（调试阶段推荐），2 = 正常
log_level = 1

# 如果 source.dir 是根目录，发出警告
warn_on_root = 1
