---
title: "Unpacking and Rebuilding with apktool"
slug: apktool
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-19T00:00:00+03:00
description: "apktool for Android: decoding an APK into a readable manifest, resources, and smali, patching what you find, rebuilding, signing, and getting the patched build installed."
---

An APK is a ZIP archive, and almost everything inside it is compiled: the manifest and every resource are binary XML, and the code is DEX bytecode (Dalvik Executable, the compiled format the Android runtime executes). apktool decodes all of that back into editable text and builds an installable APK again from your edits. It is the tool for changing an app. For reading one, use [Decompiling with jadx](/collections/mobile/jadx); the two work as a pair, and a patched build almost always starts as code you read in jadx.

Typical reasons to run it: adding a network security config so the app trusts your proxy, editing a check out of the smali, or embedding the Frida gadget in a build you can install on an unrooted device.

## Installing It

Major package managers include it:

```bash
# Debian, Ubuntu, Kali
apt install apktool
```

Or from apktool's GitHub releases: download the jar and the wrapper script, put both on your `PATH`, and make sure a JDK is installed. The jar needs Java 8 or later to run.

```bash
apktool --version
```

Keep this version recent. Decode failures on modern apps often come from an old apktool rather than a broken app, so check the version before you conclude the APK is the problem.

## Decoding an APK

```bash
# Decode into a directory named after the APK
apktool d app.apk

# Choose the output directory yourself
apktool d app.apk -o app-src

# Overwrite an output directory that already exists
apktool d app.apk -o app-src -f
```

You edit these files directly and rebuild the APK from the same directory when you are done. What each part holds:

| Path | Holds |
|---|---|
| `apktool.yml` | apktool's own metadata: the version that decoded the APK, SDK levels, framework info. `apktool b` reads it, so keep it. |
| `AndroidManifest.xml` | The manifest, decoded to readable XML. Read this copy, not jadx's. |
| `res/` | Decoded resources: layouts, `strings.xml`, `res/xml/` configs, menus, drawables. |
| `smali/`, `smali_classes2/`, ... | The code, disassembled to smali. One directory per dex, one file per class. |
| `assets/` | Raw bundled files, left unchanged. |
| `lib/` | Native `.so` libraries, left unchanged, one folder per CPU ABI. |
| `original/` | A copy of the original manifest and the signature apktool stripped out. |
| `unknown/` | Files apktool did not recognize, such as properties files. |

## The Manifest and Resources

Inside the APK the manifest is binary XML: the build compiler turned the text into a binary form that is smaller and faster to parse on the device, and a text editor only shows bytes. apktool decodes it back to text. apktool decodes the compiled resources in `resources.arsc` the same way.

The decoded manifest is the accurate copy. jadx also produces a manifest, but it can drop an attribute it fails to resolve, and a check like `android:exported="true"` turns on a single attribute. Read the manifest from the apktool output and use jadx for the code.

Once the manifest is text, the checks are greps:

```bash
# Exported components: the app's entry points from outside
grep -B2 'android:exported="true"' app-src/AndroidManifest.xml

# Requested permissions
grep '<uses-permission' app-src/AndroidManifest.xml

# Build flags that weaken the app
grep -oE 'android:(debuggable|allowBackup)="true"' app-src/AndroidManifest.xml

# Certificate pinning done through a network security config
grep -rn 'pin-set\|trust-anchors' app-src/res/xml/
```

## smali

smali is a text form of Dalvik bytecode, the same instructions the DEX holds, written out one file per class. jadx goes one step further and reconstructs Java; apktool stops at smali. You read smali when jadx produced nothing useful for a method, and you edit smali whenever you change the app's logic, because smali is what gets assembled back into DEX.

A method looks like this:

```smali
.method public static isRooted()Z
    .locals 2

    new-instance v0, Ljava/io/File;
    const-string v1, "/system/bin/su"
    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V
    invoke-virtual {v0}, Ljava/io/File;->exists()Z
    move-result v0

    return v0
.end method
```

Reading it piece by piece:

- `()Z`: takes no parameters and returns a boolean (`Z` is the bytecode's letter for boolean).
- `.locals 2`: the method uses two local registers.
- `v0`, `v1`: local registers. Parameters arrive in `p0`, `p1`, and so on (`p0` is `this` on instance methods).
- `new-instance v0, Ljava/io/File;`: makes an empty `File` object in `v0`.
- `const-string v1, "/system/bin/su"`: puts the path into `v1`.
- `invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V`: runs the `File` constructor on `v0` with `v1` as the argument.
- `invoke-virtual {v0}, Ljava/io/File;->exists()Z`: calls `exists()` on the file.
- `move-result v0`: puts the boolean answer into `v0`.
- `return v0`: returns it.

Patching a check usually means replacing a method body with the answer you want. If `isRooted()` scans for the `su` binary and you want the check to pass on a rooted device, the body becomes a single constant:

```smali
.method public static isRooted()Z
    .locals 1

    const/4 v0, 0x0    # always answer "not rooted"

    return v0
.end method
```

The same shape covers certificate-pinning checks, license checks, and most other boolean checks the app computes at startup: find the method, decide what answer you need, replace the body.

## Common Patches

### Manifest

- **Debuggable**: add `android:debuggable="true"` to the `<application>` tag to attach a debugger to the app.
- **Native libraries**: on an install error about extracting native libraries, set `android:extractNativeLibs="true"` on `<application>`, then rebuild and sign again.
- **Network security config**: point `android:networkSecurityConfig` at a config file that trusts the user certificate store, which routes the app's HTTPS into your proxy. The full config is in [Intercepting Traffic with Burp Suite](/collections/mobile/intercepting-mobile-traffic).

### smali

Replace the body of a method that returns a boolean you want to change: root detection, certificate pinning done in code, license checks. Find the class in jadx first (or grep the smali directly), edit the `.method` body, save.

### Resources

- `res/values/strings.xml`: hardcoded URLs, keys, and endpoints often live here.
- `res/raw/` and `assets/`: bundled JSON, JavaScript, or config files the app reads at runtime. Edit them like any text file.

## Rebuilding

```bash
# Build; apktool writes the APK to ./app-src/dist/
apktool b app-src

# Name the output yourself
apktool b app-src -o patched.apk
```

The build assembles your smali back into DEX and recompiles the resources. It does not recompile Java: apktool never produced Java, that was jadx.

Resource errors are the common build failure, and they almost always trace to an XML edit that broke the file, either your own or a decode artifact. Read the error, it names the file. If the build fails on resources you never touched, try the other resource compiler: recent apktool versions default to `aapt2` and accept `--use-aapt1`, older ones default to `aapt` and accept `--use-aapt2`. `aapt` is Android's resource-packaging tool, and the two versions differ in what XML they accept.

## Signing the Result

The rebuilt APK has no signature, because apktool stripped the original one when decoding. Android will not install an unsigned APK, so sign the build before installing:

```bash
# Once: generate a key to sign with
keytool -genkey -v -keystore research.keystore -alias research_key -keyalg RSA -keysize 2048 -validity 10000

# Align the ZIP, then sign
zipalign -f -p 4 patched.apk patched-aligned.apk
apksigner sign --ks research.keystore --ks-key-alias research_key \
  --out patched-signed.apk patched-aligned.apk
```

`zipalign` and `apksigner` ship with the Android SDK build-tools (`$ANDROID_HOME/build-tools/<version>/`). `zipalign` rearranges the ZIP so uncompressed parts sit on memory-page boundaries, and `apksigner` applies the modern signature schemes. Align first, sign second: the signature covers the whole file, so anything that rewrites the ZIP afterwards invalidates it. `jarsigner` also works, but it produces only the old v1 signature format, and Android 11 and later reject v1-only installs for apps whose target SDK is 30 or above, so use `apksigner`.

The signature is yours, not the developer's. Android treats it as a different app from the original: it cannot update the original build (uninstall the original first), and anything in the app that checks its own signing certificate will detect the change.

## Install Errors

| Error | Meaning and fix |
|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | The app is already installed, signed with a different key. Uninstall it first: `adb uninstall <package>`. |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES` | The APK is unsigned, or signed only with a scheme the device rejects. Sign with `apksigner`. |
| `INSTALL_FAILED_INVALID_APK: Failed to extract native libraries, res=-2` | The manifest keeps native libraries compressed where the device expects them extracted. Set `android:extractNativeLibs="true"`, rebuild, sign again. |
| `INSTALL_PARSE_FAILED_MANIFEST_MALFORMED` | A patched manifest or resource broke the XML. The message names the file; fix it and rebuild. |

## When Decode or Build Fails

| Symptom | Cause and fix |
|---|---|
| Decode dies on resource errors | The installed apktool is too old for the app's build tools. Upgrade to the latest release. |
| Decode works, build fails on resources you never touched | Try the other resource compiler (`--use-aapt1` / `--use-aapt2`). |
| Decoding a system or vendor app | Its resources reference the device's framework APK, which apktool does not ship. Pull `/system/framework/framework-res.apk` from the device and install it with `apktool if framework-res.apk`, then decode again. |
| Build output will not install | Work through the install error table above; most cases are signing. |

## Patching for Frida

Embedding the Frida gadget into an unrooted device's app follows the same loop: decode, add the gadget library, patch the smali so the app loads it, rebuild, sign, install. `objection patchapk -s app.apk` does the whole sequence in one command, and the manual steps, including the smali it needs, are in [Dynamic Instrumentation with Frida](/collections/mobile/frida).

## Where It Fits

jadx and apktool answer different questions, and an assessment uses both:

| Task | Tool |
|---|---|
| Manifest, permissions, exported components | apktool's decoded manifest |
| Reading logic, crypto, and auth code | jadx |
| A method jadx could not decompile | that class's smali in the apktool output |
| Editing and rebuilding the app | apktool |
| Behavior at runtime | Frida |

Read in jadx, edit in apktool, sign, and install over ADB ([Android Debug Bridge](/collections/mobile/android-adb)).
