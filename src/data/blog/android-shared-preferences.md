---
author: Kayra
pubDatetime: 2026-09-27T00:00:00+03:00
title: "SharedPreferences on Android"
slug: "android-shared-preferences"
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "Testing Android SharedPreferences: the plaintext XML backing store, the mode flags, EncryptedSharedPreferences and DataStore, and reading the store back from a device."
---

SharedPreferences is Android's key-value store for small persistent data: settings, feature flags, and, too often, tokens. It is a plaintext XML file inside the app sandbox, so a secret written there is readable by anyone who can reach the file. On a rooted device, or through a debug build's `run-as`, the file is reachable. This page covers what the store looks like, how to find what an app writes, and how to read it back. The sandbox layout it lives in is in [Android ADB](/collections/mobile/android-adb), and the keystore the encrypted form depends on is in [Android Foundations](/collections/mobile/android-foundations).

## How SharedPreferences Works

An app reads and writes a named preferences file with a mode argument:

```java
SharedPreferences prefs = getSharedPreferences("app_prefs", MODE_PRIVATE);
prefs.edit().putString("auth_token", token).apply();
```

The value is stored in `/data/data/com.example.app/shared_prefs/app_prefs.xml` in the clear. The file is just XML, so the store doubles as an easy list of every flag and value the app keeps, encrypted or not.

The mode argument controls who can read the file. `MODE_PRIVATE` restricts it to the app. The old `MODE_WORLD_READABLE` and `MODE_WORLD_WRITEABLE` modes made the file readable or writable by every other app on the device, removing the sandbox boundary entirely. They were deprecated in Android 4.2 and throw an exception from Android 7.0 onward, so they only appear in legacy or low-`targetSdk` apps, but where they appear they are a direct leak.

## Finding What an App Writes

List the preferences call sites and read which values reach them:

```bash
grep -rnE 'getSharedPreferences|getPreferences\(|edit\(\)|putString|putBoolean|putInt|putLong' jadx_out/sources/
```

Then check whether the writes are encrypted:

```bash
grep -rnE 'EncryptedSharedPreferences|MasterKey|AndroidKeyStore' jadx_out/sources/
```

`EncryptedSharedPreferences`, from the Jetpack Security library, encrypts both keys and values with a master key held in the `AndroidKeyStore`, so the on-disk XML is ciphertext and the key material is not in the file. A plain `getSharedPreferences` that receives a token, a password, or PII is the finding. This is MASTG-TEST-0287.

`Preferences DataStore` is the modern replacement for `SharedPreferences`, and it is not a fix on its own: its backing file in `files/` is plaintext too, so a sensitive value stored through DataStore fails the same way. Only an encrypted wrapper changes the outcome.

## Reading the Store Back

On a rooted device or a debuggable build, read the file with the app's own uid so the sandbox applies no restrictions. The filename depends on how the app calls `getSharedPreferences`: the default preferences file is `<package>_preferences.xml`, and a named store uses its own file. List the directory first, then read the file by name:

```bash
adb shell run-as com.example.app ls shared_prefs/
adb shell run-as com.example.app cat shared_prefs/com.example.app_preferences.xml
```

A `*` in the path is expanded by the device shell before `run-as` changes into the sandbox, so a bare `cat shared_prefs/*.xml` fails even when the file is there. Wrap the glob in `sh -c` to expand it after the change of directory:

```bash
adb shell run-as com.example.app sh -c 'cat shared_prefs/*.xml'
```

On a rooted device the whole store can be pulled without `run-as`:

```bash
adb pull /data/data/com.example.app/shared_prefs/
```

Exercise the flows that store something sensitive first (log in, save a token, enter a PIN), then read the store back. The value that appears in the XML is the evidence. A debuggable app also accepts writes back into the store, which the [Strings Lab write-up](/collections/mobile/mhl-strings-lab) uses to flip a check.

- **Pass**: sensitive values reach only `EncryptedSharedPreferences` (or an encrypted DataStore wrapper), or nothing sensitive is stored in preferences.
- **Fail**: a token, credential, or PII value sits in plaintext in a SharedPreferences or DataStore file.
- **Evidence**: the write call site, the file path, and the cleartext value read back from disk.

This check falls under MASVS-STORAGE-1, the control for data the app stores; the MASVS system and the testing profiles that set the bar are in [The OWASP MAS Project](/collections/mobile/mas-project). The rest of what an app stores on disk, files, databases, cache, and external storage, is in [Local Storage on Android](/collections/mobile/android-local-storage).