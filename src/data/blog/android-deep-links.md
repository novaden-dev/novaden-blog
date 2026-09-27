---
author: Kayra
pubDatetime: 2026-09-27T00:00:00+03:00
title: "Deep Links and URL Schemes on Android"
slug: "android-deep-links"
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "Testing Android deep links: how intent filters declare them, how App Links verify ownership while custom schemes cannot, and how to craft URIs that expose handlers trusting attacker-controlled data."
---

A deep link is a URI that launches an activity inside an app. Tapping `https://example.com/profile` in a browser can open the app's profile screen, and a custom scheme like `example://profile/1` does the same from any app on the device. The handler runs with whatever the link carries, so a link a user taps, or an app that fires the URI directly, passes data into the app without any privilege. This page covers how deep links are declared, how ownership works, and how to test the handlers. The intent filter machinery behind them is in [Android Foundations](/collections/mobile/android-foundations).

## How a Deep Link Is Declared

An activity becomes a deep link when its intent filter lists the `android.intent.action.VIEW` action, the `DEFAULT` and `BROWSABLE` categories, and a `<data>` element for the scheme, host, and path:

```xml
<activity android:name=".ProfileActivity" android:exported="true">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="https" android:host="example.com" />
    <data android:scheme="example" android:host="profile" />
  </intent-filter>
</activity>
```

The activity must be exported for the link to reach it, and `BROWSABLE` is what lets a browser open it. The URI scheme can be `https` or a custom scheme such as `example`, `pay`, or a reversed domain.

## Custom Schemes and App Links

`https` links can prove that the domain really owns the app; custom schemes cannot.

- **App Links**: an `https` deep link with `android:autoVerify="true"` on the intent filter. At install, Android fetches `assetlinks.json` from `https://<domain>/.well-known/assetlinks.json`; the file lists the app's signing certificate and package. Only a domain that publishes that file can claim the link, so another app cannot hijack an `https` link to the domain. An App Link that skips `autoVerify`, or a domain that does not publish the file, does not get that guarantee. That is MASTG-TEST-0393.
- **Custom schemes**: no ownership check exists. Any app can declare `example://` in its own manifest, and Android shows a chooser when several apps claim the same scheme. There is no guarantee which app `example://` resolves to, and the host in the URI is whatever the sender put there. The failure is a handler that takes a decision from the URI without validating it. That is MASTG-TEST-0394.

## What the Attacker Controls

Firing a deep link means controlling the whole URI, including the host, path, and every query parameter. For an `https` App Link the link comes from a page the attacker hosts; for a custom scheme it comes from any app on the device:

```bash
adb shell am start -a android.intent.action.VIEW -d "example://profile/1?status=success"
```

The handler receives it through `getIntent().getData()` in `onCreate`, and what it does with the parsed URI decides the risk.

## Testing the Handlers

1. **Enumerate.** List every intent filter that declares a scheme, and note which ones verify:

```bash
grep -nE '<intent-filter|<action|<category|<data|android:scheme|android:host|android:autoVerify|BROWSABLE' apktool_out/AndroidManifest.xml
```

2. **Read each handler.** In the decompiled code, find where the activity reads the incoming URI. `getData()`, `getQueryParameter`, and `getPathSegment` are the reads; a redirect, a file path, a WebView load, or a navigation decision is the use.

```bash
grep -rnE 'getData\(\)|getQueryParameter|getPathSegment|getIntent\(\)' jadx_out/sources/
```

3. **Craft and fire.** Send each scheme, host, and path combination with the parameters the handler seems to expect, then watch what happens:

```bash
adb logcat -c
adb shell am start -a android.intent.action.VIEW -d "example://profile/1?status=success&redirect=https://evil.example"
adb logcat -d | grep -i com.example.app
```

4. **Decide trigger versus data.** The key question is whether the deep link only signals that something happened, or whether it carries a value the handler trusts. A payment or login return link that re-checks status with the server is a trigger; one that trusts `?status=success` from the link is a finding:

```java
// The link is only a signal; the decision is made server side.
if (uri.getScheme().equals("example")) {
    viewModel.fetchStatusFromServer();
}

// Trusts a value the attacker wrote into the URL.
if (uri.getQueryParameter("status").equals("success")) {
    navigateToSuccessScreen();
}
```

> **Note:** an exported activity also lets another app set intent extras directly, in addition to the URI. So "the deep link only triggers a server check" must hold even when the attacker controls every extra and query parameter. If the real decision is made server side, forging the link achieves nothing.

- **Pass**: handlers validate the scheme, host, and every parameter before acting, or use the link only as a trigger for a flow whose result comes from the server.
- **Fail**: a handler reads a path or parameter from the URI and uses it for a redirect, a file path, a WebView load, or a navigation decision without validation.
- **Evidence**: the intent filter, the handler code that consumes the URI, and the `am start` command that triggered the behavior.

## A Worked Example

The [Strings Lab write-up](/collections/mobile/mhl-strings-lab) starts with exactly this surface: an exported activity takes a `mhl://labs/...` link, and the solution fires the crafted URI from adb to reach a debug screen. The related component tests are in [Exported Components and the IPC Attack Surface](/collections/mobile/android-exported-components).