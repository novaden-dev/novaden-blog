---
title: "Intercepting Android Traffic with Burp Suite"
slug: android-intercepting-traffic
category: notes
format: guide
handbook: mobile
tags: ["android", "web"]
draft: false
pubDatetime: 2026-09-15T00:00:00+03:00
description: "Getting an Android app's HTTPS through Burp: routing traffic to the proxy, installing the CA so the app trusts it, why Android 14 changed where that CA has to go, and defeating certificate pinning when the app still does not trust the proxy."
---

Most of what an Android app does is visible in its network traffic: how it authenticates, what data it sends back, which endpoints it talks to. Getting that traffic into Burp Suite takes three things to line up:

1. The app's traffic has to reach Burp.
2. The app has to trust Burp's certificate, or TLS breaks.
3. The app must not be pinning a certificate, or it rejects Burp regardless.

Work through them in order. Pinning bypass does not help if the routing is wrong.

## Prerequisites

A rooted device or emulator, set up as in [Android Lab Setup](/collections/mobile/android-lab-setup), and Burp Suite listening. Root is not strictly required for the routing step, but it is required to install the CA where modern Android will trust it, so assume it throughout.

## Step 1: Route Traffic to Burp

Point Burp's proxy at an interface the device can reach, then point the device at Burp.

In Burp: **Proxy** → **Proxy settings** → **Proxy listeners**. Either bind the listener to **All interfaces**, or bind it to your machine's LAN IP. Do not leave it on `127.0.0.1` for a physical device, because the device cannot reach your loopback.

Then route the device. Pick whichever of these fits your setup:

**Emulator, at launch.** Applies to all traffic on the emulator:

```bash
emulator -avd pentest -http-proxy 127.0.0.1:8080
```

**Any device, through Wi-Fi settings.** Long-press the connected network → **Modify** → **Advanced** → **Proxy: Manual**, then enter your machine's IP and Burp's port. Applies only to Wi-Fi, and some apps ignore it.

**Physical device, over ADB reverse.** No shared network needed. The device's own `localhost:8080` is tunnelled to Burp on your machine:

```bash
adb reverse tcp:8080 tcp:8080
adb shell settings put global http_proxy 127.0.0.1:8080
# undo with:
adb shell settings delete global http_proxy
```

To confirm routing works, open a plain HTTP site in the device browser. It should appear in Burp's HTTP history. At this point HTTPS will throw a certificate error on the device: that is expected, and the next step fixes it.

## Step 2: Make the App Trust Burp's CA

Burp generates its own CA and signs a fresh certificate for each site on the fly. The device rejects them because Burp's CA is not in its trust stores. So the CA has to be installed as trusted, and Android sorts trusted CAs into two stores that behave very differently:

- **User store**: what "install a certificate" in Settings writes to. Any app can install here, no root needed.
- **System store**: shipped with the OS, in `/system/etc/security/cacerts/`. Writing here needs root and a writable system partition.

Since **Android 7 (API 24)**, apps do not trust user-store CAs by default. An app trusts the user store only if its network security config opts in, which almost none do. So a user-store install is enough for the browser and for old apps, but for a real target you almost always need the CA in the system store.

### Export Burp's CA

**Proxy** → **Proxy settings** → **Import / export CA certificate** → **Certificate in DER format**. Save it, then convert to PEM:

```bash
openssl x509 -inform DER -in cacert.der -out cacert.pem
```

### The Quick Way: User Store

This is enough for browser traffic, and for apps that still trust the user store.

```bash
adb push cacert.pem /sdcard/Download/burp.crt
```

On the device: **Settings** → **Security** → **Encryption & credentials** → **Install a certificate** → **CA certificate** → accept the warning → pick the file. On some builds the path is **Settings** → **Security** → **Install from storage**.

If the target app now shows in Burp over HTTPS, you are done. If it fails, the app is ignoring the user store, so move to the system store.

### The Reliable Way: System Store (Android 7 to 13)

System CAs are stored under a filename derived from the certificate's subject hash, with a `.0` extension. Compute the filename, then copy the PEM into the store with that name:

```bash
# The filename Android expects
hash=$(openssl x509 -inform PEM -subject_hash_old -in cacert.pem | head -1)
echo "$hash"     # e.g. 9a5ba575

# Make the system partition writable, then install
adb root
adb remount
adb push cacert.pem /sdcard/burp.pem
adb shell su -c "cp /sdcard/burp.pem /system/etc/security/cacerts/${hash}.0"
adb shell su -c "chmod 644 /system/etc/security/cacerts/${hash}.0"
adb reboot
```

`subject_hash_old` (not `subject_hash`) is what Android uses; the wrong one gives a filename the system ignores. If `adb remount` fails, the emulator was not started with `-writable-system`, or verification was not disabled: both are covered in the lab setup note.

### Android 14 and Later

Android 14 moved the system CA store. It is no longer a plain directory you can drop a file into: the trusted CAs live in an APEX module (`/apex/com.android.conscrypt/`), and a plain file copy does not update them.

The practical answer is a Magisk module that overlays the CA into the runtime store. Options:

- **[Magisk-Trust-User-Certs](https://github.com/pnlts/Magisk-Trust-User-Certs)** and similar modules promote whatever you install in the user store into the system store at boot. Install the CA through Settings as usual, flash the module, reboot, and the user CA is now trusted system-wide.
- A **Frida or Objection runtime patch** (below) sidesteps trust stores entirely by changing the app's behaviour instead of the OS. On Android 14 this is often the fastest route.

### Confirm

Browse an HTTPS site on the device. It should now appear in Burp with no certificate warning. Check that the system store picked it up: **Settings** → **Security** → **Encryption & credentials** → **Trusted credentials** → **System** tab should list "PortSwigger" (or your CA's name).

## Step 3: Defeat Certificate Pinning

If HTTPS works in the browser but the target app's traffic never reaches Burp, or shows up as TLS errors, the app is pinning. Pinning means the app ships the certificate or public key it expects and checks the server against it directly. A CA the device trusts is not enough: the presented certificate has to be the pinned one, and Burp's is not.

You cannot satisfy a pin, only bypass it. Three routes:

### Objection

[Objection](https://github.com/sensepost/objection) wraps Frida with ready-made bypasses. With a Frida server running on the device (see [Dynamic Instrumentation with Frida](/collections/mobile/android-frida) for how to match versions and push the right build):

```bash
objection -g com.example.app explore
# then, at the prompt:
android sslpinning disable
```

It hooks the common pinning implementations at runtime: OkHttp's `CertificatePinner`, the default `TrustManager`, `WebViewClient`, and others. Traffic starts flowing into Burp without touching the APK. This works for most apps.

### Frida with a dedicated script

When Objection's generic hooks miss, a maintained script catches more implementations:

```bash
frida -U -f com.example.app -l frida-multiple-unpinning.js
```

The widely used one is `frida-multiple-unpinning` (search the CodeShare directory). If even that misses, the app is doing something custom: decompile it, find the class doing the check, and hook that method directly. Frida's own logging shows you which hooks fired and which did not.

### Patching the APK

When runtime hooking is blocked, or you need a device without Frida attached, patch the app itself and remove the pinning from its code:

1. Decompile with `apktool d app.apk`.
2. Add a network security config that trusts the user store, and point the manifest at it:

   ```xml
   <!-- res/xml/network_security_config.xml -->
   <network-security-config>
     <base-config cleartextTrafficPermitted="true">
       <trust-anchors>
         <certificates src="system" />
         <certificates src="user" />
       </trust-anchors>
     </base-config>
   </network-security-config>
   ```

   ```xml
   <!-- AndroidManifest.xml, on <application> -->
   android:networkSecurityConfig="@xml/network_security_config"
   ```

3. Repack, sign, and install. A repacked APK is unsigned, so it has to be signed with your own key (`keytool` to generate one, `apksigner` to sign) before Android will install it.

The config alone defeats apps that pin only through the network security config's `<pin-set>`. An app pinning in its own code needs the smali for that check edited out as well, or one of the runtime bypasses above instead.

## When Traffic Still Will Not Appear

| Symptom | Likely cause |
|---|---|
| Nothing in Burp at all, even HTTP | Routing. Listener bound to loopback for a physical device, or wrong IP/port on the device. |
| HTTP works, HTTPS shows TLS errors | CA not trusted. User-store install on an app that ignores it, or the wrong `subject_hash_old` filename. |
| Browser HTTPS works, the app does not | Certificate pinning. Go to step 3. |
| Works on Android 12, fails on Android 14 | The CA store move. Use a Magisk trust module, or a runtime bypass. |
| App uses a socket you never see | Not HTTP. gRPC, a raw TLS socket, or Flutter, which ignores the system proxy and needs a Frida-based approach of its own. |

Burp only sees HTTP(S). An app talking over a raw socket, or a Flutter app that bypasses the system proxy entirely, needs Frida to redirect its traffic, not a proxy setting.
