---
title: "Dynamic Instrumentation with Frida"
slug: android-frida
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-15T00:00:00+03:00
description: "Frida for Android: how injection works, matching frida-server to the device, spawning and attaching, writing hooks to read and rewrite an app's behaviour at runtime, Objection for the common jobs, and Gadget when the device is not rooted."
---

Static analysis tells you what an app could do. Frida tells you what it does, while it runs. It injects a JavaScript engine into a running process, so you can read arguments and return values, replace method implementations, dump decrypted buffers, and call the app's own functions, all without touching the APK. Most of the other dynamic tools (Objection, half the SSL-unpinning scripts) are built on it.

## How It Works

Frida has two parts that talk over a socket:

- **frida-server**: a native binary running as root on the device. It does the actual injection and hosting of the instrumentation engine.
- **The client**: `frida`, `frida-ps`, `frida-trace` and the Python bindings on your machine. You write instrumentation in JavaScript; the client ships it to the server, which runs it inside the target process.

Injection means Frida loads its engine into the target's address space, so your script runs with the app's own permissions and sees its memory directly. That is why frida-server needs root, and why the client and server versions must match exactly.

There are two ways to get a script into a process:

- **Attach**: hook a process that is already running. You miss everything that happened at startup, including early certificate-pinning setup and key derivation.
- **Spawn**: start the app under Frida, paused, inject, then resume. This is what you want most of the time, because important setup, such as certificate pinning and key derivation, happens before the first screen appears.

## Installing the Client

Frida is a Python package. Install it with pip:

```bash
pip install frida-tools        # frida, frida-ps, frida-trace, frida-discover
frida --version                # note this number, the server must match it exactly
```

`objection` (below) pulls in `frida` as a dependency, so installing it gets you both.

## Installing frida-server on the Device

Two rules decide which binary you download: it must match the client version, and it must match the device's CPU architecture.

```bash
# The client version the server has to match
frida --version                                  # e.g. 16.5.9

# The device architecture, which picks the binary
adb shell getprop ro.product.cpu.abi             # arm64-v8a, x86_64, ...
```

An x86_64 emulator needs the `x86_64` build; a physical phone almost always needs `arm64`. Grab the matching `frida-server-<version>-android-<arch>.xz` from Frida's GitHub releases, then stage and run it:

```bash
# Unpack and push to the one place shell can execute from
unxz frida-server-16.5.9-android-x86_64.xz
adb push frida-server-16.5.9-android-x86_64 /data/local/tmp/frida-server
adb shell chmod 755 /data/local/tmp/frida-server

# Run it as root, in the background
adb shell "su -c '/data/local/tmp/frida-server &'"    # Magisk root
# or, on an adb-rooted emulator:
adb root && adb shell "/data/local/tmp/frida-server &"
```

Check that the client and server are talking:

```bash
frida-ps -U                    # -U = USB/local device; lists running processes
```

If `frida-ps -U` lists processes, the client and server are connected. If it reports a version mismatch, the client and server versions differ and must match exactly. If it cannot connect, frida-server is not running as root.

## Finding the Target

```bash
frida-ps -U                    # everything
frida-ps -Ua                   # only running apps, with their identifiers
frida-ps -Uai                  # all installed apps, running or not
```

The identifier (`com.example.app`) is what you pass to spawn; the numeric PID is for attaching to a process that is already running.

## Running a Script

Use spawn:

```bash
# Spawn the app under Frida and load a script
frida -U -f com.example.app -l hook.js

# Attach to a running process instead
frida -U -n com.example.app -l hook.js

# No script, an interactive console in the process
frida -U -f com.example.app
```

`-f` spawns and pauses until your script is in place, then resumes. `-n` attaches to a running process by name. Without `-l`, Frida opens an interactive console in the process where you can try a hook before saving it to a file.

## Writing Hooks

Everything below runs inside the app. `Java.perform` waits for the runtime to be ready, then gives you the app's classes.

### Trace a Method

See every call, its arguments, and its result, without changing behaviour:

```javascript
Java.perform(function () {
  const Login = Java.use("com.example.app.LoginManager");
  Login.checkPassword.implementation = function (pw) {
    console.log("[+] checkPassword called with: " + pw);
    const result = this.checkPassword(pw);   // call the original
    console.log("[+]   -> returned: " + result);
    return result;
  };
});
```

Replacing `implementation` swaps the method for your function. Calling `this.checkPassword(pw)` runs the original code, so the app behaves as before. Overloaded methods need `.overload("java.lang.String")` before `.implementation` to pick the signature.

### Change a Return Value

Make a check the app runs return the value you want. Root and jailbreak detection is the classic case:

```javascript
Java.perform(function () {
  const Root = Java.use("com.example.app.security.RootDetector");
  Root.isDeviceRooted.implementation = function () {
    console.log("[+] isDeviceRooted() -> forcing false");
    return false;
  };
});
```

### Read Objects and Dump Buffers

```javascript
Java.perform(function () {
  const Crypto = Java.use("com.example.app.Crypto");
  Crypto.decrypt.implementation = function (data) {
    const clear = this.decrypt(data);
    console.log("[+] decrypted: " + clear);   // plaintext, before it is used
    return clear;
  };
});
```

To read data the app protects with TLS without breaking the TLS itself, hook the point right after decryption or right before encryption.

### Enumerate Loaded Classes

When you do not yet know the class name:

```javascript
Java.perform(function () {
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (name.toLowerCase().includes("login")) console.log(name);
    },
    onComplete: function () {},
  });
});
```

`frida-trace -U -f com.example.app -j '*!*login*'` does the same discovery from the command line, generating a stub handler for every matching method.

## Objection

[Objection](https://github.com/sensepost/objection) wraps Frida with a ready-made command menu, so common jobs like SSL pinning bypass or root detection bypass are one command instead of a script. With frida-server running:

```bash
objection -g com.example.app explore
```

At its prompt:

```text
android sslpinning disable                # defeat certificate pinning
android root disable                      # bypass common root checks
android hooking list classes              # enumerate loaded classes
android hooking search classes login      # find classes by keyword
android hooking watch class com.example.app.LoginManager   # trace every method
android keystore list                     # dump the app's KeyStore entries
memory dump all app_memory.bin            # dump process memory to a file
```

Use Objection first for pinning and root bypass. Drop to a hand-written Frida script only when its generic hooks miss. That, along with getting the app's HTTPS into a proxy, is covered in [Intercepting Android Traffic with Burp Suite](/collections/mobile/android-intercepting-traffic).

## When the Device Is Not Rooted: Gadget

No root means no frida-server. The alternative is **Frida Gadget**: a shared library you embed in the app itself, so Frida loads when the app starts instead of being injected from outside. That means repackaging the APK.

The practical route is `objection patchapk`, which does the whole sequence:

```bash
objection patchapk -s app.apk
```

It needs `apktool`, `zipalign`, and `apksigner` on your `PATH`. The command decompiles the APK, adds the gadget library matching the app's ABI, patches the smali so the app loads it at startup, then repacks and signs. Install the output:

```bash
adb install app.objection.apk
```

If you need to do it by hand instead, the steps are:

1. Decompile with `apktool d app.apk`.
2. Download the Frida gadget release matching the app's ABI (for example `frida-gadget-16.5.9-android-arm64.so` from Frida's GitHub releases), unpack it, rename it to `libfrida-gadget.so`, and place it in `lib/arm64-v8a/`. Android only loads libraries whose name starts with `lib` and ends in `.so`, which is why the rename is required.
3. Patch the smali of a class that loads early, the app's `Application` class or its main activity, so it calls `System.loadLibrary("frida-gadget")`. In smali, that call looks like:

   ```smali
   const-string v0, "frida-gadget"
   invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
   ```

4. Repack with `apktool b app/`, sign with `apksigner`, and install.

The downside of either route: you are now instrumenting a modified, re-signed build rather than the original one, so anything checking the APK signature will notice. On a rooted device, frida-server avoids all of that.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `frida-ps -U` shows a version mismatch | Client and frida-server versions differ. They must be identical. |
| `unable to connect to remote frida-server` | Server not running, or not running as root. Re-launch it with `su -c`. |
| Server dies the moment it starts | Wrong architecture binary. Re-check `ro.product.cpu.abi`. |
| App detects Frida and exits | Anti-Frida checks (the `frida` string, port 27042, the gadget in memory). Spawn rather than attach, rename the server, and hook the detection method itself. |
| Hook never fires | Wrong class or overload, or the class is not loaded yet. Enumerate loaded classes to confirm the name, and spawn so you catch it early. |

Anti-Frida detection is common in hardened apps. Hook the detection method itself first, and the rest of your scripts can run from there.
