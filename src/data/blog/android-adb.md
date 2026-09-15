---
title: "Android Debug Bridge (ADB)"
slug: android-adb
category: notes
format: cheatsheet
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-15T00:00:00+03:00
description: "The command reference for adb: connecting, shells, file transfer, package management, starting components, logcat, dumpsys, and the port forwarding that every other tool depends on."
---

ADB is the channel between your machine and the device, and pretty much everything else in mobile testing runs through it one way or another. Frida pushes its server over ADB. Burp reaches the device through an ADB tunnel. Even pulling an app's database is just one command.

## How It Works

ADB has three pieces:

- **Client**: the `adb` command you type. It runs on your machine and exits after sending its request.
- **Server**: a background process on your machine, listening on TCP 5037. It tracks which devices are attached and routes commands to them. It starts itself on the first `adb` command.
- **Daemon (`adbd`)**: runs on the device and executes what arrives.

So `adb shell ls` is the client handing the request to the local server, the server picking a device, and `adbd` running `ls` there.

The server holds an exclusive claim on connected devices. Android Studio and a second ADB installation will fight over them. When adb starts misbehaving, `adb kill-server` is the first thing to try.

## Connecting

The device must have **USB debugging** enabled in Developer options. The first connection prompts on the device to trust your machine's key; accept it, or the device shows as `unauthorized`.

```bash
adb devices -l            # list attached devices, with model and transport
adb kill-server           # stop the local server
adb start-server          # start it again
adb get-state             # device, offline, or unknown
adb wait-for-device       # block until a device is ready (useful after reboot)
```

### Targeting One Device

Hook up a second device and every command below fails with `more than one device/emulator`. Three flags tell adb which one you mean:

```bash
adb -d <command>              # the single USB device
adb -e <command>              # the single emulator
adb -s <serial> <command>     # a specific device, by the serial from adb devices
```

Use `-s` by default. The serial is the first column of `adb devices`, for example `emulator-5554`.

### Over Wi-Fi

Useful when the USB port is occupied, or when the app misbehaves while tethered.

```bash
# Android 11 and later: pair once using Developer options > Wireless debugging
adb pair <device-ip>:<pairing-port>
adb connect <device-ip>:<port>

# Older devices, over USB first
adb tcpip 5555
adb connect <device-ip>:5555

adb disconnect <device-ip>:5555
```

Anyone on the network can reach an open `adb tcpip` port. Turn it off when you are done.

## Shell

```bash
adb shell                              # interactive shell on the device
adb shell <command>                    # run one command and return
adb shell "ls -la /data/data/"         # quote anything with device-side globs or pipes
```

Anything with a glob or pipe in it needs quotes. Without them, your shell expands it on your own machine and adb never sees it.

### Root

```bash
adb root                  # restart adbd as root (userdebug builds only)
adb unroot                # restart it as shell again
adb shell su -c 'id'      # Magisk-rooted device: elevate per command
adb remount               # remount /system and friends read-write
```

`adb root` and `adb shell su -c` are not interchangeable. The first makes the whole ADB session root, so `adb pull` of a protected file works. The second elevates one command inside the shell, and `adb pull` still runs as `shell`.

## Files

```bash
adb push <local> <remote>          # machine to device
adb pull <remote> <local>          # device to machine

# The important paths
adb pull /data/data/<package>/ ./loot/     # app private data, needs root
adb push payload.apk /sdcard/Download/     # shared storage, no root needed
```

| Path | Holds |
|---|---|
| `/data/data/<package>/` | Private app data: `databases/`, `shared_prefs/`, `files/`, `cache/` |
| `/data/app/` | Installed APKs |
| `/sdcard/`, `/storage/emulated/0/` | Shared storage, world-readable |
| `/data/local/tmp/` | World-writable and executable, where you stage tools like the Frida server |

`/data/local/tmp/` is where you put binaries you want to run on the device. The `shell` user can write to it, and unlike `/sdcard/`, files there can be executed.

## Packages

```bash
adb install app.apk                    # install
adb install -r app.apk                 # reinstall, keeping data
adb install -g app.apk                 # grant all runtime permissions up front
adb install-multiple base.apk split_*.apk   # split APKs, from an app bundle

adb uninstall <package>
adb uninstall -k <package>             # remove the app, keep data and cache
```

### Finding Things

```bash
adb shell pm list packages             # every package
adb shell pm list packages -3          # third-party only, which is what you want
adb shell pm list packages -f          # with the APK path for each
adb shell pm list packages | grep -i <name>

adb shell pm path <package>            # where its APK lives
adb shell pm clear <package>           # wipe its data back to first-launch state
adb shell pm disable-user <package>    # disable without uninstalling
```

Pulling an app off a device, which is how most assessments start:

```bash
adb shell pm path com.example.app
# package:/data/app/~~abc==/com.example.app-xyz==/base.apk
adb pull /data/app/~~abc==/com.example.app-xyz==/base.apk
```

If `pm path` returns several lines, the app ships as split APKs. Pull all of them.

### Inspecting

```bash
adb shell dumpsys package <package>
```

It prints the requested and granted permissions, every exported component, the signing certificate, the install source, and the version. Use it to check whether an activity is exported without opening the manifest.

```bash
adb shell dumpsys package <package> | grep -A5 "requested permissions"
adb shell dumpsys activity activities    # the current activity stack
adb shell dumpsys window | grep mCurrentFocus   # what is on screen right now
```

## Starting Components

Exported components are the main way into an app from outside, and `am` is how you reach them by hand.

```bash
# Start an activity by component name
adb shell am start -n <package>/<activity>
adb shell am start -n com.example.app/.MainActivity

# With an intent action, data URI, and extras
adb shell am start -a android.intent.action.VIEW -d "https://example.com"
adb shell am start -n com.example.app/.DeepLinkActivity \
  -d "myapp://profile/1" \
  --es token "value" --ei count 3 --ez debug true

# Services and broadcasts
adb shell am startservice -n <package>/<service>
adb shell am broadcast -a com.example.ACTION --es key value

# Content providers
adb shell content query --uri content://com.example.provider/items
```

Extras are typed: `--es` string, `--ei` int, `--ez` boolean, `--ef` float, `--el` long.

```bash
adb shell am force-stop <package>     # kill it
adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1   # launch without knowing the activity name
```

## Logs

```bash
adb logcat                       # everything, which is too much
adb logcat -c                    # clear the buffer first, always do this
adb logcat -d                    # dump what is buffered and exit
adb logcat > log.txt

# Filter by tag and priority: V D I W E F, S silences
adb logcat "MyAppTag:V" "*:S"

# Filter by the app's own process
adb logcat --pid=$(adb shell pidof -s com.example.app)

adb logcat -b crash              # the crash buffer
```

Clear, reproduce, read. Apps leak tokens, keys, and full request bodies into logcat more often than they should, and a buffer full of system noise hides it.

## Port Forwarding

```bash
# Device port reachable on your machine
adb forward tcp:27042 tcp:27042        # the Frida server
adb forward tcp:8080 tcp:8080

# Your machine's port reachable on the device
adb reverse tcp:8080 tcp:8080          # the device's 8080 becomes your Burp listener

adb forward --list
adb reverse --list
adb forward --remove-all
```

`adb reverse` gives the device a route to a service on your machine even when the two are not on the same network, which is how you point a physical device at a proxy running on your laptop.

## Device State

```bash
adb shell getprop                              # every system property
adb shell getprop ro.build.version.release     # Android version
adb shell getprop ro.build.version.sdk         # API level
adb shell getprop ro.product.cpu.abi           # arm64-v8a, x86_64, and so on

adb shell settings list global
adb shell settings put global http_proxy <host>:<port>
adb shell settings delete global http_proxy
```

`ro.product.cpu.abi` decides which build of the Frida server, or any other native tool, you push to the device.

## Capture

```bash
adb shell screencap -p /sdcard/shot.png && adb pull /sdcard/shot.png
adb exec-out screencap -p > shot.png            # straight to the machine

adb shell screenrecord /sdcard/demo.mp4         # ctrl-c to stop, 3 minute cap
adb pull /sdcard/demo.mp4
```

`exec-out` skips the device's shell, so binary output arrives unmangled. `adb shell` corrupts it on some platforms by translating line endings.

## Reboots

```bash
adb reboot
adb reboot bootloader     # fastboot mode, for flashing
adb reboot recovery
```

## When It Will Not Connect

| Symptom | Fix |
|---|---|
| `device unauthorized` | Accept the RSA prompt on the device. If it never appears, revoke USB debugging authorizations in Developer options and reconnect. |
| `no devices/emulators found` | `adb kill-server && adb start-server`. On Linux, check the udev rules; the device may need a rule for its vendor id. |
| `device offline` | Unplug, replug, then `adb kill-server`. Often a cable or hub problem. |
| `more than one device/emulator` | Target one with `-s <serial>`. |
| `adbd cannot run as root in production builds` | The image is a `user` build. See [Android Lab Setup](/collections/mobile/android-lab-setup) for picking one you can root. |
| Commands hang forever | Android Studio is holding the device. Close it, or kill its ADB server. |
