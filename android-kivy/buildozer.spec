[app]
# App metadata
title = ChordImporter Tuner
package.name = chordimporter
package.domain = com.iagomussel
source.dir = .
version = 0.1.0

# Kivy app entrypoint
fullscreen = 0
orientation = portrait
log_level = 2

# Keep Android-friendly dependencies to avoid legacy NDK/fortran
# IMPORTANT: Do NOT include scipy on Android (requires LAPACK + LEGACY_NDK r21e)
requirements = python3, kivy==2.3.0, numpy, requests, beautifulsoup4, pyjnius, audiostream

# Permissions
android.permissions = RECORD_AUDIO, INTERNET

# Android APIs (match the CI image defaults)
android.api = 31
android.minapi = 21

# Java / SDK settings
android.sdk = 31

# NDK is managed by p4a/buildozer; avoid legacy NDK by keeping requirements simple

# Packaging
icons = 

# Include/Exclude patterns
android.add_src = main.py

[buildozer]
log_level = 2
warn_on_root = 0

