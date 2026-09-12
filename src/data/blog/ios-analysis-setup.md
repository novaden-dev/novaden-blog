---
author: Kayra
pubDatetime: 2026-06-22T00:00:00Z
title: "iOS Analysis Setup: Jailbreaking with palera1n"
slug: "ios-analysis-setup"
description: "Coming to iOS static analysis from Android: the mental model, why you need a jailbreak, how to functionally verify jailbreak state from Linux, and jailbreaking an iPhone X with palera1n on Fedora (including the failures along the way)."
tags: ["ios", "security"]
category: notes
draft: true
featured: false
---

> **Note:** These are working notes from setting up an iOS analysis device. The jailbreak and verification steps are done; the app-dumping and reversing sections are still in progress.

## Introduction

If you already do Android work, most of your instincts transfer to iOS, but the file formats, tooling, and the way you get the app are all different. The single biggest difference: Android apps are bytecode that decompiles back to near-readable Java, while iOS apps are natively compiled ARM64 machine code. There is no `jadx` equivalent that gives you clean source. You are doing real binary reverse engineering, closer to reversing a C or C++ binary than reversing an APK.

The device used in these notes is an iPhone X (`iPhone10,6`, A11 chip) running iOS 16.7.10, driven from a Fedora Linux host.

## The Android to iOS mental map

| Android | iOS equivalent |
|---------|----------------|
| APK | IPA (also just a ZIP) |
| `classes.dex` (Dalvik bytecode) | Mach-O binary (native ARM64) |
| `AndroidManifest.xml` | `Info.plist` |
| Java or Kotlin | Objective-C or Swift |
| `jadx`, `dex2jar` | Ghidra, Hopper, IDA (no decompile to source) |
| `apktool` | `unzip` plus plist and Mach-O tools |
| `adb` | `libimobiledevice` tools over `usbmuxd` |

## Why you need a jailbreak

Apps distributed through the App Store are encrypted with Apple's FairPlay DRM. If you pull the IPA straight from the store, the main executable's `__TEXT` section is encrypted and your disassembler shows garbage. The Mach-O header flag `cryptid = 1` tells you the binary is still encrypted.

To get a decrypted binary you have to dump it from memory after iOS has decrypted it to run it. That requires running code on a jailbroken device. This is why a jailbroken test device is part of every serious iOS static analysis setup, even though the analysis itself happens on your host.

## Verifying jailbreak state from Linux

A device can have jailbreak apps installed without being actively jailbroken right now. This matters, and it is easy to get wrong.

### Installed apps prove installation, not an active jailbreak

Reading the device log or the installed app list and seeing Sileo, Filza, or TrollStore only proves those apps exist on disk. Two traps:

- **TrollStore is not a jailbreak.** It is a permanent sideloader (a CoreTrust exploit) that installs apps with arbitrary entitlements on a fully stock device. Its presence proves nothing about jailbreak state.
- **A package manager being present does not mean the jailbreak is active.** On A11 devices, palera1n is semi-tethered: after every reboot the phone boots stock, and the jailbreak services are gone until you re-run the exploit from a computer. Sileo just sits there inert in that state.

### Test functionally instead

The honest check is to do something only an active jailbreak permits. Any one of these is proof:

- **Root filesystem access** over the `com.apple.afc2` service. Stock iOS only exposes `com.apple.afc`, which is sandboxed to the media directory. A jailbreak adds `afc2`, which reaches the whole root filesystem.
- **An SSH daemon.** Stock iOS ships none. If SSH answers on port 22 (OpenSSH) or 44 (palera1n's Dropbear over loopback), that is a jailbreak service.
- **A full process list over `frida-server`.** Seeing `launchd` and `SpringBoard` means unsigned code is running with the privileges you need.

The `afc2` test is the cleanest because it does not depend on any network service. Using `pymobiledevice3`, opening `com.apple.afc2` raises `InvalidService` on a device that is not actively jailbroken, and lists `/` with `bin`, `etc`, `private`, and `var` when it is.

> **Gotcha:** All three tests can come back negative on a device that was jailbroken yesterday. If it has rebooted since, a semi-tethered jailbreak is dormant, not gone. Re-run the jailbreak before concluding anything.

## Jailbreaking an iPhone X with palera1n

palera1n is the checkm8 bootrom jailbreak for A8 through A11 devices. checkm8 is a BootROM exploit, and the BootROM is read-only silicon, so the exploit cannot be patched in software and cannot permanently brick the device. The worst case is a reboot back to stock. The C rewrite of palera1n is a native Linux CLI, so Fedora works directly.

### Rootless vs rootful

Since iOS 15, the system partition is a cryptographically sealed read-only snapshot (SSV, the Signed System Volume). The two jailbreak styles differ in whether they break that seal.

| | Rootful | Rootless |
|--|---------|----------|
| Installs to | Real system paths (`/usr`, `/bin`) | A separate bootstrap under `/var/jb` |
| SSV seal | Broken, system remounted read-write | Untouched |
| Injection | Substrate or Substitute | ElleKit |
| Reversibility | Hard, often needs a full restore | Easy, just remove the bootstrap |
| palera1n flag | `-f` | `-l` |

For static analysis you want **rootless**. You do not need to modify the system partition, you need root-level access to run `frida-server`, SSH in, and read decrypted app binaries. Rootless gives all of that while staying clean and reversible. Sileo and the modern dumping tools all ship rootless builds.

### A11 and iOS 16 caveats

- **Passcode and the SEP.** On A11, you must not have a passcode set while jailbreaking. The Secure Enclave bug causes boot loops on iOS 16 if a passcode is set. If a passcode was ever set on iOS 16, you have to erase the device first. Check with `ideviceinfo -k PasswordProtected`; a value of `false` means you are clear and the process is non-destructive.
- **Semi-tethered.** Every reboot drops the device back to stock. Re-running `sudo palera1n -l` re-activates it. This is not a bug, it is how checkm8 on A11 works.

### The process

First install palera1n:

```bash
sudo /bin/sh -c "$(curl -fsSL https://static.palera.in/scripts/install.sh)"
```

Leave the device powered on, unlocked, and trusted to the computer. palera1n drives the reboot into recovery and then DFU itself, so do not power it off first. Start a rootless jailbreak:

```bash
sudo palera1n -l
```

Press Enter when prompted, and follow the on-screen countdown into DFU mode. The DFU sequence on an iPhone X has two phases, and the handoff between them is where most attempts fail:

1. Hold **Volume Down and Side together** for about 4 seconds.
2. Release **Side**, keep holding **Volume Down alone** for about 10 seconds.

A fully black screen means DFU succeeded. An Apple logo means you held too long. The "connect to iTunes" cable screen means you let go of Volume Down too early. palera1n auto-retries, so you get unlimited attempts.

Once the exploit lands you will see `Checkmate!`, then the device boots PongoOS, the kernel patches are applied, and it boots into iOS with the rootless bootstrap active. Verbose boot text in the top-left corner of the screen during this stage is normal, not an error.

## Troubleshooting

These are the real failures from this setup and what fixed them.

### Device did not enter DFU mode

DFU timing rarely lands on the first try. palera1n loops back to recovery and lets you try again. Start the button sequence the moment the countdown begins, press firmly, and use two hands so you can release Side cleanly while keeping Volume Down held.

### Timed out waiting for download mode

After `Checkmate!`, the device drops off USB and must re-enumerate into PongoOS mode. The host USB controller often fails to pick it up in that window, and palera1n reports `-status_exploit_timeout_error`.

The most reliable fix is the simplest: the moment palera1n prints `Checkmate!` and starts waiting for download mode, **physically unplug the cable and plug it back in**. The replug forces the re-enumeration into download mode that the controller was blocking, and palera1n proceeds to boot PongoOS. This worked every time when nothing else did.

Two things to try first, which help on some controllers but were not enough on their own here:

- Disable USB autosuspend. A default value of `2` (suspend after 2 seconds) can suspend the port during the reconnect window. Note this only changes the default for newly-probed devices and resets on a host reboot, so re-apply it each session:

```bash
echo -1 | sudo tee /sys/module/usbcore/parameters/autosuspend
```

- Route the phone through a USB 2.0 hub. USB 3.x host controllers (xHCI) have timing quirks that break the exploit's reconnect, and a USB 2.0 hub sidesteps them.

### Stuck on the Apple logo with text in the corner

Check what USB mode the device is actually in before assuming it is stuck:

```bash
lsusb | grep -i apple
```

| Product ID | Mode |
|------------|------|
| `12a8` | Normal or booting |
| `1281` | Recovery |
| `1227` | DFU |
| `4141` | PongoOS |

If it shows `4141` (PongoOS), the exploit worked and the device is just holding in pongo. The Apple logo on screen is what PongoOS displays, and the corner text is the verbose kernel boot. Do not force-restart. Re-run `sudo palera1n -l` and it will pick up the pongo device and finish the boot.

## Next steps

With an active rootless jailbreak, the path to decrypted binaries opens:

- Add the Frida repo in Sileo (`https://build.frida.re`) and install `frida-server` to get `frida-ps -U` working.
- List installed apps with `frida-ps -Uai` and pick a target.
- Dump a FairPlay-decrypted IPA with `frida-ios-dump`.
- Unzip the IPA and read `Info.plist` with `plutil -p` for entitlements, URL schemes, and the ATS network config.
- Recover Objective-C class headers with `class-dump`, inspect the Mach-O with `otool` and `nm`, and load the binary into Ghidra or Hopper for the actual reversing.
- Run the IPA through MobSF for a fast automated first pass.

> **Quick reference:** Swift is harder to reverse than Objective-C because it lacks the same runtime metadata. Expect mangled symbols, and keep `swift-demangle` handy.
