[app]
title = Flipper Companion
package.name = flippercompanion
package.domain = org.example
source.dir = .
source.include_exts = py,png,ttf,kv,atlas
source.exclude_dirs = .github,bin,.buildozer
version = 0.1
requirements = python3,kivy==2.3.0,pyjnius,usb4a,usbserial4a,pyserial
orientation = landscape
fullscreen = 1

android.api = 34
android.minapi = 30
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.p4a_whitelist = lib-dynload/
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
