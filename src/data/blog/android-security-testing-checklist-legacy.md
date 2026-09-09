---
author: Kayra
pubDatetime: 2026-06-09T00:00:00Z
title: "Android App Security Testing Checklist (Legacy)"
slug: "android-security-testing-checklist-legacy"
description: "The original topic-organized Android testing checklist. Superseded by the MASVS-structured Mobile App Static Analysis — Android Checklist; kept as a migration source while its content is moved over control by control."
tags: ["android", "security", "checklist", "masvs"]
category: notes
draft: true
featured: false
---

> **Note:** Superseded. This is the original topic-organized checklist, being replaced by the MASVS-structured [Android App Security Testing checklist](/posts/mobile-app-security-testing). It is unpublished and kept only as a source to migrate worked content from, control by control, before it is deleted.

## Setup and Unpack

Decode the app before checking anything.

- Decode resources and the manifest with apktool. This is the authoritative manifest and resource source, because the manifest ships as compiled binary XML and apktool is the tool whose job is decoding it.

```bash
apktool d -f -o apktool_out TargetApp.apk
```

- Decompile the code to Java with jadx for reading logic.

```bash
jadx -d jadx_out --show-bad-code TargetApp.apk
```

> **Tip:** Use apktool for the manifest and resources, and jadx for the code. If jadx fails to resolve a manifest attribute it can drop it silently, and in an assessment one missing attribute flips a finding.

## Backups

Check whether app data can be backed up off the device.

```bash
grep -oE 'android:(allowBackup|fullBackupContent|dataExtractionRules)="[^"]*"' apktool_out/AndroidManifest.xml
```

What to look for:

- `allowBackup="false"` disables both Auto Backup and `adb backup`. This is a `PASS`.
- If backup is enabled, read the rule files it points to and see what is included.

```bash
cat apktool_out/res/xml/backup_rules.xml
```

- `fullBackupContent` applies on API 30 and below; `dataExtractionRules` governs on API 31 and above. An empty `<full-backup-content />` defines no excludes, so if backup were enabled the default set (essentially all app files) would be included.

Verdict: `PASS` if backup is disabled, or if it is enabled with explicit excludes that keep sensitive data out. `FAIL` if sensitive data can be backed up.

## Release Build

Confirm the app is shipped as a release build, not a debug or test build.

```bash
grep -oE 'android:(debuggable|testOnly)="[^"]*"' apktool_out/AndroidManifest.xml
```

What to look for:

- Neither `debuggable` nor `testOnly` should be present. Both default to false, which is what a release build looks like.

Verdict: `PASS` if both are absent or false. `FAIL` if `debuggable="true"` appears.

## Signing Certificate

Confirm the app is signed with a real release certificate.

```bash
apksigner verify --print-certs TargetApp.apk
```

What to look for:

- A genuine distinguished name (an organization and an owner). The Android debug keystore shows `CN=Android Debug, O=Android, C=US`, which is a `FAIL` for a production build.

Verdict: `PASS` on the verifiable part if the signature is a valid release certificate. Note that the rest of the requirement, that the signing private key is properly protected (for example Play App Signing or an HSM), is not visible from the APK and is out of scope for static analysis.

## Native Debug Symbols

If the app ships native libraries (`.so` files under `lib/`), confirm their debug symbols have been stripped. Symbol names and debug info are not needed at runtime, but they make reverse engineering much easier, because tools show real function names instead of generic offsets.

Check every library at once with a glob, you do not run them one by one. Check the strip status across every architecture.

```bash
file apktool_out/lib/*/*.so
```

What to look for:

- Each library should report `stripped`. A library that reports `not stripped` still carries its symbol table and is a `FAIL`.
- Confirm there is no DWARF debug info left behind. This loop prints a line only if a library still has `.debug` sections.

```bash
for so in apktool_out/lib/*/*.so; do
  readelf -S "$so" | grep -q '\.debug' && echo "DEBUG INFO: $so"
done
```

- A full symbol table dump should come back empty on a stripped library.

```bash
for so in apktool_out/lib/*/*.so; do
  echo "$so: $(nm "$so" 2>&1 | head -1)"   # "no symbols" means stripped
done
nm -D apktool_out/lib/arm64-v8a/libsigner.so   # dynamic symbols (imports/exports): always present, not a finding
```

> **Gotcha:** `nm -D` always lists the dynamic symbol table, because the linker needs it. Entries like `U __android_log_print` are required imports, not leftover debug symbols. Do not read them as "not stripped." Use `file` and plain `nm` for the verdict.

Verdict: `PASS` if every `.so` across all ABIs is stripped with no `.debug` sections. `FAIL` if any library is not stripped.

## Permissions

Confirm the app requests only the permissions it needs. List them from the manifest.

```bash
grep -E '<uses-permission' apktool_out/AndroidManifest.xml | grep -oE 'android:name="[^"]*"' | sort -u
```

What to look for:

- **Dangerous permissions that match a feature.** Camera, NFC, contacts, biometric, and similar are fine when a real feature uses them. Flag any that have no matching feature.
- **Ungrantable permissions.** A `signature` or `signature|privileged` permission such as `READ_PRIVILEGED_PHONE_STATE` is never granted to a normal app. It does nothing and should be removed. It is cruft, not impact.
- **Deprecated permissions.** Old permissions like `READ_PROFILE` have no effect on modern Android.
- **Broad visibility.** `QUERY_ALL_PACKAGES` lets the app enumerate every installed app and is treated as sensitive. If the app already declares a `<queries>` block, it should rely on that instead.
- **Legacy storage left uncapped.** `READ_EXTERNAL_STORAGE` and `WRITE_EXTERNAL_STORAGE` are redundant on API 30 and above (scoped storage) and superseded by `READ_MEDIA_IMAGES`. If they appear without an `android:maxSdkVersion` cap, they still grant broad shared-storage access on older devices. Prefer the Storage Access Framework or the Photo Picker, which need no permission.

```bash
grep -E '<uses-permission' apktool_out/AndroidManifest.xml | grep -iE 'EXTERNAL_STORAGE|QUERY_ALL|PRIVILEGED|maxSdk'
```

> **Note:** The permission alone is rarely the impact. Broad storage permissions only matter if the app actually writes sensitive data to shared storage, so confirm that in the data storage checks before rating it.

Verdict: `PASS` if the set is minimal and each permission maps to a feature. `FAIL` (usually low severity) if the app over-requests, for example uncapped legacy storage, ungrantable, deprecated, or broad-visibility permissions.

## Network Security Config

Check how the app handles TLS, cleartext, trust anchors, and pinning. Start with the network security config file.

```bash
cat apktool_out/res/xml/network_config.xml
```

What to look for:

- **Cleartext.** `cleartextTrafficPermitted="true"` in a `base-config` or `domain-config` allows non-TLS traffic. On a `domain-config` it is scoped to listed domains. Note that a `<domain>` value must be a hostname only. A value with a port, like `example.com:443`, is invalid and will not match, which is itself a misconfiguration.
- **Trust anchors.** A `<trust-anchors>` block that adds `<certificates src="user" />` lets the app trust user-installed CAs, which makes interception easier. System-only trust is the safe default.
- **Pinning.** A `<pin-set>` in the config pins certificates at the platform level. If there is no `pin-set` here, pinning may instead be implemented in code (for example OkHttp `CertificatePinner`), so check the code too.

Then check the code, because TLS behavior is often set there.

```bash
grep -rl 'CertificatePinner' jadx_out/sources/                 # pinning in code
grep -rlE 'checkServerTrusted|X509TrustManager|HostnameVerifier' jadx_out/sources/   # trust handling
```

- A custom `X509TrustManager` whose `checkServerTrusted` body is empty accepts any certificate (a trust-all manager). That disables TLS validation and is a high-severity finding if it runs on the production path.
- Trace any trust-all code to see whether it is actually used. It is common for it to be gated behind a build flag and only active in debug or test builds.
- Not every trust-all manager is flag-gated. A secondary feature, for example a document or file download, may build its own client with an empty trust manager and an always-true hostname verifier that runs unconditionally in the release build, even when the main API client validates and pins correctly. The requirement is that TLS is used consistently across the whole app, so enumerate every place an `SSLContext`, `OkHttpClient`, or `HostnameVerifier` is constructed, not just the primary networking layer, and confirm none of them disable validation. A `HostnameVerifier` whose `verify` method returns `true` accepts a certificate for any hostname and is the same class of defect as an empty trust manager.

The dangerous pattern to recognize is an empty trust manager:

```java
// Red flag: accepts ANY certificate, so TLS validation is effectively off.
class UnsafeTrustManager implements X509TrustManager {
    public void checkServerTrusted(X509Certificate[] chain, String authType) { /* empty */ }
    public void checkClientTrusted(X509Certificate[] chain, String authType) { /* empty */ }
    public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
}
```

The safe pattern is pinning, often with OkHttp:

```java
// Connections are refused unless the server cert matches the pin.
CertificatePinner pinner = new CertificatePinner.Builder()
    .add("api.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0=")
    .build();
OkHttpClient client = new OkHttpClient.Builder()
    .certificatePinner(pinner)
    .build();
```

Often the two paths are gated behind a build flag, and the verdict depends entirely on what that flag evaluates to in the production build:

```java
// Which branch runs is decided by the flag. Confirm the flag's value in the production APK.
if (config.isSslPinningEnabled()) {
    builder.certificatePinner(pinner);                 // secure path
} else {
    builder.sslSocketFactory(unsafeFactory, unsafeTm); // trust-all path
}
```

So tracing the flag to its declared default (and any code that sets it) is what tells you which path ships.

> **Gotcha:** Run code findings against the production build, not a tester build. If you are given a second APK with pinning removed so you can intercept traffic, its disabled pinning is an intended test modification, not a vulnerability. Confirm the relevant flag (for example a pinning-enabled boolean) in the production APK before rating anything. Reading the wrong build can turn an intended test change into a false critical finding.

Verdict: `PASS` if the production build uses TLS consistently and validates certificates (system trust, ideally with pinning), with no effective cleartext or user-CA trust. `FAIL` if validation is disabled on the production path, cleartext is permitted and used, or user CAs are trusted.

## Exported Components and Deep Links

Any component marked `android:exported="true"` can be launched by other apps, and any `<data android:scheme="...">` deep link can be triggered by a web page or another app. List both.

```bash
grep -E 'android:exported="true"' -B2 apktool_out/AndroidManifest.xml
grep -oE 'android:scheme="[^"]*"' apktool_out/AndroidManifest.xml | sort -u
```

What to look for:

- **First-party vs third-party.** Most exported components belong to SDKs (payment, auth, push) and are exported by design. Separate those from the app's own components, which are the real target.
- **Permission protection.** A component with `android:permission="..."` set to a signature-level permission is protected. An exported component with no permission is reachable by any app, so check what it does.
- **Launcher and deep-link activities** are exported by necessity. The question is not that they are exported, but what they do with untrusted input.

Then read the handler for each first-party deep link and exported component. Launch it with `adb` to test.

```bash
adb shell am start -a android.intent.action.VIEW -d "yourscheme://host/path?foo=bar"
adb shell am start -n com.example.app/.SomeExportedActivity
```

The key question for a redirect or callback deep link (for example a payment or login return URL) is whether it **trusts data in the URL** or only uses it as a **trigger**.

```java
// SECURE: the deep link is only a signal to re-check status with the server.
if (url.startsWith("app://result")) {
    viewModel.fetchStatusFromServer();   // truth comes from the backend
}

// INSECURE: trusts a status value from the attacker-controllable URL.
if (uri.getQueryParameter("status").equals("success")) {
    navigateToSuccessScreen();           // spoofable by anyone who fires the link
}
```

> **Note:** An exported activity lets a malicious app set intent extras directly, not just the URL. So "the deep link only triggers a server check" must hold even when an attacker controls every extra and query parameter. If the real decision is made server side, forging the link achieves nothing.

Also check the other direction: what an exported component **returns**. An exported `ContentProvider`, or an activity/service that hands data back, must not expose sensitive data to a caller that has no business reading it. So confirm exported components neither perform sensitive actions on untrusted input nor leak sensitive data out over IPC.

Verdict: `PASS` if first-party exported components and deep links either require protection or treat all incoming data as untrusted (no sensitive action without server-side verification or authentication), and expose no sensitive data over IPC. `FAIL` if an unprotected component performs a sensitive action, leaks sensitive data, or a deep link is trusted to decide a sensitive outcome.

## Native Code Memory Safety

This check is about memory handling in the app's own native (C/C++) code. First decide whether the app even has any.

```bash
ls apktool_out/lib/                                  # native libraries by ABI
grep -rnE '\bnative\b.*\(|System\.loadLibrary' jadx_out/sources/com/<app-package>/
```

What to look for:

- Native method declarations or `System.loadLibrary` calls in first-party packages mean the app ships its own native code to review.
- Bundled third-party `.so` files (for example a crypto or database engine) are not the app's code and cannot be reviewed at the source level.

Verdict: `N/A` if there is no first-party native code, only third-party libraries. If the app does have its own native code, this becomes a deeper review of allocation, bounds, and frees.

## Secure Randomness

Security-relevant values (tokens, IVs, salts, nonces) must come from a cryptographically secure RNG.

```bash
grep -rnE 'new Random\(|Math\.random\(|java\.util\.Random' jadx_out/sources/com/<app-package>/   # insecure
grep -rnE 'SecureRandom' jadx_out/sources/com/<app-package>/                                       # secure
```

What to look for:

- `java.util.Random` or `Math.random()` used for anything security relevant is a finding, those are predictable.
- `SecureRandom` is the correct choice.

Verdict: `PASS` if there is no insecure RNG in security contexts and `SecureRandom` is used where needed. `FAIL` if a predictable RNG generates security values.

## WebView JavaScript Bridge

A JavaScript bridge lets web content call into app code. Combined with remote or attacker-controlled content, that is remote code execution in the app's context.

```bash
grep -rn 'addJavascriptInterface' jadx_out/sources/com/<app-package>/
```

What to look for:

- No `addJavascriptInterface` in first-party code means no bridge is exposed, which satisfies this check.
- If a bridge exists, confirm the WebView only loads content shipped inside the app package, never remote URLs.

Verdict: `PASS` if there is no bridge, or a bridge exists but the WebView only renders in-package content. `FAIL` if a bridge is reachable from remote or untrusted content.

## WebView Configuration

Beyond the bridge, two settings decide how much a WebView can be abused: whether JavaScript is enabled, and which resource handlers are reachable. Find every WebView and read its `WebSettings`.

```bash
grep -rn 'getSettings()\|setJavaScriptEnabled\|setAllowFileAccess\|setAllowUniversalAccessFromFileURLs\|setAllowContentAccess\|setMixedContentMode\|loadUrl' jadx_out/sources/com/<app-package>/
```

What to look for:

- **JavaScript.** `setJavaScriptEnabled(true)` is not automatically a finding. The check is whether JavaScript is actually required. Rendering remote HTML pages legitimately needs it. The risk only becomes real when JavaScript is on **and** either a native bridge exists or the loaded URL is attacker-controlled. So pair this with the bridge check and with where the URL comes from.
- **URL trust.** Trace the loaded URL to its source. A hardcoded `https://` URL to a first-party domain is low risk. A URL taken from an intent extra, a deep link, or a server response is attacker-influenced and raises the stakes for everything else.
- **File and content handlers.** `setAllowFileAccess(true)`, `setAllowFileAccessFromFileURLs(true)`, `setAllowUniversalAccessFromFileURLs(true)`, and `setAllowContentAccess(true)` widen the attack surface to `file://` and `content://`. On API 30 and above `setAllowFileAccess` defaults to `false`, so the absence of these calls means the secure default applies. Setting them to `true` is the finding.
- **Mixed content.** `setMixedContentMode(MIXED_CONTENT_COMPATIBILITY_MODE)` (integer `2`) permits some HTTP subresources on an HTTPS page. `MIXED_CONTENT_NEVER_ALLOW` (integer `0`) is the hardened choice. Remember the constants decompile as integers.

> **Gotcha:** A WebView is not the only way an app fetches web content. A screen may instead download a file with its own HTTP client and render it with a native component (for example a PDF renderer). That path has nothing to do with WebView settings, so review it separately, both for transport security (see the network section) and for the parser attack surface of whatever renders the bytes.

Verdict: `PASS` if JavaScript is only enabled where required, loaded URLs are trusted, and no dangerous file or content handlers are enabled (secure defaults are fine). `FAIL` if dangerous handlers are enabled, or JavaScript is enabled alongside a bridge or attacker-controlled content.

## Background Screen Protection

When the app is backgrounded, Android captures the screen for the recents thumbnail, and screenshots are allowed, unless the window sets `FLAG_SECURE`. For an app showing balances, cards, or codes, that snapshot can leak.

```bash
grep -rn 'FLAG_SECURE\|setFlags(8192\|addFlags(8192' jadx_out/sources/com/<app-package>/
```

> **Gotcha:** Decompiled code shows framework constants as their integer value, not the name. `FLAG_SECURE` is `8192`, so `setFlags(8192, 8192)` is exactly `FLAG_SECURE`. Grepping only for the string `FLAG_SECURE` will miss it and produce a false "no protection" finding. Always grep the integer too.

What to look for:

- A per-activity `setFlags(8192, 8192)` (often centralized in an `ActivityLifecycleCallbacks.onActivityCreated` or a base activity) protects the whole app at once.
- Check it is applied unconditionally, not gated behind a flag that defaults to off.

Verdict: `PASS` if `FLAG_SECURE` is applied to the activities that show sensitive data (ideally app-wide). `FAIL` if sensitive screens are captured in the recents thumbnail. Confirm dynamically by opening a sensitive screen and viewing the app switcher.

## Tapjacking and Screen Overlays

A tapjacking attack draws an overlay on top of the app and tricks the user into tapping controls underneath while they think they are interacting with the overlay. Against a sensitive app this can induce unintended actions. The defense is to drop touches that arrive while a view is obscured.

```bash
grep -rn 'filterTouchesWhenObscured' apktool_out/res/                  # layouts and themes
grep -rn 'setFilterTouchesWhenObscured\|onFilterTouchEventForSecurity' jadx_out/sources/com/<app-package>/
```

What to look for:

- `android:filterTouchesWhenObscured="true"` on sensitive interactive views, or applied via a base layout or theme.
- Ignore hits inside bundled UI libraries (for example Material Design components), they do not cover the app's own sensitive screens.

> **Note:** Weigh this against the platform. Android 12 (API 31) and above already filters touches passing through another app's window by default, so the practical risk is mostly on older supported versions. It also requires a malicious app with the user-granted "display over other apps" permission. Treat a missing control here as a low-severity, defense-in-depth gap unless the app targets older devices heavily.

Verdict: `PASS` if sensitive screens drop obscured touches (or rely on platform filtering on a high enough minimum SDK). `FAIL` (usually low severity) if no overlay protection is present on sensitive screens.

## Sensitive Input Fields

Two related checks live on the input fields that handle secrets (passwords, PINs, CVV, OTP): the value should be masked, and the keyboard should not cache or suggest it.

```bash
grep -rE 'inputType' apktool_out/res/layout/<sensitive-screen>.xml
```

What to look for:

- **Masking:** sensitive fields use a password input type (`textPassword`, `numberPassword`, `textWebPassword`). That both hides the value on screen and disables suggestions.
- **No keyboard cache:** non-password sensitive text fields should add `textNoSuggestions` (or `textNoSuggestions|textVisiblePassword`) so the keyboard does not learn or autocomplete the value.

Verdict: `PASS` if every sensitive field is masked and disables suggestions. `FAIL` if a sensitive field uses a plain `text` type that caches input or shows the value.

## Cryptographic Algorithms

Check that the app does not use algorithms that are broken or deprecated for security use.

```bash
grep -rhoE 'Cipher\.getInstance\("[^"]*"\)|MessageDigest\.getInstance\("[^"]*"\)' jadx_out/sources/com/<app-package>/ | sort -u
grep -rnE '"DES"|"DESede"|"RC4"|"MD5"|"SHA-?1"|/ECB/' jadx_out/sources/com/<app-package>/
```

> **Gotcha:** Scope the grep to the app's own package. A repo-wide search lights up with `MD5`, `DES`, `ECB`, and `SHA-1` from bundled libraries (crypto providers, networking, analytics) that are not the app's code. Those are not first-party findings, filter them out before judging.

What to look for:

- Deprecated or broken: `DES`, `3DES`, `RC4`, `MD5`, `SHA-1` for signatures, and any `ECB` mode.
- Modern: `AES` in an authenticated mode (`GCM`) is best. `AES/CBC` is acceptable but unauthenticated, flag it for the deeper "appropriate parameters" review rather than as a deprecated-algorithm finding.

Verdict: `PASS` if first-party code uses only current algorithms. `FAIL` if it uses a deprecated or broken one.

## Object Deserialization

Deserializing untrusted data into objects is a classic remote-code path.

```bash
grep -rnE 'ObjectInputStream|readObject\(|implements Serializable|Externalizable' jadx_out/sources/com/<app-package>/
```

What to look for:

- Native Java serialization (`ObjectInputStream`/`readObject`) on data that crosses a trust boundary.
- Prefer data-only formats (JSON via a typed parser) over object deserialization.

Verdict: `N/A` if the app does no first-party object deserialization. `PASS` if deserialization exists but only on trusted, app-controlled data with safe APIs. `FAIL` if untrusted data is deserialized.

## Build Hardening (Study Further)

Confirm the free protections the build toolchain offers are switched on.

```bash
grep -rl 'JADX INFO: renamed from' jadx_out/sources/com/<app-package>/ | head   # R8/ProGuard ran
readelf -h libfoo.so | grep Type        # DYN = position independent
readelf -l libfoo.so | grep -E 'GNU_RELRO|GNU_STACK'   # RELRO + non-exec stack
nm -D libfoo.so | grep __stack_chk_fail # stack canary present
```

What to look for:

- **Bytecode minification (R8/ProGuard):** renamed members and shrunk code. Note that retained Kotlin `@Metadata` annotations can leak original names, which weakens obfuscation even when minification ran.
- **Native libraries:** position independent (`DYN`), with `RELRO`, a non-executable stack, a stack canary, and stripped symbols.

Verdict: `PASS` if minification is on and native libraries are hardened. `FAIL` if the build ships unminified bytecode or libraries without these protections.

## Anti-Tampering and Resilience (Study Further)

These are the runtime self-defense controls: detecting root, emulators, debuggers, and instrumentation tools, plus obfuscation and code packing. They are defense-in-depth, the security decision must still be enforced server side, but they raise the cost of attacking the client. Assess them in two halves: confirm a control exists statically, then test whether it actually responds and resists bypass dynamically.

Find the detection logic and where it is called from.

```bash
grep -rln 'RootBeer\|/system/xbin/su\|goldfish\|qemu_pipe\|isDebuggerConnected\|frida\|xposed' jadx_out/sources/
strings -a lib/*/*.so | grep -iE 'ptrace|frida|magisk|su\b'
```

What to look for:

- **Detection coverage:** root, emulator, debugger (both JDWP via `Debug.isDebuggerConnected()` and native anti-`ptrace`), and instrumentation frameworks (Frida, Xposed, Substrate). Missing categories are gaps, no Frida detection is common and significant.
- **Response:** find the call site and confirm it does something (terminate, block), not just compute a boolean. A one-time check at app start is weaker than continuous checks at sensitive actions.
- **Obfuscation of the defenses:** member renaming alone is not enough. Watch for these weakeners:

> **Gotcha:** Minification can run yet leave the defenses readable. Kotlin `@Metadata` annotations retain original names, and any class annotated `@Keep` is deliberately excluded from obfuscation. Security detector classes are often `@Keep`-annotated "to be safe," which ironically leaves them fully readable. Renamed members (a method like `a()`, a field like `b3`) do not mean the defense is protected.

- **Packing:** if the DEX decompiles to readable logic, it is not packed, regardless of renamed identifiers. Packing or code encryption is what stops trivial static analysis, member renaming is not.

For the dynamic half, attempt the bypass on a device you own: hook the Java checks (`File.exists`, `SystemProperties.get`, `Debug.isDebuggerConnected`) or run a public anti-detection script, and see whether the app still runs. If a generic script defeats it, the control is present but ineffective.

> **Reporting note:** Group these into a single resilience finding rather than one per control. Root, emulator, debugger, instrumentation, obfuscation, and packing gaps share one root cause, one impact, and one remediation, so they read as a single weakness in a report even though the checklist scores each control on its own row.

Verdict per control: `PASS` if detection exists and responds and resists a basic bypass, `BYPASSED` if it exists but was defeated, `FAIL` if absent. Expect to enforce critical decisions server side regardless.

## Dependency and CVE Review

An app inherits the vulnerabilities of every library it bundles. The goal is to inventory the third-party components, pin their versions, and check each against known CVEs. Most version information is left in the build artifacts.

```bash
# AndroidX and library version markers
for f in apktool_out/unknown/META-INF/*.version; do echo "$(basename "$f" .version) $(cat "$f")"; done
# Google and Firebase client versions
grep -r 'version=' apktool_out/unknown/*.properties
# Networking and crypto libraries often embed a version banner or BuildConfig
grep -rho 'okhttp/[0-9.]*' jadx_out/sources/okhttp3/
grep -rn 'VERSION_NAME' jadx_out/sources/ | grep -iv androidx
# Native library versions live in the .so strings
strings -a lib/arm64-v8a/*.so | grep -iE 'version [0-9]|/[0-9]+\.[0-9]+\.[0-9]+]'
```

What to look for:

- **Outdated or abandoned libraries.** Map each version to its CVE history. A version bump is not always the fix: if a library is abandoned, the patched code may live only in a maintained fork under a different artifact id, so the latest release of the original is still vulnerable.
- **Bundled SDKs carry their own dependencies.** A vendor SDK often ships an older copy of a common library inside it. A grep for a package at the top level (not relocated under the vendor namespace) suggests a normal transitive dependency, while relocated or shaded classes signal it is baked into the SDK.
- **Insecure configuration inside a dependency.** The library version is only half the story. Read how it is used. An SSH or SFTP client that sets `StrictHostKeyChecking` to `no` accepts any server key, which is the SSH equivalent of an empty trust manager. That is a finding regardless of the library version.
- **Pre-release dependencies in production.** Alpha or beta versions of security-sensitive libraries (for example a crypto or biometric library) in a release build are a maturity concern worth noting even when no CVE applies.

> **Gotcha:** When the vulnerable library is inside a closed third-party SDK, the app team often cannot fix it themselves. The library and any insecure configuration are compiled into the SDK, and it may not be on a public repository to override. In that case the realistic remediation is a vendor request for a patched SDK, plus compensating controls such as disabling the feature that reaches the vulnerable path. Say this in the report rather than recommending a simple version bump that is not possible.

> **Reporting note:** Identification and CVE-checking are scored as separate checklist rows but usually share one root cause and one remediation, so a single finding can cover both. Keep the rating proportionate to reachability: a vulnerable component on a path that is hard to reach, or that fails for an unrelated reason, is lower risk than one on a primary flow.

Verdict: `PASS` if all bundled components are identified and current with no known-vulnerable versions on reachable paths. `FAIL` if a bundled component has a known CVE or is abandoned, or a dependency is configured insecurely. Maintain a software bill of materials and run automated dependency scanning in CI so these surface at build time.

## Code and Data Integrity

This is a different control from root and emulator detection. Here the question is whether the app notices that it has been modified, either on disk (repackaged and resigned) or in memory (hooked at runtime). Two checklist rows cover the two surfaces: file or executable integrity, and memory integrity. They share one root cause, so a single finding usually covers both.

Look for any self-integrity logic at all.

```bash
# On-disk / signature integrity
grep -rn 'GET_SIGNATURES\|getSigningInfo\|GET_SIGNING_CERTIFICATES\|signatures' jadx_out/sources/com/<app-package>/
# Memory / runtime integrity and anti-hooking
grep -rn 'maps\|/proc/self\|checksum\|Xposed\|frida' jadx_out/sources/com/<app-package>/
# Is Play Integrity actually wired in, or just bundled?
grep -rln 'StandardIntegrityManager\|requestIntegrityToken' jadx_out/sources/com/<app-package>/
```

What to look for:

- **Runtime signature check.** Does the app read its own signing certificate and compare it to the expected developer certificate? If there is no such check, a resigned build runs unnoticed. Be precise: a `getPackageInfo` call with flag `0` only reads the version code, it is not a signature check. The flag must request signatures.
- **File checksums.** Any validation of the app's own DEX, resources, or critical sandbox data against known-good values. Usually absent.
- **Memory integrity.** Any scan of loaded modules, checksum of loaded code, or anti-hooking logic. This overlaps with instrumentation detection: if there is no anti-Frida logic, there is almost certainly no memory-tamper detection either.
- **Play Integrity wired in, not just present.** The Play Integrity library is often pulled in transitively by other Google components. Bundled is not the same as used. Confirm first-party code actually requests a token and that the server verifies the verdict, otherwise it provides no attestation.

> **Why resigning is the finding, not repackaging itself:** Every APK can be decompiled and rebuilt. The weakness is that the app does not detect it. Android requires a signature to install but not a specific one, and it only enforces that the same key is kept across updates. An attacker has no access to the developer key, so they must uninstall the genuine app and install their build as a fresh install signed with their own key. That means a tampered build always carries a different signer. The app cannot detect that it was uninstalled, because it runs no code while uninstalled, but it can detect the wrong signer the moment it checks. Today, nothing checks.

To demonstrate the on-disk case, repackage and resign with a throwaway key, then run it:

```bash
apktool d target.apk -o work
# change one visible thing, for example a launch-screen string, as a tamper marker
apktool b work -o tampered-unsigned.apk
zipalign -p -f 4 tampered-unsigned.apk tampered.apk
keytool -genkey -v -keystore t.keystore -alias t -keyalg RSA -keysize 2048 \
        -validity 10000 -storepass android -keypass android -dname "CN=PoC"
apksigner sign --ks t.keystore --ks-key-alias t \
        --ks-pass pass:android --key-pass pass:android tampered.apk
apksigner verify --print-certs tampered.apk    # confirm the signer is the throwaway key
adb install -r tampered.apk
```

If the resigned, modified app launches and runs normally, with the tamper marker visible and no termination or warning, the on-disk integrity control is absent. The injected marker only proves the running process is the modified build, it is not the attack itself.

> **Why this is usually Medium, not Critical:** These are defense-in-depth. The server still enforces authentication and authorization, so repackaging alone does not move money. It lowers the cost of distributing trojanised clones and of stripping the remaining client-side checks. The proper fixes are a runtime signature check (as one layer) plus server-side attestation with Play Integrity, so the backend rejects a non-genuine binary instead of trusting a client self-check.

Verdict: `PASS` if the app verifies its own signature or integrity and responds, ideally backed by server-side attestation. `FAIL` if a resigned or modified build runs undetected and no memory-tamper detection exists. Group the on-disk and in-memory rows into one resilience finding.

## Third-Party Data Sharing

The question here is what leaves the app to third parties, and whether that sharing is necessary. The usual suspects are analytics, crash reporting, and marketing-attribution SDKs (for example Adjust, AppsFlyer, Firebase Analytics). Find them and read what they actually transmit.

```bash
# Identify analytics / attribution SDKs wired into first-party code
grep -rln 'adjust\|appsflyer\|FirebaseAnalytics\|logEvent\|mixpanel\|segment\|branch' jadx_out/sources/com/<app-package>/
# Read what is attached to each event
grep -rn 'addPartnerParameter\|addCallbackParameter\|setRevenue\|putString\|logEvent' jadx_out/sources/com/<app-package>/
```

What to look for:

- **What is attached to events.** SDK event helpers reveal the payload. Watch for business identifiers (customer id, account id, transaction id) and amounts being attached to marketing events. Revenue and install attribution are normal; forwarding transaction-level references to a marketing platform usually is not.
- **Where it goes onward.** Some parameters are returned only to the app's own server callbacks, while others (often called partner parameters) are forwarded by the SDK to integrated ad networks. The second category is true third-party sharing.
- **Necessity.** The checklist allows sharing that is a necessary part of the architecture. Marketing analytics is a business choice, not core architecture, so the bar is whether the specific fields are needed for that purpose, not whether analytics in general is allowed.
- **Direct PII versus pseudonymous identifiers.** Confirm whether names, phone numbers, emails, government ids, account numbers, or credentials are sent. Their presence raises severity sharply.

> **Gotcha:** Pseudonymous is not the same as non-personal. A stable device or customer id tied to in-app events is still personal data under regimes like GDPR and the Saudi PDPL, because it can be linked back to an individual and joined to an advertising id the SDK collects on its own. So the absence of names and emails lowers the severity, it does not automatically make the sharing a non-issue, especially for a regulated app such as a bank.

> **Reporting note:** Rate this by what is actually sent. Direct PII or credentials to a third party is a real finding. Pseudonymous identifiers and amounts to a standard analytics SDK are usually an Informational data-minimization observation: worth recording, with a recommendation to minimize fields and confirm consent and a data-processing agreement, but not a security vulnerability on its own.

Verdict: `PASS` if only data necessary for the feature is shared and no sensitive data leaks to third parties. `FAIL` if direct PII or credentials are shared without need. Use an Informational note when the sharing is pseudonymous telemetry that is broader than necessary but not a sensitive-data exposure.

## Input Validation

This check spans every place untrusted data enters the app: user input from the UI, data from IPC such as intents and custom URL schemes, and data from the network. Static analysis splits into two halves: confirm validation exists on the inputs, and confirm there is no unsafe sink where unvalidated input causes injection.

```bash
# Validation infrastructure on UI inputs
grep -rln 'InputFilter\|TextWatcher\|android.util.Patterns\|isValid\|validate' jadx_out/sources/com/<app-package>/
# Injection sinks: raw SQL
grep -rn 'rawQuery\|execSQL\|SimpleSQLiteQuery' jadx_out/sources/com/<app-package>/
# Injection sinks: WebView rendering of dynamic content
grep -rn 'loadData\|loadDataWithBaseURL\|evaluateJavascript\|addJavascriptInterface' jadx_out/sources/com/<app-package>/
# IPC and deep-link inputs
grep -rn 'getStringExtra\|getData()\|getQueryParameter' jadx_out/sources/com/<app-package>/
```

What to look for:

- **UI validation.** Field validators, input filters, and restrictive input types on sensitive fields (amounts, card number, CVV, expiry, phone). A spread of `validate...` helpers per form is a good sign. Remember this is defense in depth; the server must validate too.
- **Network input handling.** Typed deserialization (for example Retrofit with Gson model classes) gives structural validation for free, and Retrofit encodes `@Query`/`@Path` parameters, so they do not concatenate into URLs unsafely. Confirm responses are not then fed to an unsafe sink such as a WebView rendering server-provided HTML.
- **IPC and custom URLs.** For exported components and deep links, the key question is not just whether the value is parsed, but whether a decision is made by trusting it. A deep link that only triggers a flow whose result is decided by a server call is safe; one whose parameters are trusted directly is not. See the exported-components and deep-links section.
- **Injection sinks.** Raw SQL built by string concatenation, ORM queries built from concatenated strings, file paths built from input (path traversal), and WebView bridges or dynamic HTML are the sinks that turn missing validation into a vulnerability. Their absence is most of the verdict.

> **Gotcha:** A long list of `validate...` methods is reassuring but is not the whole check. The decisive question for severity is whether any unsafe sink exists. An app with light UI validation but no injection sink is far safer than one with thorough UI validation that still concatenates a value into a raw SQL query. Look for the sink first.

Verdict: `PASS` if inputs are validated at the UI, untrusted IPC and deep-link values are not trusted for security decisions, and there are no injection sinks (raw SQL, unsafe ORM queries, path traversal, WebView bridges or dynamic HTML). `FAIL` if any unsafe sink consumes unvalidated external input.

## Data at Rest and Credential Storage

Sensitive data (tokens, passwords, PII, encryption keys) should live in the platform's protected facilities: the hardware-backed Android Keystore for keys, and an encrypted store such as `EncryptedSharedPreferences` for values. The common failure is a home-grown encryption layer that looks secure but is not. Find where keys come from and how values are stored.

```bash
# Keystore usage: hardware-backed vs software
grep -rn 'AndroidKeyStore\|KeyStore.getDefaultType\|KeyGenParameterSpec\|MasterKey\|EncryptedSharedPreferences' jadx_out/sources/com/<app-package>/
# Cipher configuration: algorithm, mode, IV
grep -rn 'Cipher.getInstance\|IvParameterSpec\|GCMParameterSpec\|SecretKeySpec' jadx_out/sources/com/<app-package>/
# Hardcoded key material and keystore passwords
grep -rn 'KEYSTORE_PASSWORD\|KEY_ALIAS\|"AES\|SecretKeySpec(' jadx_out/sources/com/<app-package>/
```

What to look for:

- **Hardware-backed keystore versus a software one.** `KeyStore.getInstance("AndroidKeyStore")` with `KeyGenParameterSpec` keeps keys non-exportable and bound to the device hardware. `KeyStore.getInstance(KeyStore.getDefaultType())` is a software BKS/PKCS12 keystore, usually persisted to a file and protected by an app-supplied password, so the key is exportable. That is a downgrade.
- **Hardcoded keystore passwords or keys.** A constant password protecting a file keystore, or a `SecretKeySpec` built from a literal or fixed-derived value, means anyone with the APK has the key. Confirm the constant is actually used and not overridden at runtime by a setter or remote value, the same trace you would do for any flag.
- **IV and nonce handling.** For GCM the nonce must be unique per encryption under a key. A fixed or all-zero IV (`new IvParameterSpec(new byte[16])`, or a constant byte array) is a severe misuse: it leaks plaintext relationships and can expose the GCM authentication subkey. GCM also expects a 12-byte nonce via `GCMParameterSpec`, not a 16-byte `IvParameterSpec`. For CBC, a fixed IV is also wrong, though less catastrophic than for GCM.
- **Plaintext stores.** Preferences DataStore and plain `SharedPreferences` are not encrypted. Tokens, PII, and credentials placed there sit in cleartext inside the sandbox. Inside the sandbox is better than external storage, but it is still not credential storage.

> **Gotcha:** An app can do the right thing in one place and the wrong thing in another. It is common to find biometric credentials correctly stored in `EncryptedSharedPreferences` with an Android Keystore master key, while the main token and PII storage is a custom layer with a hardcoded keystore password and a static IV. Review every storage path, not just the one that looks well built.

> **Reporting note:** Rate by reachability. Backups disabled and a sandbox boundary mean an attacker usually needs root, a forensic image, or escalation to reach these files, which keeps even a broken scheme at Medium rather than High in most cases. The cryptographic defects (hardcoded key material, nonce reuse) are still worth calling out precisely, because they remove the protection the design was supposed to provide.

Verdict: `PASS` if keys are in the Android Keystore and sensitive values are in an encrypted store with correct cryptographic parameters. `FAIL` if keys are in a software keystore with a hardcoded password, IVs or nonces are static, or tokens and PII sit in plaintext preferences. Group the storage-location, hardcoded-secret, and crypto-parameter rows into one finding when they stem from the same custom layer.

## Hardcoded Secrets and API Keys

Decompile the app and search the code and resources for embedded secrets. The manifest, `res/values/strings.xml`, `BuildConfig`, and constants classes are the usual homes.

```bash
# Common API key shapes and secret-looking constants
grep -rhoE 'AIza[0-9A-Za-z_-]{30,40}' apktool_out/                          # Google API keys
grep -rinE 'password\s*=\s*"|secret\s*=\s*"|api[_-]?key\s*=\s*"|token\s*=\s*"' jadx_out/sources/com/<app-package>/
grep -rn 'API_KEY\|KEYSTORE_PASSWORD\|SecretKeySpec(' apktool_out/AndroidManifest.xml jadx_out/sources/com/<app-package>/
```

What to look for:

- **Real secrets versus user input.** A `password` field in a request model's `toString()` is runtime user input, not a hardcoded secret. A constant assigned a literal password or key is the finding. Read the assignment, not just the keyword.
- **Keystore passwords and key material.** A hardcoded keystore password or a `SecretKeySpec` built from a literal value undermines whatever it protects. These belong with the data-at-rest finding.
- **Third-party SDK tokens.** Some SDK tokens (for example a marketing-attribution app token) are designed to live in the client and are low sensitivity. Note them, but rate them accordingly.

> **Gotcha:** Some keys are supposed to be in the app. A Maps SDK key cannot be hidden, it ships in the APK by design. So the finding for that kind of key is not that it is present, it is whether it is restricted. The fix is a restriction, not removal.

For client API keys that must ship (such as Maps), the real check is restriction:

- **Application restriction** ties the key to the app's package name plus its signing-certificate SHA-1, so it only works from the genuine signed app.
- **API restriction** limits the key to the specific services the app uses, so it cannot be reused against other endpoints.
- An unrestricted key, once extracted, can be used by anyone and billed to the project's account, which is quota and billing theft and can exhaust the budget that real users depend on. Confirm restriction status by using the extracted key from an unauthorized context and seeing whether it is accepted.

> **Reporting note:** A truly secret credential in the code (a server secret, a private signing key, a keystore password) is the serious case. An unrestricted but inherently-public client key is usually Medium, rated on billing and availability impact rather than data exposure. Separate the two; do not lump a public Maps key in with a leaked server secret.

Verdict: `PASS` if no confidential secrets are hardcoded and inherently-public client keys are properly restricted. `FAIL` if server secrets, credentials, or key material are embedded, or a shipped client key is unrestricted.

## Symmetric Encryption and Key Management

Beyond which algorithm is used, review how the key is sourced, how the IV is chosen, and whether one key serves multiple purposes. Find every symmetric cipher and read its key and IV.

```bash
grep -rn 'Cipher.getInstance\|SecretKeySpec\|IvParameterSpec\|GCMParameterSpec\|KeyGenerator' jadx_out/sources/com/<app-package>/
```

What to look for:

- **Hardcoded key as the sole protection.** A `SecretKeySpec` built from a literal string or constant byte array means the key ships in the APK. Anyone who decompiles the app has it, so the encryption is reversible by anyone. This is the defining failure of the no-hardcoded-keys requirement.
- **Client-side encryption of a credential with a hardcoded key.** An application-layer encryption envelope can be a legitimate defense-in-depth layer on top of TLS, and some organizations require one, so the goal is to fix it, not to remove it. The failure is doing it with a static key embedded in the app: that specific implementation adds no real protection, because anyone who decompiles the app has the key and can recover the value. Done properly, the layer must use a key that is not in the binary, such as a server public key or a per-session negotiated key, never a static embedded symmetric key, with a fresh random nonce per operation. Keep TLS with pinning as the primary transport protection underneath, and on the server store passwords as salted hashes (bcrypt/scrypt/Argon2), never recoverable ciphertext.
- **Static or zero IV.** A fixed IV makes encryption deterministic: the same plaintext always produces the same ciphertext, leaking equality. For CBC this removes semantic security; for GCM it is catastrophic (nonce reuse). Generate a fresh random IV/nonce per operation and store it with the ciphertext.
- **One key for many purposes.** Distinct uses (storing data at rest, encrypting a transmitted value, signing) should use distinct keys. A single key spread across unrelated purposes widens the blast radius if it leaks. Note that reusing one key across instances of the same purpose is far less of a concern than reusing it across different purposes.

> **Gotcha:** Separate the failures onto the rows they belong to. A standard JCA cipher (AES via the platform provider) is a proven implementation, so the proven-primitives row can still pass even when the same code hardcodes the key and uses a zero IV. Those are key-management and parameter failures, scored on their own rows, not implementation failures. Naming each precisely is more useful in a report than calling the whole thing broken crypto.

Verdict: `PASS` if keys are generated and stored properly, IVs and nonces are random and unique, and keys are scoped per purpose. `FAIL` if a key is hardcoded, an IV or nonce is static, or a single key is reused across unrelated purposes.

## Device-Access Security Policy

A sensitive app, especially a banking one, is expected to care whether the device has a secure lock screen at all. Two related checks cover this: enforcing a minimum device-access policy, and detecting or responding to a device with no lock. Both come down to one platform call.

```bash
grep -rn 'isDeviceSecure\|isKeyguardSecure\|KeyguardManager\|DevicePolicyManager' jadx_out/sources/com/<app-package>/
```

What to look for:

- **A keyguard check.** `KeyguardManager.isDeviceSecure()` returns whether the user has set a PIN, pattern, password, or secure biometric. If the app never calls it (or `isKeyguardSecure`), it neither enforces nor detects the absence of a device lock.
- **Where third-party hits come from.** Filter to first-party code. Biometric libraries and some SDKs reference these APIs internally; their presence in a bundled library does not mean the app enforces a policy. Confirm the call is in the application's own code and that it gates something.
- **The response.** If a check exists, see what it does: warn the user, require a lock before sensitive flows, or degrade. A check that computes a boolean and ignores it is not a control.

> **Gotcha:** These two checklist rows live in different categories (one under access policy, one under resilience), but in practice they share a single root cause and a single fix: the app does not look at `isDeviceSecure()`. Report them together rather than as two separate findings.

Confirm dynamically: remove the screen lock from a test device, launch the app, and see whether anything warns or blocks. If it runs normally with no lock, the control is absent.

> **Reporting note:** This is usually Low. The most sensitive actions are still authenticated server side, and hardware-backed keys can be bound to device credentials independently. The gap is the missing baseline device-posture check that a banking app is expected to enforce, not a direct path to compromise.

Verdict: `PASS` if the app checks `isDeviceSecure()` and enforces or warns when no secure lock is set. `FAIL` if there is no device-lock check anywhere in first-party code and the app runs normally on a device with no lock.

## Biometric Authentication Binding

When an app offers biometric login, the question is not whether a prompt appears but what the prompt actually gates. There are two designs. In the weak one, the prompt returns a boolean and the app trusts it: on success it reads a stored secret and proceeds. In the strong one, the successful biometric is what unlocks a Keystore key, and that key is what makes the secret usable, so there is no boolean to trust. The checklist requirement is that biometric auth is not event-bound and is instead based on unlocking the keystore.

```bash
grep -rn 'BiometricPrompt\|CryptoObject\|authenticate(\|setUserAuthenticationRequired\|setAllowedAuthenticators' jadx_out/sources/com/<app-package>/
```

What to look for:

- **A `CryptoObject` on `authenticate`.** The strong design calls `authenticate(promptInfo, cryptoObject)` where the `CryptoObject` wraps a `Cipher`, `Mac`, or `Signature` initialised with a Keystore key created using `setUserAuthenticationRequired(true)`. If the app calls `authenticate(promptInfo)` with no `CryptoObject`, no cryptographic operation is tied to the match, and success is just an event.
- **What the success callback does.** Read the `onAuthenticationSucceeded` path. If it ignores the `AuthenticationResult` and simply calls the next step (reads a saved password, navigates into the session), the result is event-bound. The result should be used: take the unlocked cipher from the `CryptoObject` and decrypt the credential with it.
- **The allowed authenticators.** A Keystore key with `setUserAuthenticationRequired(true)` can only be unlocked by strong biometrics (Class 3). If the prompt allows weak biometrics or device credential as well, that already rules out binding to such a key. Decode the integer flags, not just the named constants.
- **Whether the credential store itself is user-bound.** Even a correctly stored secret (for example in `EncryptedSharedPreferences`) is not gated on biometry unless the master key is built with user-authentication binding. A master key without it can be used any time the app runs, so the prompt protects nothing the app could not already read.

> **Gotcha:** The presence of `EncryptedSharedPreferences` or a Keystore-backed master key is not by itself proof of binding. Storing the credential at rest with a hardware-backed key is a different control from requiring the biometric to release it. Check both: the prompt must carry a `CryptoObject`, and the key that protects the secret must require user authentication.

Confirm dynamically on a rooted or instrumented device: hook the success callback and invoke it without presenting a biometric. If the session is established, the auth was event-bound. With a keystore-bound design the forced callback yields no usable key and the operation fails.

> **Reporting note:** This is usually Medium for an app guarding account access. Exploitation needs local instrumentation or device compromise, which holds the likelihood down, but the control is defeated by a single hooked callback, which is why it is not Low.

Verdict: `PASS` if the biometric prompt carries a `CryptoObject` over a `setUserAuthenticationRequired` Keystore key and the success path uses that key to release the secret. `FAIL` if `authenticate` is called with no `CryptoObject`, the success callback trusts a boolean, or the credential's master key is not user-authentication-bound.

## Debug Logging in Release Builds

Logging facilities meant for development have a way of surviving into the production build, and on a sensitive app they turn into a data-leak path. Two things to check: that no network inspector or verbose HTTP logger ships enabled in release, and that first-party log calls do not write user data. A frequent mistake is gating these on a mutable constant that defaults to on, rather than on the build type.

```bash
grep -rn 'ChuckerInterceptor\|HttpLoggingInterceptor\|Level.BODY\|Log\.\(d\|v\|i\|e\|w\)\|Timber\|setLogLevel' jadx_out/sources/com/<app-package>/
```

What to look for:

- **A network inspector in the release APK.** Tools that capture full HTTP traffic into an on-device store and a viewer are debug-only by design. If one is present and added to the client, the recent request and response bodies, including tokens and PII, sit in a local database readable with device access. This also undermines pinning for a local attacker, because the plaintext is already saved on the device.
- **HTTP body logging.** A logging interceptor set to the body level writes complete request and response headers and bodies to the device log. On the app's main client that means the login request, the authorization token on every call, and any PII the APIs return.
- **How the logger is gated.** The right gate is the build type, compiled out of release. A boolean constant that defaults to on, and that nothing ever sets off, is not a gate. Trace the flag to its source and confirm whether release actually disables it. Decode the value, do not trust the name.
- **First-party log calls with user context.** Search for direct log calls that interpolate user or flow data: deep-link URIs, payment return URLs, status payloads, entered form fields. These are usually unconditional, so they run in release regardless of any interceptor flag.
- **What is gated off versus on.** Be precise. Some verbose logging may be behind a flag that really is false in release (for example a separate test or staging toggle). Report only what is actually active, and note the gated-off ones as not exploitable, so the finding stays defensible.

> **Gotcha:** Other apps cannot read your logs on modern Android by default, which tempts a Low rating. But the log is still reachable over the debug bridge, in bug reports, by privileged logging components, and on rooted or forensic devices, and an on-device traffic inspector persists the data outright. Credentials and tokens in those places are a real leak, not a theoretical one.

Confirm dynamically: run the app through login and a sensitive action, then read the device log and any inspector UI and look for credentials, tokens, and PII in cleartext. If they appear, the control fails.

> **Reporting note:** The data exposure (credentials, session token, PII) is usually Medium because it needs local access to collect. The leftover developer code on its own is a separate, lower-severity hygiene point. They share a root cause and a fix, so report them together but score each on its own row.

Verdict: `PASS` if release builds ship no enabled network inspector or body-level HTTP logger and first-party logs carry no sensitive data. `FAIL` if a debug logger is active in release, or user data is written to the log.
