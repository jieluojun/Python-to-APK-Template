[app]
title = LanPlayMonitor
package.name = monitor
package.domain = com.lanplay
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,xml,json,txt
exclude_patterns = **/test/*, **/tests/*, **/__pycache__/*, **/*.pyc
version = 0.0.1
requirements = python3==3.10.16,kivy==2.3.0,kivymd,libiconv,libffi
icon.filename = icon.png
fullscreen = 0
orientation = portrait
entrypoint = main.py

# ============================================================
# Android 编译配置
# ============================================================
android.accept_sdk_license = True
android.sdk = 33
android.api = 33
android.minapi = 21
android.allow_api_min = 21
android.ndk = 25b
android.ndk_api = 21

# ✅ Gradle 7.5 稳定版（CI 友好）
android.gradle_download = https://services.gradle.org/distributions/gradle-7.5-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.5
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/temurin-17-jdk-amd64 --no-daemon --parallel -Dorg.gradle.configureondemand=true

p4a.bootstrap = sdl2

# ✅ 只打单架构，速度翻倍（v8a 覆盖 95% 设备）
android.aab = False
android.archs = arm64-v8a

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# ============================================================
# Release 签名配置
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
