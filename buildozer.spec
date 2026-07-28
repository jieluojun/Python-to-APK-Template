[app]
title = LanPlayMonitor
package.name = monitor
package.domain = com.lanplay
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.include_patterns = image/*
version = 1.0.1
# 依赖
#requirements = python3
requirements = python3==3.11.12
icon.filename = icon.png
# presplash.filename = presplash.png # 启动界面图片
# 0=不启用全屏，1=启用全屏
fullscreen = 0
# 应用竖屏
orientation = portrait
entrypoint = main.py
# ==================== 关键配置 ====================
# 使用 webview 引导程序，让应用内嵌浏览器直接渲染网页
p4a.bootstrap = webview
# 指定 webserver 端口，需与 Python 脚本中监听的端口保持一致
p4a.port = 5000
# ================================================
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
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64
# 已添加：所有文件访问权权限及 Android 13+ 照片和视频读取权限
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES, READ_MEDIA_VIDEO, READ_MEDIA_AUDIO
# 强制构建APK，然而并没有用
android.aab = False
# 签名配置
# android.release_keystore = /home/runner/keystore.jks
# android.release_keyalias = %(ENV_RELEASE_KEYALIAS)s
# android.release_keystore_passwd = %(ENV_RELEASE_KEYSTORE_PASSWD)s
# android.release_keyalias_passwd = %(ENV_RELEASE_KEYALIAS_PASSWD)s

[buildozer]
log_level = 2
warn_on_root = 1
