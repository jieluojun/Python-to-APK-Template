[app]
title = LanPlayMonitor
package.name = monitor
package.domain = com.lanplay
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = image/*
version = 1.0.0
# 依赖
requirements = python3,kivy,kivymd,openssl,certifi,libiconv,libffi
icon.filename = icon.png
# presplash.filename = presplash.png # 启动界面图片
# 0=不启用全屏，1=启用全屏
fullscreen = 0
# 应用竖屏
orientation = portrait
entrypoint = main.py
android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 33
android.minapi = 21
android.ndk = 25b
exclude_patterns = **/test/*, **/tests/*
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
android.sdk = 33
android.ndk_api = 21
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64
android.permissions = INTERNET
# 强制构建APK，然而并没有用
android.aab = False
# 签名配置
android.keystore = /home/runner/work/a/b/com.lanplay.monitor.keystore
android.keystore_storepass = android
android.keystore_keypass = android
android.keystore_alias = com.lanplay.monitor

[buildozer]
log_level = 2
warn_on_root = 1