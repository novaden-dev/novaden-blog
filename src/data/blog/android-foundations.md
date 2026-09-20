---
title: "Android Foundations"
slug: android-foundations
category: notes
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-14T00:00:00+03:00
description: "How Android is built from the kernel up, the security features that protect it, and the basics of Android apps: the sandbox, the manifest, components, IPC, signing, and publishing."
---

Android is an open source operating system based on Linux. It runs on phones, cars, and IoT devices. Its source code is published as the Android Open Source Project (AOSP), and device manufacturers build their own versions of Android on top of it.

## Android Architecture

Android is built in layers. The kernel at the bottom is the most privileged, and the apps at the top are the least.

```text
Apps
Java API Framework
Native Libraries  |  Android Runtime (ART)
Hardware Abstraction Layer (HAL)
Linux Kernel
```

### Linux Kernel

The kernel provides the basic system services: memory management, process management, the network stack, and device drivers. It also enforces the main security boundaries, including the app sandbox and SELinux, both covered below.

### Hardware Abstraction Layer (HAL)

The HAL sits between the kernel and the layers above it. It is the interface between the hardware and the Android platform. Each piece of hardware, like the camera or Bluetooth, is exposed through a standard interface, so Android can use it without caring which manufacturer's driver is underneath.

### Native Libraries and Android Runtime

Native libraries are C/C++ libraries that provide core system services. A few examples:

- **SQLite**: the database engine Android uses to store structured data. The system keeps things like contacts and SMS messages in SQLite databases, and apps use it for their own local databases, stored in `/data/data/<package-name>/databases/`.
- **OpenSSL**: provides encryption and TLS. Android actually ships BoringSSL, Google's fork of OpenSSL.
- **WebKit**: the engine that renders web pages. Newer Android versions use Chromium for this instead.

The runtime runs the app code. Java or Kotlin code is compiled into DEX (Dalvik Executable) bytecode, and that bytecode is what goes into the APK. The processor can't run bytecode directly, so the runtime has to translate it into machine code, the instructions the processor actually understands. The two runtimes differ in when they do that translation:

- **Dalvik Virtual Machine (DVM)**: the original runtime. It translated the bytecode while the app was running, every time the app ran.
- **Android Runtime (ART)**: replaced Dalvik in Android 5.0. It translates the app into machine code ahead of time, before the app runs, and saves the result on the device so the work isn't repeated on every launch. In Android 5.0 and 6.0 the whole app was translated at install time, which made installs slow. Since Android 7.0, ART translates the parts of the app that get used most, in the background while the phone is idle and charging, and handles the rest while the app runs.

Either way, the APK doesn't change. It still contains the DEX bytecode, and that's what you decompile when testing an app.

### Java API Framework

These are the high-level APIs developers use to build apps. The framework also manages apps while they run: it controls each app's life cycle (when screens start, pause, and close) and handles user interaction. Its main parts:

- **Activity Manager**: manages app life cycles.
- **View System**: used to build the UI (buttons, lists, text fields) and handles user input on it.
- **Content Providers**: let apps access data from other apps.
- **Other managers**: shared services like the Notification Manager and the Location Manager.

The runtime only executes code. Life cycles and user interaction are the framework's job.

### Apps

The top layer. Apps are written in Java or Kotlin and packaged as APK files. This includes the apps that come preinstalled on the phone, like Phone and Settings.

## Android Security

### Encryption

Encryption protects the data stored on the device from unauthorized access. Without the user's PIN, pattern, or password, the data can't be read. There are two types:

- **Full-disk encryption (FDE)**: the whole data partition is encrypted with one key. Nothing works until the user unlocks the device at boot.
- **File-based encryption (FBE)**: each file is encrypted separately, with different keys. The phone can boot and handle basic things like alarms and calls before it is unlocked, while the user's data stays locked until then.

Devices that ship with Android 10 or later must use file-based encryption, and Android 13 removed full-disk encryption completely.

### Trusted Execution Environment (TEE)

The TEE is a separate, protected area inside the phone's processor. The processor is split into two parts, called worlds:

- **Normal world**: Android, the kernel, and all apps.
- **Secure world**: the TEE, with its own small operating system.

The normal world can't read the secure world's memory, even with root or a compromised kernel. So the most sensitive work happens inside the TEE:

- Creating and using encryption keys (the hardware-backed Android Keystore).
- Checking the lock screen PIN, pattern, or password.
- Matching fingerprints.

Apps never see these keys. An app sends data to the TEE to be encrypted, decrypted, or signed, and only gets the result back. That's why a hardware-backed key can't be copied off the device, even on a rooted phone.

The TEE doesn't encrypt your files itself. It protects the keys that encryption depends on.

On most Android phones the TEE is built on ARM TrustZone. The Secure Enclave is Apple's version on iOS, not part of Android.

### Verified Boot

Verified boot makes sure all the code that runs during boot comes from a trusted source. Each boot stage checks the signature of the next one before running it:

1. The **hardware root of trust**, a key built into the hardware that can't be changed, checks the bootloader.
2. The bootloader checks the kernel and the system partitions.
3. Android keeps checking the system partitions while the device is running.

If a check fails, the device shows a warning or the boot stops.

### Network Security

- **TLS by default**: apps that target Android 9 or later block plain HTTP by default. Android 9 also added Private DNS, which sends DNS queries over TLS.
- **Network security config**: each app can have its own network security config, an XML file that sets which certificate authorities the app trusts, where plain HTTP is allowed, and which certificates are pinned.
- **Certificate pinning (SSL pinning)**: the app only accepts the server's certificate if it matches a certificate or public key stored in the app. A certificate from a trusted authority still gets rejected if it doesn't match. This protects against man-in-the-middle (MITM) attacks. It also blocks your intercepting proxy during testing, so pinning usually has to be bypassed.

### SELinux

By default, Linux uses **discretionary access control (DAC)**. Each file has an owner and permissions, the owner decides who gets access, and root can access everything. Android uses this too: every app runs as its own Linux user.

SELinux (Security-Enhanced Linux) adds **mandatory access control (MAC)** on top. Every process and file gets a label, and one system-wide policy says which labels can access what. Anything the policy doesn't allow is denied. File owners can't change the rules, and the rules apply to root too.

A normal app runs with a label like this:

```text
u:r:untrusted_app:s0:c128,c257,c512,c768
```

`untrusted_app` is the app's domain, and the `c` values keep apps and device users apart. If an app gets compromised, the attacker can only do what the policy allows for `untrusted_app`. This keeps apps isolated in their sandboxes and away from system components. SELinux has been enforced on all processes since Android 5.0.

### Anti-Exploitation

These protections make memory bugs, like buffer overflows, much harder to exploit. They don't fix the bugs, they block the usual ways of using them.

| Protection | What it does |
|---|---|
| **ASLR** (Address Space Layout Randomization) | Loads programs, libraries, the stack, and the heap at random memory addresses, so an exploit can't know where things are. |
| **KASLR** (Kernel ASLR) | Loads the kernel at a random memory address every time the device boots, so an attacker exploiting a kernel bug doesn't know where the kernel's code and data are. |
| **DEP** (Data Execution Prevention, also called NX) | Marks data memory, like the stack and the heap, as not executable, so code injected there can't run. |
| **SECCOMP filter** | Limits which system calls a process can make. Android applies one to every app, blocking system calls apps don't need. |

In app pentesting you won't deal with these much. They come up when an app includes native C/C++ libraries: scanners check whether those libraries were built with protections like NX, and report the ones that weren't.

### Rooting

Rooting means getting around the device's security to gain root (superuser) access, removing the restrictions set by the manufacturer or carrier. On most phones it starts with unlocking the bootloader, which is a separate step: an unlocked bootloader lets the phone boot software the manufacturer didn't sign (verified boot shows a warning on every boot), and unlocking it wipes all user data. On iOS, the same thing is called jailbreaking.

## Android Applications

Apps are mostly built with the Java APIs from the Android SDK. They can also include native C/C++ code, built with the NDK (Native Development Kit).

### Sandbox

Every app runs in its own sandbox. When an app is installed, Android gives it its own Linux user ID (UID). The app runs in its own process, with its own instance of the runtime, and gets its own private data directory:

```text
/data/data/<package-name>/
```

For example, `/data/data/com.example.app/`. Linux file permissions and SELinux keep other apps out of it.

### sharedUserId

`sharedUserId` is a manifest setting that lets several apps run under the same Linux UID. Apps with the same UID can read each other's data directories and can even run in the same process, so they basically share one sandbox. It only works if all the apps are signed with the same certificate, which means they come from the same developer.

It has been deprecated since Android 10 (API 29), but older apps still use it. If you see it in a manifest, treat those apps as one sandbox: compromise one and you get the data of all of them.

### Packaging: APK and AAB

- **APK (Android Package)**: the older and more common format. An APK is a ZIP file with the app's DEX code, resources, manifest, and signature.
- **AAB (Android App Bundle)**: the newer format, used for publishing. The developer uploads an AAB to Google Play, and Google Play builds APKs from it for each device. New apps on Google Play have to use AAB.

Devices never install an AAB directly. What gets installed is always APKs, often a base APK plus a few split APKs.

### Manifest

Every app has an `AndroidManifest.xml` file. It includes:

- The package name, which is the app's unique ID.
- The app components.
- The app's entry point: the activity with an intent filter for `android.intent.action.MAIN` and `android.intent.category.LAUNCHER` is what the launcher icon starts.
- The permissions the app asks for.
- Flags that affect security, like `android:exported` (whether other apps can reach a component), `android:debuggable`, and `android:allowBackup`.

### App Components

An app is built from four component types. The manifest declares each one, and intents (below) are how anything reaches them.

### Activities

An activity is one screen: the login form, the message list, the settings page. It is the only component with a UI, and it is what the user interacts with. When a new activity starts, the system places it on top of a stack, so the previous screen sits below it and comes back when the new one closes. Any app can start an exported activity and hand it data in the intent.

### Activity States

An activity moves through four states as the user navigates:

- **Active**: the activity is in the foreground and receives the user's input.
- **Paused**: the activity lost focus but is still visible, for example behind a translucent activity or in multi-window mode. It keeps all its state.
- **Stopped**: another activity completely covers it. It is invisible but still holds its state, and the system kills it first when the device needs memory.
- **Destroyed**: the system either asks the activity to finish or kills its process, and it is gone.

When an activity stops being the foreground one, the system takes a screenshot of it for the task switcher, so whatever was on screen at that moment stays visible in the recents list.

### Services

A service runs work in the background with no UI: playing music, syncing data, uploading a file. Work can keep running while the user is elsewhere, and other components or apps can bind to a service and call it directly. It runs in the app's own process on the main thread, so long work needs its own thread.

### Broadcast Receivers

A broadcast receiver listens for broadcast messages. The system sends many (boot completed, battery low, connectivity changes), and apps can send their own. A receiver declared in the manifest runs code whenever a matching broadcast arrives, including one sent by another app, so an exported receiver is an external entry point in the same sense as an exported activity.

### Content Providers

A content provider shares an app's data with other apps. Other apps query it through `content://` URIs (for example `content://com.example.app/notes/3`), and the provider decides which URIs and rows they can read. A provider that checks its callers loosely exposes data the app treats as private.

### Intents

An intent is a messaging object that asks the system to do one of three things: start an activity, start a service, or deliver a broadcast. It is the only way an app reaches another app's activity, service, or receiver, which makes it the main carrier of data across app boundaries.

- **Explicit intent**: names the target component by package and class. The sender already knows exactly what it is calling, and apps use these internally, for example to open their own second screen.
- **Implicit intent**: names only an action, such as `android.intent.action.VIEW` with a URL attached. The system matches the action against the **intent filters** that components declare in the manifest, and offers the intent to every matching component.

An intent filter lists the actions, data types, and URI schemes a component accepts. An implicit intent reaches a component only if its filter matches, and a component that receives intents from other apps must also be exported. The combination of `android:exported="true"` with a filter marks an external entry point.

## Android IPC

Inter-Process Communication (IPC) is how apps pass data to each other. Each app runs in its own sandbox and can't access another app's memory, so the system provides a controlled way for apps to talk to each other.

On Android this goes through **Binder**, a driver in the kernel. Starting another app's activity, sending a broadcast, querying a content provider, and calling system services all go through Binder. On every call, Binder tells the receiver the caller's UID, and the system uses it to check permissions.

Apps don't call Binder directly. The **intents** described under App Components are what an app writes, and the system turns them into Binder transactions under the hood. The system controls how apps talk to each other, but the receiving app still has to check what it gets. An exported component that trusts any data sent to it is a common vulnerability.

## Publishing an Android App

### Signing

Every APK has to be signed with a certificate before Android will install it. The certificate identifies the developer. It doesn't need to come from a certificate authority; self-signed is normal. Android uses the signature for:

- **Updates**: an update only installs if it's signed with the same key as the app already on the device.
- **Trust between apps**: `sharedUserId` and signature permissions only work between apps signed with the same certificate.

If you modify an app during testing, you have to sign it again before it will install.

### Google Play Requirements

To publish on Google Play, a developer needs to:

- Register in the Google Play Console.
- Upload a signed AAB or APK.
- Follow Google Play's Developer Program Policies.

AOSP has nothing to do with this. AOSP is the source code of Android itself, and it doesn't approve apps.
