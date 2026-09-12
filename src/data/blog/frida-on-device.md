---
author: Kayra
pubDatetime: 2026-07-06T00:00:00Z
title: "Frida on Device: Rooted Android and Jailbroken iOS"
slug: "frida-on-device"
description: "Getting frida-server onto a rooted Android or jailbroken iOS device: the client/server model, per-platform install, the Gadget path for stock devices, and the version-match gotcha that breaks everyone's first attempt."
tags: ["frida", "mobile", "security", "cheatsheet"]
category: notes
draft: true
featured: false
---

Frida is a dynamic instrumentation toolkit: a client on your workstation drives an agent on the device, so you can hook and rewrite a running app. On iOS it is also how you decrypt a store-downloaded app before static analysis, since `frida-ios-dump` reads the code out of memory after the OS has decrypted it. This is a setup reference for getting Frida running on a rooted Android or jailbroken iOS device. For where it sits in a full assessment, see [Mobile Security Testing Foundations](/posts/mobile-security-testing-foundations).

## How Frida Fits Together

Frida is two pieces that talk over USB:

- **The client**, on your workstation: the `frida`, `frida-ps`, and `frida-trace` command-line tools, plus the Python and JavaScript bindings.
- **The agent**, on the device: on a rooted or jailbroken device this is `frida-server`, a binary running as root that can attach to any process. On a stock device you cannot run it, so you embed **Frida Gadget**, a library, into the one app you want to instrument.

The rooted/jailbroken path (full `frida-server`) is what the rest of this reference sets up. The Gadget path is covered at the end for when you have no root or jailbreak.

## Install the Client

The client is the same on every platform:

```bash
pip install frida-tools     # installs frida, frida-ps, frida-trace, frida-ls-devices
frida --version             # note this version; the device agent must match it exactly
```

> **Gotcha:** The client and the device agent must be the **same version**. Almost every "it won't connect" problem is a version mismatch between `frida-tools` here and `frida-server` on the device. Read `frida --version` now and match the server to it.

## Android (Rooted)

1. **Read the device CPU ABI**, so you download the right server build:

```bash
adb shell getprop ro.product.cpu.abi     # e.g. arm64-v8a, armeabi-v7a, x86_64
```

2. **Download the matching `frida-server`** from the Frida GitHub releases: pick the build whose version equals your `frida --version` and whose architecture matches the ABI above (for `arm64-v8a`, the `android-arm64` build). It ships compressed:

```bash
unxz frida-server-<version>-android-arm64.xz
```

3. **Push it to the device and run it as root:**

```bash
adb push frida-server-<version>-android-arm64 /data/local/tmp/frida-server
adb shell "chmod 755 /data/local/tmp/frida-server"
adb shell "su -c '/data/local/tmp/frida-server &'"
```

4. **Verify from the workstation:**

```bash
frida-ps -U     # -U = USB device; should list running processes
```

## iOS (Jailbroken)

On iOS you do not push a binary by hand. Frida ships as a package for the on-device package manager, which installs the server and launches it on boot.

1. **Add Frida's repository** in Sileo or Cydia: `https://build.frida.re`.
2. **Install the "Frida" package** from that repo. It registers `frida-server` as a daemon, so it is already running after install.
3. **Verify from the workstation** with the device connected over USB:

```bash
frida-ps -U
```

> **Note:** Rootless jailbreaks (palera1n, Dopamine) work the same way. Install through Sileo from the same repository; the package is maintained for the rootless layout. If `frida-ps -U` does not see the device, make sure the USB connection is trusted and, on Linux, that `usbmuxd` is running.

Once `frida-ps -U` lists processes, `frida-ios-dump` will work, which is the step that gives you a decrypted IPA for the [iOS security-testing checklist](/posts/mobile-app-security-testing-ios).

## Without Root or Jailbreak: Frida Gadget

On a stock device you cannot run `frida-server`, so you inject **Frida Gadget** into a single app. This repackages that app.

- **Android:** let `objection` patch the APK for you. It adds the gadget library and the load code, then re-signs the result:

```bash
objection patchapk -s target.apk     # produces target.objection.apk, then install it
```

- **iOS:** inject `FridaGadget.dylib` into the app binary and re-sign the bundle with a provisioning profile you control (with a tool such as `insert_dylib` plus `codesign`, or a re-signing wrapper). This is more involved than the Android path.

> **Note:** The Gadget path changes the app's binary and signature. Keep the patched build for instrumentation only, and report static findings against the original signed build, for the same reason you never analyze a pinning-disabled build (see the two-binaries note in [Mobile Security Testing Foundations](/posts/mobile-security-testing-foundations)).

## Verify and Troubleshoot

- `frida-ls-devices`: confirm the workstation sees the device at all.
- `frida-ps -U`: list processes on the USB device. Success here means client and agent are talking.
- **Version errors** from `frida-ps -U` mean the server and client versions differ. Re-check `frida --version` and install the matching `frida-server`.
- **No device found:** on Android confirm `adb devices` shows it; on iOS confirm the pairing is trusted and `usbmuxd` (or `iproxy` for a manual tunnel) is available.
