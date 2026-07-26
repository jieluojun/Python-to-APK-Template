[app]
title = 应用名
package.name = 包名
package.domain = org.test#域名
source.dir = .#根目录下工作
source.include_exts = py,png,jpg,kv,atlas,ttf#打包文件
source.include_patterns = image/*#文件夹内文件
version = 114.514#版本
#依赖
requirements = python3,kivy,kivymd,libiconv,libffi
#icon.filename = 应用图标
#presplash.filename = 加载界面图片
#fullscreen = 0
#orientation = portrait
entrypoint = main.py#主程序
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
android.permissions = INTERNET#构筑需要网络权限

[buildozer]
log_level = 2
warn_on_root = 1
