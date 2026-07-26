[app]
# 应用标题(可中文)
title = LanPlayMonitor

# 包名 = com.lanplay.monitor (domain + name)
package.name = monitor

# 域名反转格式(不能用 org.test 才能打 release)
package.domain = com.lanplay

# 工作目录
source.dir = .

# 需要打包的文件类型
source.include_exts = py,png,jpg,kv,atlas

# 主程序入口
entrypoint = main.py

# 软件版本
version = 1.0.0

# 软件图标
icon.filename = icon.png

# 启动图
# presplash.filename = presplash.png

# 全屏/横竖屏(按需打开)
# fullscreen = 0
# orientation = portrait

# 依赖库(python3 + kivy + kivymd + 打包必需的系统库)
requirements = python3,kivy,kivymd,libiconv,libffi

# ===== Android 构建参数(不要乱改) =====
android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# Gradle(版本必须与 android.gradle_plugin 匹配)
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# 网络权限(监控类应用通常需要)
android.permissions = INTERNET

# ===== Release 签名配置 =====
# 签名由 GitHub Actions 通过环境变量注入,这里保持注释即可
# 本地手动签名再取消注释并填好路径
# android.keystore = com.lanplay.monitor.keystore
# android.keystore_storepass = android
# android.keystore_keypass = android
# android.keystore_alias = com.lanplay.monitor

# 排除测试文件
exclude_patterns = **/test/*, **/tests/*

[buildozer]
log_level = 2
warn_on_root = 1
