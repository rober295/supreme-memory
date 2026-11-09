[app]
title = God-level upgrade
package.name = godlevelupgrade
package.domain = org.godlevel
source.dir = .
source.include_exts = py,kv,png,jpg,json,atlas
source.exclude_patterns = test_logic.py,.venv/*,.github/*
version = 2.6.0
requirements = python3,kivy,pyjnius,openssl,certifi
orientation = portrait
fullscreen = 0

# Android
android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
