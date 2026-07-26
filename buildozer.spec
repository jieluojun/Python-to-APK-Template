[app]
# 应用标题(可中文)
title = LanPlay Monitor
# 包名 = com.lanplay.monitor (domain + name)
package.name = monitor
# 域名反转格式(不能用 org.test 才能打 release)
package.domain = com.lanplay
# 工作目录
source.dir = .
# 需要打包的文件类型(加入 ico 和 xml 适配新图标)
source.include_exts = py,png,jpg,kv,atlas,xml,ico
# 主程序入口
entrypoint = main.py
version = 1.0.0

# 依赖库(python3 + kivy + kivymd + 打包必需的系统库)
requirements = python3,kivy,kivymd,libiconv,libffi

# ===== 应用图标 & 启动图 =====
# 应用图标(正方形 PNG,推荐 1024x1024,放在项目根目录)
icon.filename = icon.png
# 启动图(可选,放在项目根目录)
presplash.filename = presplash.png
# 启动图背景色(可选,#RRGGBB)
presplash.color = #1a1a2e

# ===== Android 自适应图标(Adaptive Icon) =====
#  foreground: 带透明背景的前景图层(108x108 dp 安全区内的内容)
#  background: 背景图层(纯色 PNG 或 xml 渐变)
android.icon_foreground_filename = icon_foreground.png
android.icon_background_filename = icon_background.png
# 自适应图标背景色(当没有 background 图时使用)
android.icon_background_color = #1a1a2e

# 全屏/横竖屏(按需打开)
# fullscreen = 0
# orientation = portrait

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

# 强制输出 APK(不设或设 False 都可能被打成 AAB)
android.release = True
android.aab = False

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
