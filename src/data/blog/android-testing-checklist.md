---
author: Kayra
pubDatetime: 2026-09-24T00:00:00+03:00
title: "Android Testing Checklist"
slug: "android-testing-checklist"
category: notes
handbook: mobile
format: checklist
tags: ["android"]
draft: true
featured: false
description: "Per-control checks for testing an Android app against OWASP MASVS: what to run on a decompiled APK and on a running device, with the verdict criteria and the evidence to capture."
---

A per-control checklist for testing an Android app against [OWASP MASVS](https://mas.owasp.org/MASVS/). Each control lists the checks that belong to it: the static pass reads a decompiled APK, the dynamic pass works against the app running on a device, and every check ends in a verdict plus the evidence to save. The system behind the controls (MASVS, MASWE, MASTG, testing profiles) is in [The OWASP MAS Project](/posts/mas-project).

The chapter covers the MASVS groups whose checks are finished, currently MASVS-PRIVACY and MASVS-AUTH. Checks for other groups get added here as they are completed.

## Setting Up the Checks

The checks below read from two states of the same app:

- **Static**: the decompiled APK. `apktool d` produces the decoded manifest and resources, `jadx` produces readable Java sources. Both outputs feed every static check.
- **Dynamic**: the app installed and running on a device or emulator. The install and traffic capture commands are in [Android ADB](/posts/android-adb) and [Intercepting Mobile Traffic](/posts/intercepting-mobile-traffic).

## MASVS-PRIVACY-1: The App Minimizes Access to Sensitive Data and Resources

### Dangerous permissions (MASTG-TEST-0254)

Check the permissions the app declares against the [dangerous permissions](https://developer.android.com/reference/android/Manifest.permission) Android defines.

From the APK, without decompiling:

```bash
# Declared permissions, straight from the APK
aapt d permissions app.apk
```

From the installed app, which also shows granted versus denied at runtime:

```bash
# Requested permissions plus their grant status
adb shell dumpsys package <package> | grep -A10 "requested permissions"
```

- **Verdict**: the check fails when a dangerous permission is declared and no feature of the app justifies it. Context decides: `CAMERA` is expected in an app that scans QR codes, and unnecessary in an app with no camera feature.
- **Watch for the alternative**: apps can reach the same functionality through intent actions without holding the permission, for example `ACTION_IMAGE_CAPTURE` captures a photo without the `CAMERA` permission.
- **Evidence**: the declared permissions list, and for each dangerous permission the workflow that uses it.

## MASVS-PRIVACY-3: The App is Transparent About Data Collection and Usage

The prerequisite for this group is the app's public declarations: the [Data Safety section](https://support.google.com/googleplay/android-developer/answer/10787469) of its Google Play listing, and its privacy policy where one exists. The checks find what the app actually collects and shares; the diff against the declarations is the finding.

### SDK entry points for data collection (MASTG-TEST-0318)

Static check: identify the third-party SDKs bundled in the app, read each SDK's documentation for the methods that receive user data, and find the call sites in the decompiled code. Google Analytics for Firebase is the canonical example: `FirebaseAnalytics` exposes `setUserId`, `setUserProperty`, and `logEvent`, each of which carries user data out of the app.

```bash
# Call sites of a data-collection entry point in the decompiled sources
grep -rn "setUserProperty\|logEvent" jadx_out/sources/
```

- **Verdict**: the check fails when the app calls SDK methods that can carry sensitive user data.
- **Limit**: this proves potential sharing only, from code presence. Confirmation at runtime is the next check.
- **Evidence**: the call sites, with the SDK and method each belongs to.

### Runtime use of SDK APIs (MASTG-TEST-0319)

Dynamic counterpart to the previous check: hook the SDK entry points while the app runs, then exercise as many flows as possible and enter sensitive data wherever the app accepts it. Method hooking is covered in [Frida](/posts/frida).

```bash
# Watch the values that reach an SDK entry point at runtime
frida-trace -U -f <package> -j 'com.google.firebase.analytics.FirebaseAnalytics.logEvent'
```

- **Observation**: the call sites, the stacktrace that leads to each call, and the argument values passed at runtime.
- **Verdict**: the check fails when sensitive values reach the SDK methods.
- **Evidence**: the stacktrace and the argument values, which name both the code path and the data.

### Undeclared PII in traffic (MASTG-TEST-0206)

Dynamic check: capture all traffic the app produces (decrypted HTTPS included) while using it, and enter PII wherever the app accepts it. How the capture is set up is in [Intercepting Mobile Traffic](/posts/intercepting-mobile-traffic).

- **Verdict**: the check fails when PII you entered appears in the capture and is not declared in the Data Safety section or the privacy policy.
- **Evidence**: the traffic capture with each PII finding annotated, next to the declarations it contradicts.
- **Follow-up**: the capture does not identify the code that sent the data. Locating the sending code is the static and dynamic analysis covered by the two checks above.

## MASVS-AUTH-2: The App Performs Local Authentication Securely According to Platform Best Practices

Local authentication on Android is biometric authentication backed by the Android Keystore. `BiometricPrompt` shows the system dialog and returns the result, and Keystore keys can be bound to that authentication so the key only unlocks after a successful biometric check. The five checks below cover the ways that binding can be weakened.

### Biometric fallback to device credentials (MASTG-TEST-0326)

`BiometricPrompt.Builder.setAllowedAuthenticators` decides which authenticators the prompt accepts. Including `DEVICE_CREDENTIAL` (alone, or combined like `BIOMETRIC_STRONG | DEVICE_CREDENTIAL`) lets the user authenticate with the PIN, pattern, or password instead of a biometric. The passcode is weaker than a biometric: it can be observed when entered (shoulder surfing) and it is easier to hand over or guess.

```bash
# Allowed authenticator configurations in the decompiled sources
grep -rn "setAllowedAuthenticators\|setDeviceCredentialAllowed" jadx_out/sources/
```

- **Scenario**: an attacker shoulder-surfs the victim's PIN, steals the phone, and opens the banking app with the PIN. The biometric requirement was meant to tie access to the user's physical presence; a passcode is a secret that can be learned once and reused.
- **Verdict**: the check fails when a sensitive flow allows `DEVICE_CREDENTIAL`. Context decides: a banking app should require the biometric itself, a note-taking app may accept the passcode.
- **Watch for the alternative**: `setDeviceCredentialAllowed(true)` is the deprecated equivalent and fails the same way.
- **Watch for the integer form**: decompiled code shows the constants as numbers, not names. `32783` is `BIOMETRIC_STRONG | DEVICE_CREDENTIAL` (`15 | 32768`).
- **Evidence**: the call sites with the authenticator constants each one uses.

### Event-bound authentication without a CryptoObject (MASTG-TEST-0327)

`BiometricPrompt.authenticate` has two forms. With a `CryptoObject` (a `Cipher`, `Signature`, or `Mac`), the prompt unlocks a Keystore key created with `setUserAuthenticationRequired(true)`: the biometric check is bound to the cryptographic operation out of process, and there is no success boolean an attacker can forge. Without a `CryptoObject`, the app decides what to do in the `onAuthenticationSucceeded` callback, and that callback can be overwritten so the app believes authentication succeeded.

```bash
# Where the prompt is shown and how it is called
grep -rn "BiometricPrompt\|\.authenticate(" jadx_out/sources/
# Whether any Keystore key enforces user authentication
grep -rn "setUserAuthenticationRequired" jadx_out/sources/
```

- **Scenario**: an attacker hooks the app (for example with Frida) and forces `onAuthenticationSucceeded` to fire without any biometric check. The app only trusts that callback, so it releases the token. With a `CryptoObject`, the Keystore key stays locked without a real biometric check, so there is no callback to forge.
- **Verdict**: the check fails for a sensitive operation when `authenticate` is called without a `CryptoObject` and no key is generated with `setUserAuthenticationRequired(true)`.
- **Evidence**: the `authenticate` call sites with their arguments, plus the key generation parameters.

### Keys that survive biometric enrollment changes (MASTG-TEST-0328)

A Keystore key bound to biometrics is invalidated by default when a new biometric is enrolled: the key only works for the fingerprints and faces that existed when it was created. An attacker who knows the passcode can add their own fingerprint in system settings, and `setInvalidatedByBiometricEnrollment(false)` keeps the key usable for that new fingerprint.

```bash
grep -rn "setInvalidatedByBiometricEnrollment" jadx_out/sources/
```

- **Scenario**: an attacker who knows the passcode adds their own fingerprint in system settings, then unlocks the vault with their finger. With the default `true`, the key dies the moment the enrollment changes and the attacker is stuck; with `false`, the key keeps working for the newly enrolled fingerprint.
- **Verdict**: the check fails when `false` is passed for a key that protects sensitive data.
- **Evidence**: the key generation call sites with the flag value.

### Authentication without explicit user action (MASTG-TEST-0329)

Passive biometrics (face) succeed the moment they are recognized, which takes no deliberate action from the user. `setConfirmationRequired(true)`, the default, adds a confirmation step: after recognition the prompt shows a button the user must tap. With `false`, the prompt succeeds on recognition alone, so a camera pointed at an unlocked or sleeping face unlocks the app.

```bash
grep -rn "setConfirmationRequired" jadx_out/sources/
```

- **Scenario**: the victim uses face recognition. The attacker points the phone at the victim's face while they sleep or are distracted, and the app unlocks on recognition alone. With confirmation required, the prompt demands a deliberate tap the victim will not give.
- **Verdict**: the check fails when the app sets `setConfirmationRequired(false)` for a sensitive operation such as a payment or account access. The default passes; look for the explicit `false`.
- **Evidence**: the call sites with the flag value.

### Keys with an extended authentication validity window (MASTG-TEST-0330)

For a Keystore key bound to user authentication, the validity window decides how long the key stays usable after one successful check. `setUserAuthenticationParameters(duration, type)` (and the deprecated `setUserAuthenticationValidityDurationSeconds`) takes the window in seconds:

```java
// 0: every cryptographic operation needs a fresh biometric check
new KeyGenParameterSpec.Builder("vault_key", PURPOSE_ENCRYPT | PURPOSE_DECRYPT)
    .setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
    .build();

// 300: one check unlocks the key for the next 5 minutes
new KeyGenParameterSpec.Builder("vault_key", PURPOSE_ENCRYPT | PURPOSE_DECRYPT)
    .setUserAuthenticationParameters(300, KeyProperties.AUTH_BIOMETRIC_STRONG)
    .build();
```

With a nonzero window, anyone holding the device can trigger operations that use the key without biometric verification until the window expires. A short window (seconds) is acceptable when several related operations run in quick succession; minutes or hours are not for sensitive data.

```bash
grep -rn "setUserAuthenticationParameters\|setUserAuthenticationValidityDurationSeconds" jadx_out/sources/
```

- **Scenario**: a banking app sets a 24-hour validity window (`86400` seconds). The victim authenticates once in the morning, the attacker steals the phone at noon, and the key is still unlocked, so payments go through with no biometric until the window expires. With duration 0, the thief is stopped at the first payment.
- **Verdict**: the check fails when a key protecting sensitive data is configured with a duration above 0.
- **Evidence**: the key generation call sites with their durations.

> The remaining MASVS groups (storage, crypto, network, platform, code, resilience) join this chapter as their checks are completed.
