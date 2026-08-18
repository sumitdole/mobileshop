[app]

title = Shop Manager
package.name = shopmanager
package.domain = org.shopmanager

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0

# Pinned deliberately — kivymd 2.x uses a completely different widget API
# (Material Design 3 rewrite) that this codebase is NOT written against.
# Do not bump kivymd past the 1.1.x line without rewriting the UI code.
requirements = python3,kivy==2.2.1,kivymd==1.1.1,plyer,pillow

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/assets/icon.png

# No network, camera, contacts etc. needed — this app is fully offline.
android.permissions =

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
