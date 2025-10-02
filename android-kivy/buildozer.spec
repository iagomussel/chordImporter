[app]

# App title and package info
title = ChordImporter
package.name = chordimporter
package.domain = com.musical

# Version
version = 0.1.0

# Application source
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

# Entry point
source.main = main.py

# Requirements - all Python packages needed
requirements = python3,kivy==2.3.0,numpy,scipy,requests,beautifulsoup4,audiostream,pyjnius

# Icon
icon.filename = %(source.dir)s/assets/icon.png

# Presplash (optional)
#presplash.filename = %(source.dir)s/assets/presplash.png

# Orientation - can be portrait, landscape, or all
orientation = portrait

# Fullscreen mode
fullscreen = 0

# Android specific
android.permissions = INTERNET,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MODIFY_AUDIO_SETTINGS
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 31
android.accept_sdk_license = True
android.arch = armeabi-v7a,arm64-v8a

# Android application name
android.appname = ChordImporter

# Android entrypoint
android.entrypoint = org.kivy.android.PythonActivity

# Android app theme
android.apptheme = "@android:style/Theme.NoTitleBar"

# List of Java files to add to the project
#android.add_src = 

# List of Java libraries to include
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# Gradle dependencies
#android.gradle_dependencies = 

# Java classes to add
#android.add_activities = com.example.ExampleActivity

# Skip byte compile for performance
android.no-byte-compile-python = False

# Android logcat filters
android.logcat_filters = *:S python:D

# Copy files from app to /sdcard/
#android.copy_libs = 1

# Android wakelock
#android.wakelock = False

# Android meta-data
#android.meta_data = 

# Add custom Java code
#android.add_jars = foo.jar,bar.jar,path/to/more/*.jar

[buildozer]

# Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# Display warning if buildozer is run as root
warn_on_root = 1

# Build output directory
build_dir = ./.buildozer

# Specification file location
spec = buildozer.spec

