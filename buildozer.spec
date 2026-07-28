[app]
title = LanPlayMonitor
package.name = monitor
package.domain = com.lanplay
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.include_patterns = image/*
version = 1.0.0

# ===== WebView 配置 =====
p4a.bootstrap = webview
p4a.port = 5000
# ========================

icon.filename = icon.png
fullscreen = 0
orientation = portrait
entrypoint = main.py

requirements = python3

android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# 强制使用特定架构
android.archs = arm64-v8a

android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO

exclude_patterns = **/test/*, **/tests/*
android.aab = False

# 签名配置
android.release = False
android.sign = True
android.sign_key_path = ~/.android/debug.keystore
android.sign_key_alias = androiddebugkey
android.sign_store_password = android
android.sign_key_password = android

[buildozer]
log_level = 2
warn_on_root = 1