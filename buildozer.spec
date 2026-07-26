[app]
# 应用标题(可中文)
title = LanPlay Monitor
# 包名 = com.lanplay.monitor (domain + name)
package.name = monitor
# 域名反转格式(不能用 org.test 才能打 release)
package.domain = com.lanplay
# 工作目录
source.dir = .
# 需要打包的文件类型
source.include_exts = py,kv
# 主程序入口
entrypoint = main.py
version = 1.0.0

# ===== 依赖(精简版) =====
# 只保留最小依赖,去掉不必要的库
requirements = python3,kivy,libiconv,libffi

# ===== 应用图标 & 启动图 =====
icon.filename = icon.png
presplash.filename = presplash.png
presplash.color = #1a1a2e

# 自适应图标
android.icon_foreground_filename = icon_foreground.png
android.icon_background_filename = icon_background.png
android.icon_background_color = #1a1a2e

# 全屏/横竖屏
# fullscreen = 0
orientation = portrait

# ===== Android 构建参数 =====
android.accept_sdk_license = True
android.allow_api_min = 21
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.ndk_api = 21

# Gradle
android.gradle_download = https://services.gradle.org/distributions/gradle-7.6.4-all.zip
android.gradle_plugin = 7.4.2
p4a.gradle_dependencies = gradle:7.6.4
p4a.bootstrap = sdl2
p4a.gradle_options = -Dorg.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64

# 网络权限
android.permissions = INTERNET

# 输出格式控制(关键: android.release 会触发 AAB 输出!)
# android.aab = False → 告诉 p4a 打 APK 不是 AAB
# buildozer android apk → release.yml 里用这个命令明确指定
android.aab = False
# 不用 android.release = True (那是 AAB 的开关)

# ===== 🔥 APK 体积优化(核心) =====

# 1. 移除未使用的 Python 标准库模块(大幅减小体积)
#    常见可移除的: tests, tkinter, turtle, sqlite3(不用数据库时),
#    email(不发邮件时), xmlrpc(不用RPC时), curses(终端用不到)
android.add_packageroot =
android.exclude_pythonlib = idlelib,lib2to3,test,tests,tkinter,turtle,sqlite3,pydoc_data,ensurepip,venv,curses,email,mimetypes,http,urllib,xmlrpc,distutils,configparser,argparse,gettext,locale,logging,optparse,pdb,profile,pstats,timeit,trace,tracemalloc,typing,unittest,venv,zipapp

# 2. 排除不需要的文件(减少 assets 体积)
exclude_patterns = **/test/*, **/tests/*, **/*.pyc, **/__pycache__/*, **/*.md, **/*.txt, **/docs/*, **/examples/*, **/demos/*

# 3. 只打包必要的依赖(如果不用 KivyMD 就去掉)
#    如果用了 KivyMD,取消下面一行的注释
# requirements = python3,kivy,kivymd,libiconv,libffi

# 4. 不打包 Android x86 架构(只保留 arm64-v8a 和 armeabi-v7a)
#    x86 模拟器用,真机不需要,去掉能省 ~30%
p4a.archs = arm64-v8a,armeabi-v7a

# 5. 启用 ProGuard / R8 代码混淆压缩(减小 Java 层体积)
android.enable_obfuscation = True

# 6. 移除调试符号(Release 不需要)
android.debuggable = False

# 7. 压缩级别调最高
p4a.compilepythondir = True

# 8. 不生成 unaligned APK(减少中间产物)
p4a.unaligned_apk = False

# ===== Release 签名配置 =====
# 签名由 GitHub Actions 通过环境变量注入
# android.keystore = com.lanplay.monitor.keystore
# android.keystore_storepass = android
# android.keystore_keypass = android
# android.keystore_alias = com.lanplay.monitor

[buildozer]
log_level = 2
warn_on_root = 1
