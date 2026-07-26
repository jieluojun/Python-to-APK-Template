[app]
# 标题 (可中文)
title = LanPlayMonitor

# 包名
package.name = monitor

# 发布模式不能用 org.test
package.domain = com.lanplay

# 工作目录
source.dir = .

# 需要打包的文件类型
source.include_exts = py,png,jpg,jpeg,kv,atlas,xml,json,txt

# 排除测试文件
exclude_patterns = **/test/*, **/tests/*, **/__pycache__/*

# 版本号
version = 0.0.1

# 依赖库 (固定版本,避免CI拉到不兼容版本)
requirements = python3==3.9.16,kivy==2.3.0,kivymd==1.1.1,libiconv,libffi

# 图标
icon.filename = icon.png

# 启动图 (如有请取消注释)
# presplash.filename = presplash.png

# 全屏 / 方向
fullscreen = 0
orientation = portrait

# 主程序入口
entrypoint = main.py

# ============================================================
# Android 编译配置
# ============================================================

# 自动接受 SDK License (CI 必须)
android.accept_sdk_license = True

# SDK / API
android.sdk = 33
android.api = 33
android.minapi = 21
android.allow_api_min = 21

# NDK (r25b 稳定)
android.ndk = 25b
android.ndk_api = 21

# Gradle (7.5 + AGP 7.4.2 最稳)
android.gradle_download = https://services.gradle.org/distributions/gradle-7.5-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.5
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/temurin-17-jdk-amd64 --no-daemon -Dorg.gradle.configureondemand=true

# python-for-android
p4a.bootstrap = sdl2

# 强制 APK (不要 AAB)
android.aab = False

# 架构
android.archs = arm64-v8a,armeabi-v7a

# 网络权限 (LAN 监控类应用需要)
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# ============================================================
# Release 签名配置
# CI 中由 release.yml 自动生成 keystore
# ============================================================
android.keystore = %(source.dir)s/com.lanplay.monitor.keystore
android.keystore_alias = com.lanplay.monitor
android.keystore_storepass = android
android.keystore_keypass = android

# ============================================================
# Buildozer 自身配置
# ============================================================
[buildozer]
log_level = 2
warn_on_root = 1
