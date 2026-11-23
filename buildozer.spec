[app]
title = Flipper Companion
package.name = flippercompanion
package.domain = org.example
source.dir = .
source.include_exts = py,png,ttf,kv,atlas
source.exclude_dirs = .github,bin,.buildozer
version = 0.1
requirements = python3,kivy==2.3.0
orientation = landscape
fullscreen = 1

android.api = 34
android.minapi = 30
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
