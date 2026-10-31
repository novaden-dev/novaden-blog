---
title: "MHL SecureNotes Lab Writeup"
slug: mhl-securenotes-lab
category: notes
format: writeup
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-10-31T00:00:00+03:00
description: "Solving the Mobile Hacking Lab SecureNotes challenge: an exported content provider with no permission, a four-digit PIN used as the PBKDF2 input for an AES key, and an offline search that recovers the PIN and the flag."
---

The SecureNotes app (`com.mobilehackinglab.securenotes`) is a single-screen PIN checker. It takes a four-digit PIN, sends it to an exported content provider, and the provider decrypts a secret with a key derived from that PIN. The app never stores the PIN. The ciphertext, salt, IV, and iteration count ship inside the APK, the provider is exported without a permission, and the PIN space is 10,000 values, so the flag can be recovered by searching that space.

## The App and the Provider

MainActivity has three views: `pinEditText`, `submitPinButton`, and `resultTextView`. The button handler reads the PIN and calls `querySecretProvider(pin)`, which builds the provider URI and sends the PIN as part of the selection string:

```java
Uri uri = Uri.parse("content://com.mobilehackinglab.securenotes.secretprovider");
String selection = "pin=" + pin;
Cursor cursor = getContentResolver().query(uri, null, selection, null, null);
```

The query returns a cursor with a single `Secret` column, and the activity writes that value to `resultTextView`. When the cursor is null, it shows `[ERROR: Incorrect PIN]`.

The manifest declares the provider exported with no permission:

```xml
<provider
    android:name="com.mobilehackinglab.securenotes.SecretDataProvider"
    android:enabled="true"
    android:exported="true"
    android:authorities="com.mobilehackinglab.securenotes.secretprovider"/>
```

`android:exported="true"` with no `android:permission` means any app on the device, or `adb shell`, can query it. The [Exported Components and the IPC Attack Surface](/collections/mobile/android-exported-components) note covers the manifest rules. The application is also `android:debuggable="true"`, which allows Frida and `run-as`, but neither is needed for the offline route.

![The SecureNotes app with the PIN field and Submit button](/images/mhl-securenotes-lab/app-empty.png)

## The PIN Is the Key

There is no comparison between the entered PIN and a stored value. The APK does not contain the PIN; the provider treats it as key material:

```java
String pin = StringsKt.removePrefix(selection, "pin=");
String formatted = String.format("%04d", Integer.parseInt(pin));
String secret = decryptSecret(formatted);
```

`decryptSecret` derives a 256-bit AES key with PBKDF2-HMAC-SHA1, a password-based key derivation function, then decrypts the ciphertext with AES-CBC and PKCS#5 padding:

```java
PBEKeySpec keySpec = new PBEKeySpec(pin.toCharArray(), salt, iterationCount, 256);
SecretKeyFactory keyFactory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
byte[] key = keyFactory.generateSecret(keySpec).getEncoded();

Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new IvParameterSpec(iv));
byte[] plaintext = cipher.doFinal(encryptedSecret);
return new String(plaintext, Charsets.UTF_8);
```

A correct PIN derives the key that decrypts the ciphertext to valid padding and readable plaintext. A wrong PIN derives a different key, `doFinal` throws `BadPaddingException`, the method returns null, and the activity shows `[ERROR: Incorrect PIN]`. The encrypted secret is what separates a correct PIN from a wrong one, and the PIN is the only unknown.

PKCS#5 padding validation, the check that the final AES block is filled correctly, is not a PIN check. About one in 256 wrong keys produces valid padding by chance, so a wrong PIN can return a row of garbage instead of the error. On this ciphertext, 44 PINs passed the padding check; only one produced printable text.

## The Crypto Material in the APK

The provider's `onCreate` loads `assets/config.properties` and Base64-decodes four values:

```properties
encryptedSecret=bTjBHijMAVQX+CoyFbDPJXRUSHcTyzGaie3OgVqvK5w=
salt=m2UvPXkvte7fygEeMr0WUg==
iv=L15Je6YfY5owgIckR9R3DQ==
iterationCount=10000
```

The same file is readable by unzipping the APK:

```bash
unzip -o com.mobilehackinglab.securenotes.apk -d apk_out
cat apk_out/assets/config.properties
```

With the ciphertext, salt, IV, and iteration count available locally, the only missing input is the PIN. The UI limits the field to four digits (`android:maxLength="4"` and `android:inputType="number"`), and the provider pads the parsed integer to four digits with `%04d`, so the practical search space is `0000` through `9999`.

## Offline Key Recovery

The search runs on the host without the device. The script below uses the values from `config.properties`, tries every PIN, decrypts, and keeps only candidates with valid padding and printable ASCII:

```python
#!/usr/bin/env python3
import base64
import hashlib

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

enc  = base64.b64decode("bTjBHijMAVQX+CoyFbDPJXRUSHcTyzGaie3OgVqvK5w=")
salt = base64.b64decode("m2UvPXkvte7fygEeMr0WUg==")
iv   = base64.b64decode("L15Je6YfY5owgIckR9R3DQ==")

for i in range(10000):
    pin = f"{i:04d}"
    key = hashlib.pbkdf2_hmac("sha1", pin.encode(), salt, 10000, 32)
    try:
        plaintext = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(enc), 16)
    except ValueError:
        continue

    if all(32 <= b < 127 for b in plaintext):
        print(f"PIN: {pin}")
        print(f"Plaintext: {plaintext!r}")
```

The output is:

```text
PIN: 2580
Plaintext: b'CTF{D1d_y0u_gu3ss_1t!1?}'
```

![The offline script printing PIN 2580 and the flag](/images/mhl-securenotes-lab/offline-bruteforce.png)

The `unpad` call rejects wrong keys that produce invalid PKCS#5 padding. The printable-ASCII check removes the 43 remaining padding collisions. The only candidate that decrypts to readable text is `2580`.

The script does not need to know the flag format. The first run used padding and printability, then the plaintext itself showed the `CTF{...}` prefix. Checking for `b"CTF{"` directly is faster, about 12 seconds instead of about 45 on this host, but that check assumes the format is already known.

## The Flag

The offline search returns `2580`. One query against the exported provider confirms that the recovered PIN decrypts the secret in the app:

```bash
adb shell content query \
  --uri content://com.mobilehackinglab.securenotes.secretprovider \
  --where "pin=2580"
```

```text
Row: 0 Secret=CTF{D1d_y0u_gu3ss_1t!1?}
```

![The SecureNotes app showing the recovered flag after submitting 2580](/images/mhl-securenotes-lab/app-flag.png)

The exported provider and the four-digit PIN were the only protection. The ciphertext, salt, and IV were in the APK, so the PIN was recoverable with a local loop over 10,000 values.
