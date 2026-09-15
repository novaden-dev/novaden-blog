---
title: "Android Lab Setup"
slug: android-lab-setup
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-15T00:00:00+03:00
description: "Setting up the Android testing lab: Android Studio and the SDK, an emulator you can actually root, a writable system partition, and the physical-device path when the emulator will not do."
---

Testing an Android app means reading its files, watching its traffic, and changing what it does while it runs. None of that works on a stock device. You need a device you fully control, which means root, and you need the SDK tools on your machine to talk to it.

Every other note in this handbook assumes the setup described here.

## What the Lab Needs

| Requirement | Why |
|---|---|
| Root access | Read `/data/data/<package>/`, write to the system certificate store, attach a debugger to any process. |
| A writable system partition | Installing a proxy CA as a system-trusted certificate. |
| ADB over USB or TCP | Every other tool is driven through it. |
| A resettable state | Snapshots, so a broken app or a bad patch costs seconds instead of an afternoon. |

An emulator gives you all four out of the box. Start with the emulator, and move to a physical device only if the app will not run on it.

## Emulator or Physical Device

| | Emulator | Physical device |
|---|---|---|
| Root | Built in on the right image | Bootloader unlock, wipes the device |
| Architecture | x86_64 | ARM |
| Reset | Snapshot, instant | Reflash, slow |
| Hardware | Emulated sensors, camera, fingerprint | Real |
| Play Integrity | Fails | Can pass, with effort |
| Cost | Free | A spare phone |

The emulator has two real problems. Apps shipping only ARM native libraries will not install or will crash on x86_64, and apps that check Play Integrity or run their own emulator detection refuse to start. When either happens, you need a physical device.

## Android Studio and the SDK

Install Android Studio from the [developer site](https://developer.android.com/studio). The IDE is optional, but it is the easiest way to get the SDK, and its **Device Manager** and **Device Explorer** are useful.

If you want the tools without the IDE, download the **command line tools only** package and use `sdkmanager` directly.

Either way, the SDK goes into a single directory:

```text
~/Android/Sdk/          # Linux
~/Library/Android/sdk   # macOS
```

Put its tool directories on your `PATH`, or you will be typing absolute paths all day:

```bash
# ~/.bashrc or ~/.zshrc
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$PATH:$ANDROID_HOME/platform-tools"      # adb, fastboot
export PATH="$PATH:$ANDROID_HOME/emulator"            # emulator
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"  # sdkmanager, avdmanager
```

Check that it works:

```bash
adb version
emulator -version
sdkmanager --list_installed
```

Install `build-tools` explicitly as well. It carries `apksigner` and `zipalign`, which you need the first time you repackage an APK:

```bash
sdkmanager "build-tools;35.0.0"
```

## Creating an Emulator You Can Root

System images come in flavours, and the flavour decides whether you can become root:

| Image label | Build type | `adb root` |
|---|---|---|
| **Google APIs** | `userdebug` | Works immediately |
| **AOSP** (no label) | `userdebug` | Works immediately |
| **Google Play** | `user`, production-signed | Refused |

A Google Play image is signed the same way a retail phone is, and `adbd` on it will not restart as root. Pick **Google APIs** unless you specifically need the Play Store on the device. If you do, rooting it with Magisk is covered further down.

Through the GUI: **Device Manager** → **Add a new device** → pick a phone → on the system image screen, choose an image whose target reads *Google APIs* rather than *Google Play*.

From the command line:

```bash
# See what is available, then install one
sdkmanager --list | grep "system-images;android-35"
sdkmanager "system-images;android-35;google_apis;x86_64"

# Create the AVD
avdmanager create avd -n pentest -k "system-images;android-35;google_apis;x86_64" -d pixel_7

# Check it exists
emulator -list-avds
```

Keep the command line tools current (`sdkmanager --install "cmdline-tools;latest"`). Older versions had an `avdmanager` bug where `-d` aborted with a `Could not load devices from .../devices.xml` error; recent versions create the AVD cleanly.

### Starting It

```bash
# Normal start
emulator -avd pentest

# Useful flags
emulator -avd pentest \
  -writable-system \      # allow the system partition to be remounted rw
  -no-snapshot-load \     # cold boot, ignore the saved snapshot
  -http-proxy 127.0.0.1:8080   # route device traffic through a proxy
```

`-writable-system` gives the emulator a writable copy of the system image. You need it for installing a system CA certificate, and the emulator must keep that flag on every subsequent start or the changes are dropped.

### Getting Root

On a Google APIs image, root is one command:

```bash
adb root          # restarts adbd as root
adb shell id      # uid=0(root) gid=0(root)
```

If you get `adbd cannot run as root in production builds`, you picked a Google Play image. Either recreate the AVD with a Google APIs image, or root it with Magisk as below.

### Making the System Partition Writable

Root alone is not enough to write to `/system`. Verified boot still blocks it, so verification has to come off first:

```bash
adb root
adb shell avbctl disable-verification
adb reboot

# after it comes back
adb root
adb remount
```

`adb remount` should report that the partitions were remounted read-write. If it fails, the emulator was started without `-writable-system`.

## Rooting a Google Play Image with Magisk

When you need the Play Store, or you want the emulator to behave like a Magisk-rooted phone, patch the AVD's ramdisk. [rootAVD](https://github.com/newbit1/rootAVD) automates it:

```bash
git clone https://github.com/newbit1/rootAVD.git
cd rootAVD

# Lists every AVD image it can patch, with the exact command for each
./rootAVD.sh ListAllAVDs

# Patch the one you want, using the path the listing printed
./rootAVD.sh system-images/android-35/google_apis_playstore/x86_64/ramdisk.img
```

The emulator reboots into a patched ramdisk with the Magisk app installed. Open Magisk, let it finish setup, and reboot once more. Root is then granted per-app through Magisk rather than by `adb root`:

```bash
adb shell su -c id     # uid=0(root)
```

Magisk modules also install a system CA certificate on Android 14 and later.

## Rooting a Physical Device

Only do this on a device you own and are willing to wipe. Unlocking the bootloader erases all user data, and on some devices it permanently trips a fuse that disables banking apps and DRM playback.

The steps are the same on most devices:

1. **Enable developer access.** Settings → About phone → tap **Build number** seven times. Then in **Developer options**, enable **USB debugging** and **OEM unlocking**.
2. **Unlock the bootloader.** Reboot to the bootloader and unlock it. Some vendors require an unlock code requested from them first, and some do not allow it at all.

   ```bash
   adb reboot bootloader
   fastboot flashing unlock     # older devices: fastboot oem unlock
   ```

3. **Get the matching `boot.img`.** Download the factory image for the exact build currently on the device and extract `boot.img` from it. The wrong build will bootloop the phone.
4. **Patch it with Magisk.** Install the Magisk APK on the device, push `boot.img` to it, and use **Install** → **Select and Patch a File**. Pull the patched image back:

   ```bash
   adb push boot.img /sdcard/Download/
   # patch in the Magisk app, then
   adb pull /sdcard/Download/magisk_patched-<suffix>.img
   ```

5. **Flash it.**

   ```bash
   adb reboot bootloader
   fastboot flash boot magisk_patched-<suffix>.img
   fastboot reboot
   ```

Verified boot will now warn on every boot. That is expected on an unlocked bootloader and not a sign anything went wrong.

Google Pixels are the easiest devices for this: factory images are published for every build, and the unlock is officially supported.

## Snapshots

Before installing the target app, save a clean state. That way every test starts from a known device instead of one still carrying changes from earlier tests.

In the emulator's extended controls, **Snapshots** → **Take snapshot**. From the command line, `-no-snapshot-load` starts from a cold boot instead of the saved snapshot, and `-wipe-data` resets the device entirely.

On a physical device, the cheap equivalent is uninstalling and reinstalling the app between tests:

```bash
adb shell pm clear <package>      # wipe app data, keep the app
adb uninstall <package>
```

## Verifying the Setup

Before moving on, check that all of these work:

```bash
adb devices                 # the device is listed as "device", not "unauthorized"
adb shell getprop ro.build.version.release   # Android version
adb shell id                # uid=0(root), or use: adb shell su -c id
adb remount                 # partitions remounted read-write
```

With that working, the device is ready for [ADB](/collections/mobile/android-adb) and for putting a proxy in front of its traffic.
