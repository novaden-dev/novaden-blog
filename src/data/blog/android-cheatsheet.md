---
author: Kayra
pubDatetime: 2026-06-02T00:00:00Z
title: "Android Pentesting Cheat Sheet"
slug: "android-cheatsheet"
description: "Quick-reference commands for Android pentesting: adb device interaction, apktool, APK signing, and jadx decompilation."
tags: ["android", "security", "cheatsheet", "notes"]
draft: false
featured: false
---

> **Note:** These are working notes and still in progress.

A living quick-reference for the commands used when pentesting Android apps. For the model behind any of this (activities, intents, attack surface, RE methodology), see [Android Pentesting](/posts/android-pentesting).

## Device Setup

Enable developer access on the phone before connecting it to `adb`:

1. Go to **Software Information** and tap the **build number** 7 times.
2. In **Developer Options**, enable **USB Debugging**.

`adb` has three parts: a client and a server that run on your computer, and a daemon that runs on the device.

## ADB

### Device Interaction

```bash
# List the devices connected to the computer
adb devices

# Get a shell on the device
adb shell

# Run a command against a specific device
adb -d <device-id> <command>

# Push a file from computer to device (e.g. /sdcard/ is the internal storage)
adb push <local-file-on-computer> <remote-path-on-device>

# Pull a file from the device to the computer
adb pull <file-path-on-device> <local-path-on-computer>
```

You can also browse files through Android Studio's **Device Explorer** instead of `adb push`/`pull`.

### Packages

```bash
# Install an APK onto the device
adb install <path-to-apk>

# Uninstall an app from the device
adb uninstall <app-package-name>

# List all installed packages
adb shell pm list packages

# List only third-party packages
adb shell pm list packages -3

# Clear the data of a specific app
adb shell pm clear <app-package-name>

# Show package info: permissions, exported activities, etc.
adb shell dumpsys package <app-package-name>

# Return the path of the APK for an application
adb shell pm path <app-package-name>
```

### Starting Activities

```bash
# Start an activity in a package
adb shell am start <app-package-name>/.<activity-name>

# Start an activity explicitly by component name
adb shell am start -n <app-package-name>/.<activity-name>
```

### Logs

```bash
# Show device logs in a given format (e.g. brief)
adb logcat -v <log-format>

# Show only MainActivity logs at verbose level, silence everything else
# Tag priority values: V, D, I, W, E, F, S
adb logcat "MainActivity:V *:S"
```

## apktool

`apktool` unpacks an APK into smali and repacks it.

```bash
# Decompile an APK
apktool d <path-to-apk>

# Repack an APK
apktool b
```

## Signing APKs

APKs are signed, and the signature is checked on update to confirm the APK came from the same origin. APKs repacked with `apktool` are unsigned, so you must sign them before installing.

```bash
# Generate a key to sign APKs with
keytool -genkey -v -keystore research.keystore -alias research_key -keyalg RSA -keysize 2048 -validity 10000

# Sign the APK with the generated key
jarsigner -verbose -keystore research.keystore app.apk research_key

# Align the APK on a 4-byte boundary (sometimes required, see errors below)
zipalign -f -p -v 4 repacked-raw.apk

# Newer signing scheme via apksigner
~/Android/Sdk/build-tools/35.0.0/apksigner sign --ks research.keystore --ks-key-alias research_key --out final-signed.apk repacked-final.apk
```

Common install errors and what they mean:

- `INSTALL_PARSE_FAILED_NO_CERTIFICATES`: something was wrong with the signature (you tried to install an unsigned APK, or chose the wrong algorithm). If the message mentions "No signature found in package of version 2 or newer", sign with `apksigner`.
- `INSTALL_FAILED_INVALID_APK: Failed to extract native libraries, res=-2`: edit `AndroidManifest.xml`, set `extractNativeLibs` to `true`, then repackage and re-sign.
- `INSTALL_FAILED_UPDATE_INCOMPATIBLE`: expected if the app was already installed, because it is now signed with a different key. Uninstall the existing app first.
- `Failed parse during installPackageLI`: happens with newer apps. Try an alternative signing method, such as `zipalign` or `apksigner`.

## jadx

`jadx` decompiles an APK back to readable Java.

```bash
# Open the GUI
jadx-gui

# Decompile an APK from the terminal
jadx <apk-path>
```

- When doing a global search, include resources too, since secrets are often stored there.
- `jadx` cannot analyze native (JNI) code. Use Ghidra for that, or run `strings` to pull out any useful information.
- You can export all decompiled files as a Gradle project (or other formats).
