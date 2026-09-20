---
title: "Decompiling with jadx"
slug: jadx
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-19T00:00:00+03:00
description: "jadx for Android: turning an APK's bytecode back into readable Java from the CLI and the GUI, searching the tree for secrets and weak crypto, what the error count means, and when to fall back to smali, native tools, or Frida."
---

jadx decompiles an APK's code back into Java. The code in an APK is DEX bytecode (Dalvik Executable, the compiled format the Android runtime executes), which no processor runs directly, and jadx reconstructs Java source from it. The reconstruction is best effort rather than exact: a decompiler cannot always recover what the original source looked like, so expect imperfect code in places. Reconstructed Java is what you read to follow an app's logic; smali and disassembly are the fallbacks. It is usually the first tool you open after pulling the APK off a device.

It runs two ways, and each has its own job:

- **The CLI (`jadx`)**: writes the whole decompilation to disk as a source tree you can `grep` across. This is how you sweep an app for a pattern.
- **The GUI (`jadx-gui`)**: a browser for the same output. Read a single class here, search across the app, and follow cross-references to see who calls what.

## Installing It

Major package managers include it:

```bash
# Debian, Ubuntu, Kali
apt install jadx
```

Or from jadx's GitHub releases: the zip ships launch scripts for `jadx` and `jadx-gui` that need a Java runtime on your `PATH`.

```bash
jadx --version
```

## Decompiling from the CLI

```bash
# Decompile everything (code and resources) into a directory
jadx -d jadx_out app.apk

# Code only, skip decoding the resources
jadx -d jadx_out --no-res app.apk

# Print partial code for methods that failed, instead of an empty stub
jadx -d jadx_out --show-bad-code app.apk

# More threads, useful on large apps
jadx -d jadx_out -j 8 app.apk
```

A full run on a commercial app takes a minute or two and ends with a line like `finished with errors, count: 4`. That count is normal, not a failure of the run. A handful of methods did not decompile cleanly, usually because the build obfuscated them or used constructs the decompiler does not handle; the rest of the tree is complete and searchable. Treat the error count as a note that some methods will need the smali instead.

What the output holds:

| Path | Holds |
|---|---|
| `jadx_out/sources/` | The Java, one folder per package. Third-party libraries ship inside the APK too, and they are decompiled alongside the app's own code. |
| `jadx_out/resources/` | The manifest and decoded resources. |

One caveat on the resources: jadx's decoded manifest can silently drop an attribute it fails to resolve. A check like `android:exported="true"` turns on a single attribute, so read the manifest from [Unpacking and Rebuilding with apktool](/collections/mobile/apktool) instead and use jadx for the code.

Start in the app's own package, which the manifest's `package` attribute names, for example `sources/com/example/app/`. The rest of the tree is third-party libraries: sweep it with the same greps, and spend your line-by-line reading time in the app's own package.

## Searching the Tree

The CLI output exists so `grep` can sweep it. The productive patterns:

```bash
# Hardcoded secrets: keys, tokens, endpoints
grep -rnE '(api[_-]?key|secret|token|password)\s*=\s*"' jadx_out/sources/

# Crypto to review: weak algorithms, hardcoded ciphers
grep -rnE 'Cipher\.getInstance\(|MessageDigest\.getInstance' jadx_out/sources/

# Certificate pinning, by implementation
grep -rln 'CertificatePinner\|X509TrustManager' jadx_out/sources/

# Root, emulator, and instrumentation checks
grep -rlnE 'frida|/system/xbin/su|RootBeer|isDebuggerConnected' jadx_out/sources/

# WebView bridges: native methods scripts in the WebView can call
grep -rn 'addJavascriptInterface' jadx_out/sources/

# External input: where the app reads intents other apps sent it
grep -rn 'getIntent()' jadx_out/sources/

# What the app writes to logcat
grep -rn 'Log\.[dviwe]\(' jadx_out/sources/com/example/
```

Each match is a place to start reading and not a finding on its own. Pattern-based sweeps produce false positives, and a finding needs the surrounding code to make sense of it.

## The GUI

```bash
jadx-gui app.apk
```

The left panel is a tree of packages and classes, the main pane shows the decompiled Java of whatever you select, and the APK's decoded resources sit alongside the code. What it adds over a flat source tree:

- **Global search**: search across all classes, with options to include resources. Include them: hardcoded secrets sit in `strings.xml`, `res/raw/`, and `assets/` as often as in code.
- **Find usage**: right-click a method or field and list every caller. This is how you trace an exported component from the manifest to the code that handles it, or trace a pinning flag to the value it enforces.
- **Deobfuscation**: Tools > Deobfuscation renames obfuscated identifiers (`a.a.a`) to stable unique names so search results stay usable across sessions. It assigns new names; the original ones are not recoverable because the APK does not contain them.
- **Copy as Frida snippet**: right-click a class or method and pick the Frida option to copy a ready-to-run hook for it. When a method computes something you want at runtime, such as a routine that decrypts a hardcoded key, paste the snippet into the Frida console, adjust the arguments, and run the method instead of replicating its work by hand.
- **Export**: save the whole decompilation as a Gradle project you can open in Android Studio or another IDE, useful when you want an IDE's navigation on top of jadx's.

A practical loop: sweep with `grep` on the CLI tree until you have candidate classes, then read those classes in the GUI and use Find usage to walk outward from them.

## Comparing Two Versions

When an app update breaks a setup or adds a new check, decompile both versions and diff the source trees:

```bash
jadx -d old_out old.apk
jadx -d new_out new.apk
diff -ru old_out/sources new_out/sources > changes.diff
```

The raw diff is noisy: obfuscated names shift between builds, so whole files show as changed when only a few classes did. Start with the app's own package (the manifest's `package` attribute names it) and ignore the third-party libraries. Opening both folders in an editor with a folder-compare view, such as VS Code with its compare extension, makes the real changes easier to pick out than raw diff output.

## Native Libraries

jadx reads bytecode only. Code inside the `lib/*.so` files, C/C++ built with the NDK, does not appear anywhere in the output. An app that calls `System.loadLibrary("secret-lib")` ships that logic in a `.so`, and jadx shows you nothing but the load call. Three ways at it:

- **Ghidra**: open the `.so` in Ghidra and reverse the routine from the disassembly.
- **`strings`**: `strings libsecret-lib.so | grep -iE 'key|secret|token'` finds values stored as plain literals in the binary. It costs one command, so run it before opening Ghidra.
- **Run the library yourself**: build a small app that loads the same `.so` and calls the same function. Copy the `.so` into the PoC project's `jniLibs`, recreate the Java class with the same package and method name as the app's (JNI resolves native methods by package, class, and function name), and call it exactly as the app does. The library runs on your device and returns its result, so you read the output without reverse-engineering the binary at all.

## Obfuscation

Commercial apps are built with an obfuscator, usually R8 or ProGuard, which renames classes, methods, and fields to short names. You will see packages like `a.b.c` and methods like `a()`. Two consequences:

- **Strings survive.** Renaming touches identifiers, not string literals, so the searches above still work.
- **Reading takes more work.** The reconstructed Java remains, with meaningless names in place of the originals, and the originals are gone from the APK. Deobfuscation gives the names stability across sessions; it does not restore the original names.

When obfuscated logic is too dense to read as Java, use that class's smali in the apktool output instead: the bytecode listing is shorter than the Java and has no decompiler artifacts in it.
