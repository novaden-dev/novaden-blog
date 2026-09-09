---
author: Kayra
pubDatetime: 2026-06-02T00:00:00Z
title: "Android App Fundamentals"
slug: "android-fundamentals"
description: "How Android apps are built (activities, services, broadcast receivers, content providers), how they store data (SharedPreferences, the AndroidKeyStore, external storage), where the attack surface is, and the methodology for reversing an APK."
tags: ["android", "security"]
category: notes
draft: false
featured: false
---

> **Note:** These are working notes and still in progress.

## Introduction

Every Android application has an `AndroidManifest.xml`. The entry point of the application is the component declared with the `android.intent.action.MAIN` action in the manifest.

The canonical reference for developing Android applications is [developer.android.com](https://developer.android.com/). Understanding how an app is meant to be built is what tells you where to push on it when pentesting.

## App Components

An Android app is built from four kinds of components: activities, services, broadcast receivers, and content providers. Intents are not a component; they are the messaging object that ties components together, so they get their own subsection below. Each component is a place where the app receives input, which makes each one worth looking at when pentesting.

### Activity

An activity is a single, focused thing the user can do. It is what the user interacts with: the UI.

When a new activity is started, it is usually placed on top of the current activity stack. The previous activity stays below it in the stack and does not come back to the foreground until the new activity exits.

An activity moves through four states:

- **Active**: the activity is in the foreground of the screen.
- **Alive**: the activity lost focus but is still visible (for example, another activity was launched in a higher position in multi-window mode). It keeps all its state and member information.
- **Stopped/hidden**: the activity is completely obscured by another activity. It still retains all state and member information, but it is not visible to the user and will often be killed by the system when memory is needed.
- **Destroyed**: the system drops the activity, either by asking it to finish or by killing its process.

### Intents

An intent is a messaging object you use to request an action from another app component. There are three fundamental use cases:

- Starting an activity.
- Starting a service.
- Delivering a broadcast.

Intents come in two types:

- **Explicit intents**: the exact component (which app, which class) that should satisfy the intent is named.
- **Implicit intents**: no specific component is named, just a general action. The system decides which component can handle it.

Example of an intent that opens a URL:

```java
Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse("https://hextree.io/"));
startActivity(browserIntent);
```

To receive an intent, you set up the `AndroidManifest.xml` to accept it (via an intent filter), and the receiving activity must be exported so other apps can reach it.

### Services

A service is a component that performs an action in the background, without a user interface.

### Broadcast

A broadcast is a message that any application can receive.

### Content Provider

A content provider is the structured way for an app to expose its data to other apps, through a URI interface like `content://<authority>/<path>` that other apps query, insert, update, or delete against. It is the intended mechanism for sharing data across app boundaries; the system Contacts app hands out contacts this way.

Because a provider is a door into an app's data, it is squarely part of the attack surface. If a provider is exported (`android:exported="true"`) and fronts sensitive data without a permission guard, any app on the device can read straight through it.

**FileProvider** is a specialized content provider for sharing files. Modern Android blocks handing another app a raw `file://` path, so a FileProvider issues a temporary `content://` URI for a specific file instead. It is configured with an XML resource that declares which directories it may share. The failure mode is an over-broad declaration: if that XML exposes the whole data directory or a root path rather than one narrow export folder, a granted URI can leak far more than intended.

## Attack Surface

Exported activities are part of the attack surface: any app on the device can interact with the exported parts of an application. Exported services and broadcast receivers are reachable the same way. When mapping an app, the exported components are the first thing to enumerate, because they are what an attacker can touch without any privilege on the app itself.

## Data Storage

Most of what is worth stealing from an app is data it stored locally, so knowing where an app can put data, and which locations are protected, is the groundwork for the whole STORAGE and CRYPTO side of testing.

### Internal vs external storage

**Internal storage** is the app's private sandbox at `/data/data/<package>/`. The OS keeps other apps out of it while the device is intact. **External storage** (the SD card or the emulated equivalent) is shared space: any app holding the storage permission can read it, with no user interaction, and data there can outlive the app's uninstall. The rule of thumb: internal is private by default, external is world-readable, and neither is encrypted just because of where it sits.

### SharedPreferences and file modes

`SharedPreferences` is Android's simple key-value store for small persistent data (settings, flags, and, when developers cut corners, tokens). It is just a plaintext XML file in the sandbox:

```java
SharedPreferences prefs = getSharedPreferences("app_prefs", MODE_PRIVATE);
prefs.edit().putString("auth_token", token).apply();
```

That lands at `/data/data/<package>/shared_prefs/app_prefs.xml` with the value in the clear, which is why it is the first place to look for a carelessly stored secret.

The mode argument controls who can read the file. `MODE_PRIVATE` restricts it to the app. The old `MODE_WORLD_READABLE` and `MODE_WORLD_WRITEABLE` modes made the file readable (or writable) by every other app on the device, removing the sandbox boundary entirely. They were deprecated in Android 4.2 and throw an exception from Android 7.0 onward, so you only see them in legacy or low-`targetSdk` apps, but where they appear they are a direct leak.

### AndroidKeyStore and hardware-backed keys

Storing an encryption key in a file or hardcoding it in the app defeats the point: anyone who pulls the filesystem or reverse-engineers the app gets the key and can decrypt everything. The `AndroidKeyStore` solves this by keeping the key out of the app entirely.

When a key is **hardware-backed**, the raw key material is generated and held inside a separate secure environment, the **TEE** (Trusted Execution Environment) or, on newer devices, a dedicated secure chip (**StrongBox**). The app never sees the key bytes; it asks the keystore to encrypt, decrypt, or sign, and the operation runs inside the secure hardware. The key cannot be extracted even from a rooted device, and it can be bound to conditions such as requiring biometric authentication before use. This is why "put the key in the AndroidKeyStore" is the answer to almost every key-storage question. On iOS the equivalent is the Keychain, backed by the Secure Enclave.

### EncryptedSharedPreferences and EncryptedFile

These are the Jetpack Security wrappers that combine the two ideas above: they encrypt stored data using a master key held in the `AndroidKeyStore`. The choice between them is only about data shape:

- **`EncryptedSharedPreferences`**: the encrypted drop-in for `SharedPreferences`, encrypting both keys and values. Use it for small key-value data like a token or a flag.
- **`EncryptedFile`**: encrypts an arbitrary file or stream. Use it for anything file-shaped, like a document, an image, or a database file.

Neither is stronger than the other; they wrap the same keystore-backed encryption around different data shapes. The Jetpack Security crypto library is deprecated, but with no official replacement yet it is still the recommended option.

## Reverse Engineering Methodology

### How an APK is built

An Android application is written in Java or Kotlin. It is compiled into class files (regular Java bytecode), and a compiler then converts that into DEX code (Dalvik bytecode).

An APK is a ZIP archive containing:

- `classes.dex`
- `AndroidManifest.xml`
- Resources
- Signature

Some applications will not let you pull their APK off the device. In those cases, search for the APK online, but verify the signature and scan it for malware before trusting it.

### Define the goal first

Always define the goal of your reverse engineering before you start. The goal shapes your strategy. For example, if you just want to find where the data comes from (the backend APIs) or to understand the overall app flow, you take a different path than if you are hunting for one specific value, where you may not need to walk the whole app at all.

### Comparing app versions

To compare an updated app against an old one, decompile both APKs with `jadx` into separate folders, then diff the two folders (a VS Code extension works well for this).

### Keys hidden in native libraries

Sometimes an app hides keys inside a native library (for example, `System.loadLibrary("native-lib")`). Native code cannot be decompiled with `jadx`, so there are three approaches:

- **Reverse the binary**: use Ghidra to reverse engineer the native library.
- **Network interception**: intercept the request that uses the key.
- **Run the library yourself**: build a proof of concept that links the native library and calls it the same way the app does.
  1. Export the native library binary from the app's resources.
  2. Create a new class using the same class, package name, and method names as the application.
  3. Add code in your PoC that calls the function which exposes the key.

## Tooling

The tools you reach for during Android pentesting, and what each is for:

- **adb**: the bridge to interact with a device or emulator. Install and pull apps, get a shell, read logs, start activities.
- **apktool**: disassembles an APK into smali (a human-readable form of Dalvik bytecode) and repacks it. Use it when you need to edit and rebuild an app.
- **jadx**: decompiles an APK back to readable Java. Use it to read the code and search for secrets. It cannot handle native (JNI) code.
- **Ghidra**: for the native libraries `jadx` cannot read.

> **Quick reference:** for the actual commands, see the [Android Cheat Sheet](/posts/android-cheatsheet).
