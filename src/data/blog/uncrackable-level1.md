---
author: Kayra
pubDatetime: 2026-11-01T00:00:00+03:00
title: "UnCrackable Level 1 Writeup"
slug: "uncrackable-level1"
category: notes
format: writeup
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "Solving OWASP UnCrackable Level 1: the Java check decrypts a hardcoded AES key and ciphertext, the root check that closes the app on a rooted emulator, and the plaintext secret it compares against."
---

UnCrackable Level 1 (`owasp.mstg.uncrackable1`) is the first crackme in the OWASP MASTG repository. It has one text field and one VERIFY button. A correct string shows `Success!` and anything else shows `Nope...`. The check is in Java, so jadx shows the whole path from the button to the comparison. There is no native library, no encrypted string table, and no Frida detection. The app also carries a root check that shows a dialog and exits when it finds a rooted device. That check is separate from the secret check: bypassing it only gets you to the input screen.

The APK is in the MASTG repository under `Crackmes/Android/Level_01`. Install it with `adb install -r UnCrackable-Level1.apk` and open `UnCrackable1` from the launcher.

![The UnCrackable Level 1 screen with the secret field and VERIFY button](/images/uncrackable-level1/app.png)

## The Root Check

`MainActivity.onCreate()` runs the anti-tampering checks before it sets the layout:

```java
if (c.a() || c.b() || c.c()) {
    a("Root detected!");
}
if (b.a(getApplicationContext())) {
    a("App is debuggable!");
}
super.onCreate(bundle);
setContentView(R.layout.activity_main);
```

`sg.vantagepoint.a.c` checks three things: `su` in `PATH`, `ro.build.tags` containing `test-keys`, and a list of Superuser files such as `/system/app/Superuser.apk` and `/system/xbin/daemonsu`. `sg.vantagepoint.a.b.a` reads the `debuggable` flag from `ApplicationInfo`. The `a(String)` method builds a non-cancelable dialog whose OK button calls `System.exit(0)`. If the check matches, the app closes from that dialog before the input screen is usable.

The `su` check is weaker than it looks. `c.a()` walks the `PATH` and calls `new File(dir, "su").exists()`, which runs under the app's UID. On the API 33 Google APIs image used here, `/system/xbin/su` is present, but `/system/xbin` is mode `0750` owned by `root:shell`. The app UID cannot traverse the directory, so `exists()` returns false and the check misses the binary. `Build.TAGS` is `dev-keys` rather than `test-keys`, and the Superuser paths are absent. A userdebug emulator can therefore run `frida-server` from an `adb root` shell and still pass all three checks without a hook. A production phone with no `su` and `release-keys` also passes all three.

The stock APK has `android:debuggable="false"`, so the debuggable alert can only fire after a rebuild with `android:debuggable="true"`. Both checks run once in `onCreate`; a process already past that method, or one started under the bypass script, shows neither dialog.

On a device where the check does fire, use a non-rooted device or hook the four methods before `onCreate` runs. ART can inline the small static checks, so call `Java.deoptimizeEverything()` before installing the hooks. A Frida spawn with this script sets every check to false:

```javascript
Java.perform(function () {
  Java.deoptimizeEverything();

  var c = Java.use("sg.vantagepoint.a.c");
  c.a.implementation = function () {
    return false;
  };
  c.b.implementation = function () {
    return false;
  };
  c.c.implementation = function () {
    return false;
  };

  var b = Java.use("sg.vantagepoint.a.b");
  b.a.implementation = function (context) {
    return false;
  };
  console.log("[+] hooks installed");
});
```

Save it as `bypass.js` and spawn the app:

```bash
frida -U -f owasp.mstg.uncrackable1 -l bypass.js
```

The [Frida note](/collections/mobile/frida) covers installing `frida-server` and matching the CLI version. The `-f` flag spawns the app with the script already loaded, so the hooks are in place for `onCreate`. If the dialog still appears before the hooks load, spawn with `--pause`, wait for `[+] hooks installed`, then run `%resume`:

```bash
frida -U -f owasp.mstg.uncrackable1 -l bypass.js --pause
```

This bypass does not reveal the secret. It only removes the dialog that blocks the input field.

To make the check fire naturally, put one of the Superuser files on a writable system image. `/system/app/Superuser.apk` is the simplest target. Start the emulator with `-writable-system`, remount, create the file, and relaunch:

```bash
emulator -avd api33 -writable-system
adb root
adb remount
# reboot once if adb asks, then run adb root and adb remount again
adb shell 'touch /system/app/Superuser.apk'
adb shell am force-stop owasp.mstg.uncrackable1
adb shell am start -n owasp.mstg.uncrackable1/sg.vantagepoint.uncrackable1.MainActivity
```

`c.c()` finds the file and shows the dialog. Remove it with `adb shell 'rm /system/app/Superuser.apk'` when you are done.

![The Root detected! dialog after creating /system/app/Superuser.apk on the emulator](/images/uncrackable-level1/root-dialog.png)

## The Check in MainActivity

The VERIFY button calls `verify(View)`:

```java
public void verify(View view) {
    String string = ((EditText) findViewById(R.id.edit_text)).getText().toString();
    AlertDialog alertDialogCreate = new AlertDialog.Builder(this).create();
    if (a.a(string)) {
        alertDialogCreate.setTitle("Success!");
        str = "This is the correct secret.";
    } else {
        alertDialogCreate.setTitle("Nope...");
        str = "That's not it. Try again.";
    }
    alertDialogCreate.setMessage(str);
    alertDialogCreate.setButton(-3, "OK", new DialogInterface.OnClickListener() {
        @Override
        public void onClick(DialogInterface dialogInterface, int i) {
            dialogInterface.dismiss();
        }
    });
    alertDialogCreate.show();
}
```

The call is `a.a(string)`, and jadx shows two classes named `a` in the path. The full name of the checker is `sg.vantagepoint.uncrackable1.a`. The crypto helper it calls is `sg.vantagepoint.a.a`. That second class is the AES routine, not the checker.

## The Checker

The checker decrypts a fixed ciphertext and compares the input to the plaintext:

```java
public static boolean a(String str) {
    byte[] bArrA;
    byte[] bArr = new byte[0];
    try {
        bArrA = sg.vantagepoint.a.a.a(
            b("8d127684cbc37c17616d806cf50473cc"),
            Base64.decode("5UJiFctbmgbDoLXmpL12mkno8HT4Lv8dlat8FxR2GOc=", 0)
        );
    } catch (Exception e) {
        Log.d("CodeCheck", "AES error:" + e.getMessage());
        bArrA = bArr;
    }
    return str.equals(new String(bArrA));
}

public static byte[] b(String str) {
    int length = str.length();
    byte[] bArr = new byte[length / 2];
    for (int i = 0; i < length; i += 2) {
        bArr[i / 2] = (byte) ((Character.digit(str.charAt(i), 16) << 4)
                + Character.digit(str.charAt(i + 1), 16));
    }
    return bArr;
}
```

![jadx-gui showing sg.vantagepoint.uncrackable1.a with the hex key, the Base64 ciphertext, and the equals comparison](/images/uncrackable-level1/jadx-checker.png)

`b()` is a hex decoder, not a hash. The 32-character string becomes a 16-byte key. `Base64.decode` turns the second string into 32 bytes of ciphertext. The helper does the rest:

```java
public static byte[] a(byte[] bArr, byte[] bArr2) {
    SecretKeySpec secretKeySpec = new SecretKeySpec(bArr, "AES/ECB/PKCS7Padding");
    Cipher cipher = Cipher.getInstance("AES");
    cipher.init(2, secretKeySpec);
    return cipher.doFinal(bArr2);
}
```

`cipher.init(2, secretKeySpec)` uses `Cipher.DECRYPT_MODE`. On Android, `Cipher.getInstance("AES")` resolves to AES/ECB/PKCS5Padding, and PKCS5 padding is the same as PKCS7 for a 16-byte block. The method decrypts the stored ciphertext and returns the plaintext. The checker compares your input to that plaintext with `str.equals(...)`, so the decrypted string is the secret. Nothing is hashed, and there is no key search to run.

| Item       | Value                                                                           |
| ---------- | ------------------------------------------------------------------------------- |
| Key        | `8d127684cbc37c17616d806cf50473cc` (16 bytes)                                   |
| Ciphertext | `5UJiFctbmgbDoLXmpL12mkno8HT4Lv8dlat8FxR2GOc=` (32 bytes after Base64 decoding) |
| Algorithm  | AES-128-ECB with PKCS7 padding                                                  |

## Decrypting the Secret

The two values are enough for `openssl`. `-K` takes the key as hex, which matches the key string in the app. `-aes-128-ecb` matches the 16-byte key and the ECB mode:

```bash
printf '%s' '5UJiFctbmgbDoLXmpL12mkno8HT4Lv8dlat8FxR2GOc=' \
  | base64 -d \
  | openssl enc -d -aes-128-ecb \
      -K 8d127684cbc37c17616d806cf50473cc
```

```text
I want to believe
```

CyberChef gives the same result: From Base64, then AES Decrypt with the key set as Hex, mode ECB, and the IV left empty. Enter the plaintext and tap VERIFY:

![The app showing Success! after entering I want to believe](/images/uncrackable-level1/success.png)

## Why the Check Fails

The APK ships the key and the ciphertext. The key is a string literal in the DEX (Dalvik Executable, the compiled bytecode in the APK) and the ciphertext sits beside it, so anyone with the APK can decrypt the value. The encryption keeps the plaintext out of a `strings` search; it does not protect the value. Moving to CBC with a random IV would not change the result, because the key still ships in the package and a static read still recovers both.

The comparison is also local. The app decides success on the device, so a patched branch or a hook on `a.a` produces the same dialog without knowing the plaintext. Save this as `success-hook.js`:

```javascript
Java.perform(function () {
  var checker = Java.use("sg.vantagepoint.uncrackable1.a");
  checker.a.implementation = function (input) {
    console.log("[+] verify called with: " + input);
    return true;
  };
  console.log("[+] hooked sg.vantagepoint.uncrackable1.a.a");
});
```

The check runs when VERIFY is tapped, so attaching to the running app is enough. Enter any string and tap VERIFY:

```bash
frida -U -n Uncrackable1 -l success-hook.js
```

If the app is not running, spawn it instead with `frida -U -f owasp.mstg.uncrackable1 -l success-hook.js`.

```text
[+] hooked sg.vantagepoint.uncrackable1.a.a
[+] verify called with: definitely-wrong
```

![The app showing Success! for the input definitely-wrong after hooking a.a](/images/uncrackable-level1/success-hook.png)

The hook replaces the checker's return value, so `verify()` takes the success branch and the AES decryption never runs. The input is printed and discarded. This is a bypass rather than the intended solve, and it shows that the check is not an authentication boundary. The root check has the same shape: it raises the effort on a rooted test device, but it does not protect the value in the APK.

## The Finding

The app stores a secret in a reversible form with the key next to it. This is the hardcoded-secret class, MASWE-0005. A client-side check that decrypts a bundled ciphertext with a bundled key is a static-analysis exercise.

- **Pass**: the app does not ship a reusable secret, and any value that must remain secret is checked by a server or held in the Android keystore.
- **Fail**: the APK contains the AES key and ciphertext, and the app compares the user input to the decrypted plaintext locally.
- **Evidence**: the checker in `sg.vantagepoint.uncrackable1.a`, the key `8d127684cbc37c17616d806cf50473cc`, and the decrypted string `I want to believe`.
