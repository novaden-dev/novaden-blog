---
author: Kayra
pubDatetime: 2026-09-27T00:00:00+03:00
title: "WebViews in Android Apps"
slug: "android-webviews"
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "Testing Android WebViews: the JavaScript bridge, what content the WebView loads, file and content access, mixed content and certificate errors, and remote debugging, with the pass and fail conditions for each."
---

A WebView is a browser engine embedded in an activity, and the app gives it HTML, JavaScript, and other web content to render. Its security is decided by what content it loads, how its settings relax the browser's default behavior, and whether the page can call back into the app through a JavaScript bridge. A WebView that loads trusted first-party HTTPS content with default settings is low risk; the same WebView loading attacker-influenced content with a bridge exposed is code execution in the app's context. This page covers each setting and where the risk comes from. How a WebView fits into the rest of the app's attack surface is in [Exported Components and the IPC Attack Surface](/collections/mobile/android-exported-components).

## Find Every WebView and What It Loads

List the WebViews first and trace where each one gets its content. A hardcoded `https://` URL to a first-party domain is low risk. A URL taken from an intent extra, a deep link, or a server response is attacker-influenced, and it raises the stakes for every setting below.

```bash
grep -rnE 'WebView|loadUrl\(|loadDataWithBaseURL|loadData\(' jadx_out/sources/
```

Two places set the behavior: the `WebSettings` calls on the WebView's `getSettings()`, and the `WebViewClient` and `WebChromeClient` handlers the activity assigns.

## JavaScript and the Native Bridge

`setJavaScriptEnabled(true)` turns on JavaScript in the page. On its own that is not a finding; rendering remote HTML legitimately needs it. The risk appears when JavaScript is on and the content is untrusted, or when the page can call into the app.

`addJavascriptInterface(object, name)` exposes a Java object to the page's JavaScript as `window.<name>`, and since Android 4.2 (API 17) only methods annotated `@JavascriptInterface` are reachable. A page that can call those methods can do whatever they do with the app's privileges. Reachable by remote or cleartext content, that is remote code execution in the app's context. This is MASTG-TEST-0033.

```bash
grep -rnE 'addJavascriptInterface|@JavascriptInterface|setJavaScriptEnabled' jadx_out/sources/
```

- **Pass**: no bridge is exposed, or the bridge is reachable only by content the app fully controls and serves over HTTPS.
- **Fail**: `addJavascriptInterface` is reachable by remote, cleartext, or user-influenced content, or JavaScript is enabled alongside such content and a bridge.
- **Evidence**: the interface registration, the exposed methods, and the URL the WebView loads.

## File and Content Access

The `file://` and `content://` schemes let WebView content read local resources, which a browser page could not. Relaxing them widens what an embedded page can reach.

- `setAllowFileAccess(true)`: allows loading `file://` URLs. Defaults to false for apps targeting API 30 or later, true for older targets.
- `setAllowFileAccessFromFileURLs(true)`: lets a `file://` page read other `file://` URLs.
- `setAllowUniversalAccessFromFileURLs(true)`: lets a `file://` page reach any origin.
- `setAllowContentAccess(true)`: allows loading `content://` URLs. Defaults to true.

The last two default to false and were the source of the classic "arbitrary file read" WebView bug; re-enabling them on a WebView that loads untrusted content is a finding. This is MASTG-TEST-0252.

```bash
grep -rnE 'setAllowFileAccess|setAllowFileAccessFromFileURLs|setAllowUniversalAccessFromFileURLs|setAllowContentAccess' jadx_out/sources/
```

- **Pass**: file access from file URLs and universal access are disabled (the modern defaults), and file access is enabled only where genuinely needed.
- **Fail**: `setAllowUniversalAccessFromFileURLs(true)` or `setAllowFileAccessFromFileURLs(true)` on a WebView that loads any untrusted content.
- **Evidence**: the `WebSettings` calls and what the WebView loads.

## Mixed Content and Certificate Errors

An HTTPS page that loads HTTP subresources is mixed content. `setMixedContentMode` decides what happens:

- `MIXED_CONTENT_NEVER_ALLOW` (0): HTTP resources are not loaded. The hardened choice.
- `MIXED_CONTENT_COMPATIBILITY_MODE` (2): some HTTP resources load. This mode fails the check.
- `MIXED_CONTENT_ALWAYS_ALLOW` (1): everything loads.

The constants decompile as integers, so read them as numbers. This is MASTG-TEST-0284 when the app also ignores TLS errors: a `WebViewClient` whose `onReceivedSslError` calls `handler.proceed()` accepts any certificate, including a proxy's or an attacker's. That check belongs with the certificate-validation review in [Intercepting Mobile Traffic](/collections/mobile/intercepting-mobile-traffic).

```bash
grep -rnE 'setMixedContentMode|onReceivedSslError|\.proceed\(\)' jadx_out/sources/
```

- **Pass**: mixed content is `MIXED_CONTENT_NEVER_ALLOW` (or the page is fully HTTPS), and TLS errors are not silently accepted.
- **Fail**: an HTTPS page loads HTTP resources, or `onReceivedSslError` calls `proceed()` without evaluating the error.
- **Evidence**: the mixed-content mode and the `onReceivedSslError` handler.

## Web Debugging

`setWebContentsDebuggingEnabled(true)` lets anyone with the device attach Chrome DevTools to the WebView through `chrome://inspect` and read or drive the page. It belongs in debug builds only. This is MASTG-TEST-0227.

```bash
grep -rnE 'setWebContentsDebuggingEnabled' jadx_out/sources/
```

- **Pass**: debugging is off in release, or guarded by a `BuildConfig.DEBUG` check.
- **Fail**: it is enabled unconditionally in the production build.
- **Evidence**: the call site and whether a build guard wraps it.

## Dynamic Confirmation

Proxy the app with the setup in [Intercepting Mobile Traffic](/collections/mobile/intercepting-mobile-traffic) and drive every flow that shows a WebView. Note the URLs it loads and whether any arrive over HTTP or from a redirectable source. If web debugging is enabled, open `chrome://inspect` on the host with the device connected; the WebView appears there and confirms the exposure.

```bash
# With setWebContentsDebuggingEnabled(true), the WebView shows under chrome://inspect
```

- **Pass**: WebViews load only trusted HTTPS content, no bridge is reachable by that content, and DevTools shows nothing in release.
- **Fail**: a WebView loads attacker-influenceable content with a bridge or relaxed file access, or DevTools attaches in the production build.
- **Evidence**: the loaded URL in the proxy, and the DevTools session if debugging is exposed.

> **Note:** an app can also render web content without a WebView. A screen may download a file with its own HTTP client and render it with a native component such as a PDF renderer. That path has nothing to do with WebView settings, so review it separately, both for transport security and for the parser attack surface of whatever renders the bytes. For content the app itself serves into a WebView, the same header hardening as a web application applies, such as CSP and cookie security attributes on the served pages.

These checks sit under MASVS-PLATFORM-2, the control for how an app uses WebViews; the MASVS system and the testing profiles that set the bar are in [The OWASP MAS Project](/collections/mobile/mas-project).