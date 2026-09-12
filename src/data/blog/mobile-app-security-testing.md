---
author: Kayra
pubDatetime: 2026-07-06T00:00:00Z
title: "Android App Security Testing: Static and Dynamic"
slug: "mobile-app-security-testing"
description: "A per-control security-testing checklist for Android apps against OWASP MASVS: how to unpack the app, and for each control the static checks (from a decompiled APK) and the dynamic confirmation (on a running device), with PASS and FAIL conditions and the evidence to capture."
tags: ["android", "security"]
category: notes
draft: true
featured: false
---

A per-control security-testing checklist for Android apps against [OWASP MASVS](https://mas.owasp.org/MASVS/). Each control pairs a static pass (worked from a decompiled APK) with a dynamic pass (worked against the app running on a device): the static checks find the breadth, the dynamic checks confirm what only shows up at runtime. For the concepts behind it (static versus dynamic analysis, the MASVS profiles, why you always analyze the production build, and why scanner output is a lead rather than a verdict), start with [Mobile Security Testing Foundations](/posts/mobile-security-testing-foundations). This is the Android counterpart to the [iOS checklist](/posts/mobile-app-security-testing-ios); the two mirror each other control for control.

## Setting Up the Static Pass

Before any control, you need the app in a readable form. "Decompiling" is not one action: an APK is made of several parts, and each needs a different tool to become readable. That is why the setup runs two tools, not one, and produces two output trees that the rest of the checklist reads from.

### What an APK actually is

An APK is a ZIP. Unzip it and the parts are there, but most are not human-readable yet:

- `AndroidManifest.xml`: the app's declaration (package name, components, permissions, build flags). Stored as **binary XML**, so a text editor shows garbage.
- `classes.dex`, `classes2.dex`, …: the app's compiled code, as **Dalvik bytecode**. Not source.
- `resources.arsc` and `res/`: compiled resources and layouts, also largely binary.
- `assets/`: raw bundled files, sometimes configs, keys, or JavaScript for WebViews.
- `lib/`: native `.so` libraries, one folder per CPU ABI (`arm64-v8a`, `armeabi-v7a`, …).
- `META-INF/`: the v1 signature. The v2 and v3 signatures live in a signing block outside the entries.

### apktool: manifest, resources, and smali

`apktool` decodes the binary manifest and resources back into readable form, and disassembles the DEX bytecode into **smali**, a low-level text transcript of the bytecode. It is not pretty, but it is a faithful record of what the app does, and apktool's decoded manifest is the authoritative one.

```bash
# Decode manifest + resources (binary XML -> readable) and disassemble to smali
apktool d target.apk -o apktool_out
```

### jadx: readable Java

`jadx` takes the same DEX bytecode and decompiles it up to **Java source**. This is what you read to follow logic: a pinning flag, a cipher construction, a biometric callback. Decompilation to Java is a best-effort reconstruction, not a lossless reversal, so obfuscated or unusual methods fail. That is why jadx almost always ends with `finished with errors, count: N`. This is normal: a handful of methods did not fully decompile, and the rest of the tree is complete and searchable.

```bash
# Decompile DEX -> Java source tree
jadx -d jadx_out target.apk
```

You will use jadx two ways. The CLI (above) writes a source tree to disk that you can `grep` across, which is how you sweep for a pattern. `jadx-gui` is for reading a single class and following cross-references ("who calls this?"), which is how you trace a flag to its production value.

### Why run both

**jadx gives you readable logic; apktool gives you the true manifest, the resources, and a ground-truth fallback for anything jadx could not decompile.** They answer different questions:

- Manifest posture, permissions, exported components, resource strings: **apktool**.
- Reading business logic and crypto or auth code quickly: **jadx**.
- A method jadx renders as broken or empty: drop to that class's **smali** in the apktool output. The bytecode transcript is always there even when the Java reconstruction is not.

Neither alone is enough. jadx on its own means trusting a lossy decompile with a weaker manifest; apktool on its own means reading smali for everything, which is punishing for logic.

### Supporting tools

These do not read app logic; they cover the parts jadx and apktool do not.

- `apksigner verify --print-certs` (or `keytool`): read the signing certificate, the signature scheme (v1, v2, v3), the signer identity, and whether it is a debug certificate.
- `strings`, `nm -D`, `readelf`: inspect the native `.so` files in `lib/` for exported symbols and hardcoded strings, for when logic has been pushed into native code.

### Run order

Order matters here, because later steps depend on the outputs of earlier ones.

1. **Get the APK.** From the client, or pull it off a device: `adb shell pm path <pkg>` to find its path, then `adb pull <path>`. If it arrives as split APKs from an App Bundle, merge them first.
2. **Run `apktool d`** to produce the manifest, resources, and smali tree.
3. **Run `jadx -d`** (and open the app in `jadx-gui` alongside it) to produce the Java tree.
4. **Read the package name** from the decoded manifest.

```bash
# Package name from the decoded manifest
grep -m1 'package=' apktool_out/AndroidManifest.xml
```

5. **Set a package shortcut and scope every search to it.** Nearly every command in this checklist greps the app's own source. Set the package once and derive its source-tree path (the package uses dots; the decompiled tree uses slashes, so swap them).

```bash
PKG="com.example.app"                      # the app's package, from the manifest
PKGPATH="jadx_out/sources/${PKG//.//}"     # same package as a source-tree path

echo "$PKGPATH"                            # sanity check: jadx_out/sources/com/example/app
ls "$PKGPATH" | head                       # should list the app's own source folders
```

> **Note:** Scope every grep to `"$PKGPATH/"`. A repo-wide search for a term like `MD5`, `DES`, or `ECB` lights up with hits from bundled libraries (crypto providers, networking, analytics) that are not the app's code. Treating library hits as noise, unless a check is specifically about a dependency, is the difference between a real first-party finding and a false one. The variable lives only in the current terminal, so redefine it if you open a new one.

## Setting Up the Dynamic Pass

The static pass reads what the app *could* do; the dynamic pass watches what it *actually* does while running, which is the only way to confirm a runtime-built cipher string, a file written to disk, or a biometric gate that trusts a boolean. Each control below adds a dynamic check on top of its static ones.

You need a device you control:

- A **rooted device or emulator**. A Google APIs emulator image (not a Play image) gives you root out of the box with `adb root`. On a physical device you need it rooted so you can read the app sandbox.
- **`adb`** for shell access, pulling files, and reading logs.
- **Frida** for hooking and observing the app at runtime. Setup (server on device, client on host, and the checks that it is working) is covered in [Frida on-device setup](/posts/frida-on-device). `objection` sits on top of Frida for common tasks without writing scripts.
- An intercepting proxy (**Burp Suite** or **mitmproxy**) for the network-facing checks, once you reach NETWORK.

The core loop for most dynamic checks is the same: install the app, drive the feature you are testing, then inspect what it left behind or hook the call while it happens.

```bash
adb install target.apk               # install the build under test
adb shell run-as "$PKG" ls files     # list the app's private sandbox (debuggable build)
adb pull /sdcard/Android/data/"$PKG"  # pull app-scoped external storage
adb logcat --pid=$(adb shell pidof -s "$PKG")   # only this app's log output
```

> **Note:** `run-as` only works on a `debuggable` build or with root. On a production build, root the device (or use an emulator) and read `/data/data/$PKG/` directly. Always confirm findings against the production build, not a tester build with protections disabled.

## MASVS-STORAGE-1: The App Securely Stores Sensitive Data

STORAGE-1 asks one thing: any sensitive data the app intentionally stores is protected wherever it lands. Before the checks, build the sensitive-data map for this app (auth tokens, the session, PII, payment data, cryptographic keys); each check below runs that list against one class of storage location. Two weaknesses sit under this control, and both come down to the same failure, sensitive data written without encryption:

- **MASWE-0006:** unencrypted sensitive data in private storage. Both platforms, profile L2.
- **MASWE-0007:** unencrypted sensitive data in shared storage that needs no user interaction. Android only.

Access restrictions on internal files, log leakage, and backup exposure are a separate control (STORAGE-2), so they are not checked here.

Hold one boundary. STORAGE-1 asks whether stored data is encrypted at all and whether its key lives in the hardware-backed keystore. Whether the algorithm is strong or the key is hardcoded is why MASWE-0006 also maps to MASVS-CRYPTO-2; judge key strength and algorithm choice under CRYPTO and note the crossover here rather than failing it in both places.

### Check 1: Unencrypted sensitive data in private storage (MASWE-0006)

The app sandbox is private, but private is not encrypted. Wrong file permissions, an app or device vulnerability, or a device backup can lift data straight out of it. Confirm every sensitive value written to the sandbox is encrypted with a key from the `AndroidKeyStore`.

Sweep the private-storage APIs first, then read the call sites it returns:

```bash
grep -rnE 'getSharedPreferences|MODE_PRIVATE|openFileOutput|getFilesDir|getCacheDir|SQLiteDatabase|Room\.databaseBuilder' "$PKGPATH/"
```

Then confirm whether the encrypted wrappers back those same values:

```bash
grep -rnE 'EncryptedSharedPreferences|EncryptedFile|MasterKey|AndroidKeyStore' "$PKGPATH/"
```

- **PASS:** every sensitive value reaches only `EncryptedSharedPreferences`, `EncryptedFile`, or a store whose key comes from the `AndroidKeyStore`.
- **FAIL:** a token, password, key, or PII value lands in plain `SharedPreferences`, a cleartext file through `openFileOutput`, or an unencrypted SQLite or Room database.
- **Evidence:** the write call site, the value written, and the protection that is or is not in place. If you have the app on a device, pair it with the on-disk file under `/data/data/<pkg>/`.

### Check 2: Unencrypted sensitive data in shared storage (MASWE-0007)

Shared (external) storage is readable by any app holding the storage permission, with no user interaction, and it can outlive the app's uninstall. Anything sensitive written there in cleartext is exposed. This covers storage the app writes to on its own; a location the user explicitly picks through the system document picker counts as user interaction and is out of scope for this weakness.

```bash
grep -rnE 'getExternalStorage|getExternalFilesDir|getExternalCacheDir|Environment\.DIRECTORY|MediaStore' "$PKGPATH/"
```

- **PASS:** no sensitive value is written to external storage, or anything written there is encrypted with a hardware-backed key.
- **FAIL:** a token, key, credential, or PII value is written to external storage or `MediaStore` in cleartext.
- **Evidence:** the external-write call site and the sensitive value it carries.

### Dynamic confirmation

The grep finds where the app writes; the disk shows what actually landed there, which is the authoritative answer. Install the app, exercise every flow that stores something sensitive (log in, save a token, enter payment data), then read the sandbox back.

```bash
# Pull the whole private sandbox (root or debuggable build)
adb shell run-as "$PKG" tar c . > sandbox.tar    # or: adb pull /data/data/$PKG
```

Inspect what came out:

```bash
# SharedPreferences land here as plaintext XML
adb shell run-as "$PKG" cat shared_prefs/*.xml

# Open any database and read sensitive tables
adb shell run-as "$PKG" ls databases
sqlite3 pulled.db '.tables'

# Grep the whole pulled tree and external storage for known secrets
grep -rniE 'token|password|Bearer|<known-secret-value>' sandbox_extracted/
adb shell ls -R /sdcard/Android/data/"$PKG"
```

- **PASS:** the token, PIN, or PII you entered does not appear in cleartext anywhere in the sandbox or external storage; where it is stored, the on-disk bytes are ciphertext.
- **FAIL:** the value you entered is readable on disk in a preferences XML, a database column, a file, or external storage.
- **Evidence:** the file path and the cleartext value, tied back to the flow that wrote it.

> **References:** MASVS-STORAGE-1; MASWE-0006, MASWE-0007; MASTG-TEST-0001, MASTG-TEST-0052.

## MASVS-STORAGE-2: The App Prevents Leakage of Sensitive Data

Where STORAGE-1 covers data the app deliberately stores, STORAGE-2 covers sensitive data that escapes by accident: into logs, out through weak file permissions, or into a device backup. Four weaknesses map here:

- **MASWE-0001:** sensitive data written to logs. Both platforms, profiles L1, L2, P.
- **MASWE-0002:** sensitive data in internal storage with insufficient access restrictions. Android, profiles L1, L2.
- **MASWE-0003:** the app's backup is not encrypted. Android, profile L2.
- **MASWE-0004:** sensitive data is not excluded from backup. Both platforms, profiles L1, L2, P.

### Check 1: Sensitive data written to logs (MASWE-0001)

A log statement carrying a token, password, or PII reaches the system log (readable by other apps on old or compromised devices) or an app log file (readable on a rooted device). Verbose logging is useful in development and a leak in production, so the check is whether sensitive values reach any log call in the shipping build.

```bash
grep -rnE 'Log\.(v|d|i|w|e)|System\.out\.print|printStackTrace|Timber\.' "$PKGPATH/"
```

Read the hits that log request bodies, auth headers, exceptions, or user objects.

- **PASS:** no sensitive value reaches a log call, or logging is stripped in the release build (for example a ProGuard rule removing `Log` calls, or a build-flag guard).
- **FAIL:** a token, credential, session, or PII value is passed to any log call in the production build.
- **Evidence:** the log call site and the sensitive value it prints.

### Check 2: Insufficient access restrictions in internal storage (MASWE-0002)

Even inside internal storage, data can be exposed to other apps through world-readable file modes or a misconfigured `FileProvider`. The deprecated `MODE_WORLD_READABLE` and `MODE_WORLD_WRITEABLE` remove the sandbox boundary entirely; an over-broad `FileProvider` or an exported `ContentProvider` hands other apps a path in.

```bash
grep -rnE 'MODE_WORLD_READABLE|MODE_WORLD_WRITEABLE|setReadable\(true|setWritable\(true' "$PKGPATH/"
grep -nE 'provider|android:exported="true"|grantUriPermissions' apktool_out/AndroidManifest.xml
```

For each `<provider>`, check `android:exported`, `android:permission`, and the paths declared in its filepaths resource.

- **PASS:** internal files use private modes only, and any `FileProvider` or `ContentProvider` over sensitive data is not exported or is guarded by a signature-level permission with tightly scoped paths.
- **FAIL:** internal data is written world-readable or world-writable, or a provider over it is exported without a meaningful permission, or its declared paths expose the data directory.
- **Evidence:** the mode flag or the provider declaration and the data it exposes.

### Check 3: Backup not encrypted (MASWE-0003)

Android's auto-backup can require client-side encryption and can restrict device-to-device transfer through backup conditions. When those conditions are not set, backed-up data can leave the device in a form an attacker can read.

```bash
grep -nE 'allowBackup|fullBackupContent|dataExtractionRules' apktool_out/AndroidManifest.xml
```

Open the referenced backup rules resource (the `dataExtractionRules` XML on Android 12 and above) and check the conditions on each `<cloud-backup>` and `<device-transfer>` block.

- **PASS:** backup is disabled for sensitive data, or the extraction rules require client-side encryption for cloud backup and constrain device transfer.
- **FAIL:** backup is enabled and the rules place no encryption condition on the sensitive data they cover.
- **Evidence:** the manifest backup attributes and the rules resource.

### Check 4: Sensitive data not excluded from backup (MASWE-0004)

Separate from whether the backup is encrypted is what it contains. With `android:allowBackup="true"` and no exclusion rules, the sandbox (token stores and databases included) is swept into the backup. An attacker can restore it, or tamper with it and restore, for example to reset a one-time coupon or a premium-feature flag.

```bash
grep -nE 'allowBackup|fullBackupContent|dataExtractionRules' apktool_out/AndroidManifest.xml
```

Read the backup rules resource and confirm each sensitive store is covered by an `<exclude>`.

- **PASS:** `allowBackup` is false, or the backup rules exclude every store holding sensitive data.
- **FAIL:** backup is enabled and a token store, credential file, or sensitive database is not excluded.
- **Evidence:** the `allowBackup` value and the exclusion rules (or their absence) for the sensitive stores.

### Dynamic confirmation

Two of these weaknesses have a decisive runtime test. For logging, watch the log while you drive the app; for backup, actually take a backup and read it.

```bash
# Logs: capture only this app's output while you log in and move money
adb logcat -c && adb logcat --pid=$(adb shell pidof -s "$PKG") | grep -iE 'token|password|Bearer|[0-9]{16}'

# Backup: pull an ADB backup and unpack it (works when allowBackup is true)
adb backup -f app.ab -noapk "$PKG"
( printf '\x1f\x8b\x08\x00\x00\x00\x00\x00' ; tail -c +25 app.ab ) | tar xfvz -
```

For access restrictions (MASWE-0002), confirm a suspect exported provider actually serves data by querying it from another context.

```bash
adb shell content query --uri content://<authority>/<path>
```

- **PASS:** no sensitive value appears in logcat during real use; the backup archive contains no sensitive store, or `allowBackup` is false so no archive is produced; the provider query returns nothing sensitive or is denied.
- **FAIL:** a token or PII value prints to the log during normal use, or the backup archive yields a token store or database, or the provider hands back sensitive rows.
- **Evidence:** the log line, the extracted backup file, or the provider query result.

> **References:** MASVS-STORAGE-2; MASWE-0001, MASWE-0002, MASWE-0003, MASWE-0004.

## MASVS-CRYPTO-1: The App Employs Current Strong Cryptography and Uses It According to Best Practices

CRYPTO-1 asks whether the cryptography itself is sound: the algorithm, the mode, the padding, and the randomness, independent of any key. Judge the primitive and its configuration here; key generation and key storage are CRYPTO-2. For the model behind these checks (cipher modes, padding oracles, authenticated encryption, secure randomness), see [Cryptography Foundations](/posts/cryptography-foundations). Four weaknesses map to this control:

- **MASWE-0020:** improper encryption (broken algorithm, broken mode, short key, bad IV, or fake encryption). Both platforms, profiles L1, L2.
- **MASWE-0023:** risky padding that enables padding-oracle attacks. Both platforms, profiles L1, L2.
- **MASWE-0027:** improper random number generation. Both platforms, profiles L1, L2.
- **MASWE-0019:** risky or home-rolled cryptographic implementations. Both platforms, profile L2.

The mechanic for the first two checks is the same: find every `Cipher.getInstance` and read the transformation string it is handed. That string is `algorithm/mode/padding`, and each part is a separate pass or fail.

### Check 1: Broken algorithm, mode, or key length (MASWE-0020)

AES-ECB reuses no state between blocks, so identical plaintext blocks produce identical ciphertext blocks and structure leaks straight through. DES, 3DES, RC4, and Blowfish are retired. A 128-bit AES key is under the 256-bit floor for anything sensitive. And XOR, Base64, or byte shuffling is encoding, not encryption.

```bash
grep -rnE 'Cipher\.getInstance|MessageDigest\.getInstance|"(DES|DESede|RC2|RC4|ARCFOUR|Blowfish)"|/ECB/' "$PKGPATH/"
```

Read the transformation string at each `Cipher.getInstance` hit, and check for encoding used in place of encryption:

```bash
grep -rnE 'Base64\.(encode|decode)|\^ 0x|\^= 0x' "$PKGPATH/"
```

- **PASS:** encryption uses an approved algorithm and mode with a sufficient key length, for example `AES/GCM/NoPadding` with a 256-bit key.
- **FAIL:** a sensitive value is protected with DES, 3DES, RC4, or Blowfish; with AES in ECB mode; with an AES key under 256 bits; or with XOR or Base64 standing in for encryption.
- **Evidence:** the `Cipher.getInstance` call site, the full transformation string, and the key length.

### Check 2: Risky padding (MASWE-0023)

A padding-oracle attack recovers plaintext without the key, when two conditions both hold: a padding scheme that is oracle-prone, and the app leaking whether padding validated (an error message or a timing difference). RSA with PKCS#1 v1.5 (Bleichenbacher) and AES-CBC with PKCS#7 but no separate integrity check are the two to flag.

```bash
grep -rnE 'RSA/[A-Za-z]+/PKCS1Padding|/CBC/PKCS5Padding|/CBC/PKCS7Padding' "$PKGPATH/"
```

- **PASS:** symmetric encryption uses an authenticated mode (AES-GCM) or pairs CBC with an Encrypt-then-MAC integrity check; RSA uses OAEP.
- **FAIL:** RSA uses PKCS#1 v1.5, or AES-CBC with PKCS#7 carries no MAC and the decrypt path surfaces distinct padding errors.
- **Evidence:** the transformation string, and for CBC whether any MAC covers the ciphertext.

### Check 3: Insecure random number generation (MASWE-0027)

`java.util.Random` and `Math.random()` are linear generators: observe enough output and you can predict the rest. Used for a key, IV, token, or nonce, that is a break. Only `SecureRandom` (seeded by the system, never with a fixed seed) belongs in a security context.

```bash
grep -rnE 'new Random\(|Math\.random\(|java\.util\.Random|SecureRandom\([^)]|\.setSeed\(' "$PKGPATH/"
```

- **PASS:** every security-relevant random value comes from `SecureRandom` with no hardcoded seed.
- **FAIL:** a key, IV, token, salt, or nonce is drawn from `java.util.Random`, `Math.random()`, or a `SecureRandom` seeded with a fixed value.
- **Evidence:** the generator call site and what the value is used for.

### Check 4: Risky or home-rolled cryptography (MASWE-0019, L2)

Custom crypto rarely survives review. Hardcoded S-boxes, permutation tables, long chains of bit shifts and XORs, or a high-entropy blob that hides an algorithm all signal a hand-rolled primitive that has not been validated. The standard is to use a vetted library: Android's Conscrypt, or OpenSSL, BoringSSL, BouncyCastle.

```bash
grep -rnE 'byte\[\] *[A-Za-z0-9_]+ *= *\{|>>> |<<< |\^ [A-Za-z]' "$PKGPATH/"
```

- **PASS:** all cryptography runs through a standard, well-reviewed library.
- **FAIL:** the app implements its own cipher, hash, or PRNG, or pulls in an unvetted crypto library.
- **Evidence:** the custom implementation and the operation it stands in for.

### Dynamic confirmation

Grep only sees literal transformation strings. Apps often build the string at runtime (`"AES/" + mode + "/" + padding`), pull the algorithm from config, or reach crypto through a wrapper, and those slip straight past a static sweep. Hooking the actual crypto calls shows the real algorithm, key, and IV as they run, and catches IV reuse that no static read can prove.

```bash
# Log every Cipher.getInstance transformation string the app actually uses
frida -U -f "$PKG" -l - <<'EOF'
Java.perform(function () {
  var Cipher = Java.use('javax.crypto.Cipher');
  Cipher.getInstance.overload('java.lang.String').implementation = function (t) {
    console.log('[Cipher] ' + t);
    return this.getInstance(t);
  };
});
EOF
```

`objection`'s `android hooking watch class javax.crypto.Cipher` does the same without a script. Drive an encrypt flow twice and compare the IVs to check for reuse. OWASP's runtime tests cover exactly this: broken modes (MASTG-TEST-0350) and reused IVs (MASTG-TEST-0310).

- **PASS:** every transformation logged at runtime is an approved algorithm and mode with a fresh IV per operation.
- **FAIL:** a runtime transformation resolves to DES, RC4, ECB, or a short key that the static sweep missed, or the same IV appears across operations.
- **Evidence:** the logged transformation string, key length, and IV values across runs.

> **Deeper on L2:** CRYPTO-1 has finer-grained placeholder weaknesses that the checks above partly cover: improper hashing (MASWE-0021, the MD5/SHA-1 part of Check 1), predictable IVs (MASWE-0022, the IV part of Check 1 and the dynamic reuse check), improper MAC use (MASWE-0024), and improper signature generation and verification (MASWE-0025, MASWE-0026). Where an app uses a MAC or digital signatures, review those explicitly against the same primitive-strength logic.

> **References:** MASVS-CRYPTO-1; MASWE-0019, MASWE-0020, MASWE-0023, MASWE-0027; MASTG-TEST-0013, MASTG-TEST-0014, MASTG-TEST-0016, MASTG-TEST-0350, MASTG-TEST-0310.

## MASVS-CRYPTO-2: The App Performs Key Management According to Best Practices

Where CRYPTO-1 judges the primitive, CRYPTO-2 judges the key: how it is generated, and where it lives. Two weaknesses carry current OWASP text:

- **MASWE-0009:** improper cryptographic key generation (weak size or weak source). Both platforms, profiles L1, L2.
- **MASWE-0014:** cryptographic keys not properly protected at rest. Both platforms, profiles L1, L2. Also maps MASVS-STORAGE-1.

This control is the home for the hardcoded-key finding raised under STORAGE-1. An app that encrypts with a strong algorithm but ships the key in its code passes STORAGE-1's "is it encrypted" question and fails here; report it once, under CRYPTO-2.

### Check 1: Weak key generation (MASWE-0009)

A key is only as strong as its length and its source. RSA under 2048 bits and AES under 256 bits are below the floor for sensitive data. A key derived from a predictable generator (see CRYPTO-1 Check 3) is guessable regardless of length.

```bash
grep -rnE 'KeyGenerator\.getInstance|KeyPairGenerator\.getInstance|KeyGenParameterSpec|\.init\(|setKeySize\(' "$PKGPATH/"
```

Read the size passed to each `init` or `setKeySize`, and confirm the source feeding any raw key material is a CSPRNG.

- **PASS:** symmetric keys are at least 256 bits and RSA keys at least 2048 bits, generated through `KeyGenerator`, `KeyPairGenerator`, or `KeyGenParameterSpec` from a secure source.
- **FAIL:** a key is generated under the size floor, or from `java.util.Random` or another predictable source.
- **Evidence:** the generation call site, the key size, and the randomness source.

### Check 2: Keys not protected at rest (MASWE-0014)

The strongest key is worthless if it sits next to the data it protects. Keys hardcoded in code, held in plain `SharedPreferences` or files, or built from a `SecretKeySpec` over a literal byte array are all extractable by decompiling the app. Keys should be generated on-device and held in the `AndroidKeyStore`, hardware-backed through StrongBox where the use case allows.

```bash
grep -rnE 'SecretKeySpec\(|IvParameterSpec\(|\.getBytes\(\)|"[A-Fa-f0-9]{32,}"|(private|static|final).*[Kk]ey *=' "$PKGPATH/"
```

Then confirm keys actually come from the keystore rather than a literal:

```bash
grep -rnE 'AndroidKeyStore|KeyStore\.getInstance|setUserAuthenticationRequired|setUnlockedDeviceRequired' "$PKGPATH/"
```

- **PASS:** keys are generated into and retrieved from the `AndroidKeyStore`, never appearing as literals in code or in cleartext storage.
- **FAIL:** a key is hardcoded, built from a literal byte array through `SecretKeySpec`, or written to `SharedPreferences` or a file in cleartext.
- **Evidence:** the key literal or the storage write, and the code path that reads it back.

> **Deeper on L2:** OWASP also tracks key derivation strength (MASWE-0010, PBKDF2 iteration count), key rotation (0011), wrong or reused key usage (0012), deprecated keystore implementations (0015), imported and exported keys (0016, 0017), and key access restrictions such as `setUserAuthenticationRequired` (0018). These are placeholder weaknesses without finalized OWASP test text, so they are review prompts rather than fixed pass or fail checks for now.

### Dynamic confirmation

The question at runtime is where the key comes from. Hook `SecretKeySpec`, the point where a raw byte array becomes a key, and you catch keys built from literals or from cleartext storage even when the bytes were assembled at runtime. A key that never passes through `SecretKeySpec` and instead comes from an `AndroidKeyStore` handle is the good sign.

```bash
# Dump every raw key handed to SecretKeySpec
frida -U -f "$PKG" -l - <<'EOF'
Java.perform(function () {
  var SKS = Java.use('javax.crypto.spec.SecretKeySpec');
  SKS.$init.overload('[B', 'java.lang.String').implementation = function (k, a) {
    console.log('[SecretKeySpec] ' + a + ' key=' + Java.use('android.util.Base64').encodeToString(k, 0));
    return this.$init(k, a);
  };
});
EOF
```

Cross-check against the keystore: a key created with `setUserAuthenticationRequired(true)` cannot be used at all until the user authenticates, which you can observe by trying to use it while locked.

- **PASS:** keys used at runtime resolve to `AndroidKeyStore` handles; no sensitive key appears as raw bytes passed to `SecretKeySpec`.
- **FAIL:** a key is reconstructed at runtime from a hardcoded or stored byte array, revealing the same secret on every run.
- **Evidence:** the raw key bytes captured at the `SecretKeySpec` call, matched to their source in the static read.

> **References:** MASVS-CRYPTO-2; MASWE-0009, MASWE-0014; MASTG-TEST-0015. Key-at-rest also relates to MASVS-STORAGE-1.

## MASVS-AUTH-1: The App Uses Secure Authentication and Authorization Protocols

AUTH is the group where a static pass is deliberately narrow, and it helps to know why. Authentication and authorization decisions are made on the server, and local authentication is a runtime event, so most of this group is tested dynamically or against the backend. Of the AUTH weaknesses, only one carries finalized OWASP test text, and it is the one thing the client package fully exposes: secrets that should never ship inside it.

- **MASWE-0005:** API keys hardcoded in the app package. Both platforms, profiles L1, L2.

Auth material stored unencrypted on the device (MASWE-0036) is the other static-visible AUTH-1 concern, but it is the same finding as STORAGE-1 Check 1 and CRYPTO-2 Check 2; judge it there and cross-reference rather than failing it a third time here.

### Check 1: Hardcoded API keys and auth secrets (MASWE-0005)

Anything embedded in the code, resources, assets, or a bundled library is extractable by unzipping and decompiling the package. Sweep the decompiled sources and the packaged resources for key-shaped values, then confirm each hit is a real secret rather than a public identifier.

```bash
grep -rniE 'api[_-]?key|secret|password|passwd|bearer|authorization|AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|sk_live_|-----BEGIN' "$PKGPATH/"
grep -rniE 'api[_-]?key|secret|token|client_secret' apktool_out/res/values/ apktool_out/assets/ 2>/dev/null
```

A dedicated secret scanner catches formats a hand-written pattern misses:

```bash
gitleaks detect --no-git --source apktool_out/
```

- **PASS:** no live secret ships in the package; the app authenticates through short-lived tokens obtained at runtime, or any embedded key is a public client identifier scoped to the minimum permissions.
- **FAIL:** a usable API key, client secret, password, or private key is present in the code, `strings.xml`, `BuildConfig`, an asset file, or a library config.
- **Evidence:** the file and line, the value, and what service it authenticates to. A key you can actually use against the backend is a confirmed finding, not a lead.

### Dynamic confirmation

A key in the package is a lead; a key that works against the backend is the finding. Take the extracted key and use it directly, and separately proxy the app's live traffic to see the key and any auth headers in flight.

```bash
# Use the extracted key against the API it targets; does it return real data?
curl -s 'https://api.example.com/v1/resource?key=AIza...' | head

# Or route the app through a proxy and read what it sends
# (set the device HTTP proxy to Burp/mitmproxy, then drive the app)
```

- **PASS:** the extracted key is rejected, is a public identifier with no privileged access, or is scoped so tightly that it cannot perform sensitive actions.
- **FAIL:** the key returns real data, performs billed operations, or unlocks paid or restricted functionality.
- **Evidence:** the request you sent with the extracted key and the backend's response.

> **Deeper on L2:** OWASP also tracks not using platform-provided authentication APIs such as AppAuth (MASWE-0032), passwordless authentication not implemented (MASWE-0035), and authentication material sent over insecure connections (MASWE-0037, which overlaps the NETWORK-1 cleartext check). These are placeholder weaknesses without finalized test text; treat them as review prompts.

> **References:** MASVS-AUTH-1; MASWE-0005 (MASWE-0036 cross-references STORAGE-1 and CRYPTO-2).

## MASVS-AUTH-2: The App Performs Local Authentication Securely

Local authentication is a biometric or device-credential unlock done on the device. The static question is not whether the app calls the biometric API, but whether a successful biometric actually gates something cryptographic, or is just a boolean the app chooses to trust.

- **MASWE-0044:** biometric authentication can be bypassed. Both platforms, profile L2.
- **MASWE-0043:** a custom app PIN is not bound to the platform keystore. Both platforms, profile L2. Also maps MASVS-CRYPTO-2.

### Check 1: Local authentication is bound to a keystore key (MASWE-0044, MASWE-0043)

There are two ways to build a fingerprint gate. The insecure one calls `BiometricPrompt.authenticate()` with no `CryptoObject` and simply proceeds when `onAuthenticationSucceeded` fires; that callback is a boolean, and a boolean can be forced at runtime, so the gate is cosmetic. The secure one hands `authenticate()` a `CryptoObject` wrapping a key from the `AndroidKeyStore` created with `setUserAuthenticationRequired(true)`, so a real biometric is the only thing that unlocks the key. The same logic applies to a custom PIN: it must unlock a keystore key, not just compare against a stored value.

```bash
grep -rnE 'BiometricPrompt|FingerprintManager|\.authenticate\(|CryptoObject|setUserAuthenticationRequired|KeyguardManager|createConfirmDeviceCredentialIntent' "$PKGPATH/"
```

Read each `authenticate` call: check whether it is passed a `CryptoObject`, and whether the key it wraps was created with `setUserAuthenticationRequired(true)`.

- **PASS:** biometric or PIN success unlocks a key from the `AndroidKeyStore` (`setUserAuthenticationRequired(true)`), and the app cannot proceed without that key.
- **FAIL:** the flow relies on the `onAuthenticationSucceeded` callback or a returned boolean with no `CryptoObject`, or a custom PIN is compared in code without unlocking a keystore key.
- **Evidence:** the `authenticate` call site, whether a `CryptoObject` is present, and what the success path actually gates.

### Dynamic confirmation

This is where the static read pays off or falls over, and it is the most important dynamic check in the group. If the gate is a boolean (no `CryptoObject`), you can force the success callback and walk straight through without a valid biometric. If it is bound to a keystore key, the same attack fails because there is no key to unlock.

```bash
# objection's built-in biometric bypass hooks the success path
objection -g "$PKG" explore
# then at the prompt:  android hooking watch class androidx.biometric.BiometricPrompt
#                      android biometrics-bypass
```

The withSecure fingerprint-bypass Frida scripts referenced in the OWASP test do the same: one flips `onAuthenticationSucceeded` when no `CryptoObject` is used, the other targets incorrect `CryptoObject` handling. Separately, confirm server-side enforcement: with the app proxied, complete a sensitive action, then replay the request with the auth token stripped or altered and check that the server rejects it.

- **PASS:** the bypass fails because success unlocks a keystore key that never gets released, and the server independently rejects a tampered or missing token.
- **FAIL:** forcing the success callback lets the app proceed, or the server accepts an action after the client-side gate is bypassed.
- **Evidence:** the bypass attempt and the app's response, plus the server's response to the tampered request.

> **Deeper on L2:** OWASP also tracks authentication and authorization enforced only locally instead of on the server (MASWE-0041, MASWE-0042), auth tokens not validated (MASWE-0038), and keys not invalidated on new biometric enrollment (MASWE-0046, favor a `...CurrentSet` binding). The server-side items cannot be proven from the client alone; statically, flag any security decision the app makes purely on local state with no backend call, and confirm it dynamically with the replay test above.

> **References:** MASVS-AUTH-2; MASWE-0043, MASWE-0044; MASTG-TEST-0326, MASTG-TEST-0327, MASTG-TEST-0328, MASTG-TEST-0329, MASTG-TEST-0330.

## MASVS-AUTH-3: The App Requests Re-Authentication for Sensitive Operations

AUTH-3 covers step-up authentication: re-prompting the user before a high-value action (a payment, a settings change, a credential update), and multi-factor flows. This is almost entirely a design and runtime property, so there is no finalized static check here; the weaknesses (MASWE-0028 MFA best practices, MASWE-0029 step-up after login, MASWE-0030 contextual re-authentication) are all placeholders.

Statically, you can record whether sensitive actions re-invoke the biometric or credential prompt at all, as a lead for the dynamic pass:

```bash
grep -rnE 'BiometricPrompt|createConfirmDeviceCredentialIntent|setUserAuthenticationValidityDurationSeconds' "$PKGPATH/"
```

A very long `setUserAuthenticationValidityDurationSeconds` means one unlock covers a long window, which weakens step-up.

### Dynamic confirmation

Step-up is a runtime property, so this is where it is actually judged. Reach a sensitive action (a payment, a password or beneficiary change) and watch whether the app forces a fresh authentication, or rides the session from the initial login. Then test the server: proxy the request for the sensitive action and replay it without whatever step-up factor the client added.

- **PASS:** the sensitive action triggers a fresh prompt, and the server rejects the replayed request that lacks the step-up factor.
- **FAIL:** the action proceeds on the original session with no re-authentication, or the server accepts the replay without the step-up factor.
- **Evidence:** the action tested, whether a prompt appeared, and the server's response to the replayed request.

> **References:** MASVS-AUTH-3; MASWE-0028, MASWE-0029, MASWE-0030 (all placeholder; primarily dynamic).

## MASVS-NETWORK-1: The App Secures All Network Traffic According to Best Practices

NETWORK-1 is the baseline question: is every connection encrypted, authenticated, and made through an API that enforces both. This is where the static config and the intercepting proxy pair most directly. Four finalized weaknesses map here:

- **MASWE-0050:** cleartext traffic. Both platforms, profiles L1, L2.
- **MASWE-0052:** insecure certificate validation. Both platforms, profiles L1, L2.
- **MASWE-0049:** proven networking APIs not used. Both platforms, profile L2.
- **MASWE-0051:** unprotected open ports. Both platforms, profile L2.

For the whole dynamic side of this control you need an intercepting proxy in place: set the device HTTP proxy to Burp or mitmproxy and install its CA, as described in Setting Up the Dynamic Pass.

### Check 1: Cleartext traffic (MASWE-0050)

Plain HTTP, an insecure protocol, or a platform config that permits either. On Android the switch is the manifest `usesCleartextTraffic` flag and the Network Security Config it points at.

```bash
grep -nE 'usesCleartextTraffic|networkSecurityConfig' apktool_out/AndroidManifest.xml
grep -rnE 'cleartextTrafficPermitted|<base-config|<domain-config' apktool_out/res/xml/ 2>/dev/null
grep -rnE 'http://[a-zA-Z]' "$PKGPATH/"
```

- **PASS:** cleartext is disabled (no `usesCleartextTraffic="true"`, and the NSC sets `cleartextTrafficPermitted="false"` with no broad exceptions); all endpoints are HTTPS.
- **FAIL:** cleartext is permitted globally or for a broad domain, or a sensitive endpoint is reached over `http://`.
- **Evidence:** the manifest flag or NSC block, and the cleartext URL.

### Check 2: Insecure certificate validation (MASWE-0052)

HTTPS that does not actually verify the peer. The patterns are a `TrustManager` whose `checkServerTrusted` is empty, a `HostnameVerifier` that returns `true`, an allow-all `SSLSocketFactory`, or a WebView that calls `handler.proceed()` inside `onReceivedSslError`.

```bash
grep -rnE 'X509TrustManager|checkServerTrusted|HostnameVerifier|ALLOW_ALL_HOSTNAME|setHostnameVerifier|onReceivedSslError|\.proceed\(|TrustManager\[\]' "$PKGPATH/"
```

Read each hit: an empty `checkServerTrusted` body or a `HostnameVerifier` returning `true` is a trust-everything override.

- **PASS:** the app relies on the platform's default trust evaluation; any custom `TrustManager` performs full chain and hostname validation.
- **FAIL:** a trust-all `TrustManager`, an allow-all `HostnameVerifier`, or a WebView that proceeds through SSL errors.
- **Evidence:** the override method and its body.

### Check 3: Roll-your-own networking (MASWE-0049, L2)

Custom network stacks and low-level sockets skip the platform's built-in encryption, validation, and error handling. Prefer `HttpsURLConnection` or `OkHttp`.

```bash
grep -rnE 'new Socket\(|SSLSocket|DatagramSocket|getOutputStream\(\)|URLConnection' "$PKGPATH/"
```

- **PASS:** networking goes through `HttpsURLConnection`, `OkHttp`, or a comparable vetted library.
- **FAIL:** the app builds its own HTTP or TLS over raw `Socket`/`SSLSocket`, bypassing platform security features.
- **Evidence:** the low-level networking call site and what it carries.

### Check 4: Unprotected open ports (MASWE-0051, L2)

An app that listens on a socket can expose functionality to other apps or the network, especially bound to all interfaces rather than loopback.

```bash
grep -rnE 'ServerSocket|InetSocketAddress|\.bind\(|0\.0\.0\.0' "$PKGPATH/"
```

- **PASS:** the app opens no listening socket, or binds to loopback with authentication on the service.
- **FAIL:** the app listens on a wildcard address with no authentication.
- **Evidence:** the bind call and the interface and port it exposes.

### Dynamic confirmation

With the proxy in place, drive every network feature and read the flows. Cleartext shows up as plain HTTP in the proxy history. For certificate validation, present a certificate your device does not trust (the proxy's default, before you install its CA): if the app still connects, it is accepting any certificate.

```bash
# Confirm listening sockets actually opened by the app at runtime
adb shell run-as "$PKG" netstat -tlnp 2>/dev/null   # or: adb shell ss -tlnp
```

- **PASS:** no cleartext appears in the proxy; with the proxy CA untrusted, TLS connections fail; no unexpected listening port is open.
- **FAIL:** plain HTTP is observed, or traffic intercepts even though the proxy CA is untrusted (broken validation), or a service answers on an open port.
- **Evidence:** the proxy flow, or the `netstat` line for the open port.

> **Deeper on L2:** OWASP also tracks insecure machine-to-machine communication (MASWE-0048) and data sent unencrypted inside an otherwise encrypted connection (MASWE-0096, a second layer of plaintext within TLS). These are placeholder weaknesses; where the app has non-user M2M channels or wraps its own payload encoding, review them against the same transport logic.

> **References:** MASVS-NETWORK-1; MASWE-0048, MASWE-0049, MASWE-0050, MASWE-0051, MASWE-0052, MASWE-0096; MASTG-TEST-0019, MASTG-TEST-0020, MASTG-TEST-0021, MASTG-TEST-0023.

## MASVS-NETWORK-2: The App Performs Identity Pinning for Developer-Controlled Endpoints

Pinning ties the app to a specific certificate or public key, so that even a valid CA-issued certificate is rejected unless it matches the pin. Its absence is not a NETWORK-1 failure (the platform trust store still validates the chain); it is a separate L2 expectation for endpoints the developer controls.

- **MASWE-0047:** insecure identity pinning. Both platforms, profile L2.

One framing to hold, straight from OWASP: pinning is defense-in-depth and is bypassable by anyone who can reverse the app, so bypassing it at runtime is expected and is not itself the finding. The finding is pinning being absent, or misconfigured so it does not actually enforce.

### Check 1: Pinning is present and correctly configured (MASWE-0047)

Look for pins in the Network Security Config or in a pinning library (`OkHttp`'s `CertificatePinner`, TrustKit). A pin-set with a live pin and a backup pin, applied to the domains the app controls, is what you want.

```bash
grep -rnE 'CertificatePinner|certificatePinner|TrustKit|sha256/' "$PKGPATH/"
grep -rnE '<pin-set|<pin ' apktool_out/res/xml/ 2>/dev/null
```

- **PASS:** pinning is enforced for developer-controlled endpoints through the NSC `<pin-set>` or a well-configured library, with a backup pin.
- **FAIL:** no pinning on sensitive endpoints, pins retrieved over an insecure channel, or a custom implementation that accepts any chain to a trusted root instead of the specific key.
- **Evidence:** the pin-set or `CertificatePinner` config, and the domains it covers.

### Dynamic confirmation

This is the decisive test, and it runs in two steps. First, install the proxy CA in the device system trust store (rooted device or emulator). If the app now intercepts, there is no pinning. If it refuses to connect while your CA is trusted, pinning is present. Then confirm it is a pin, not a fluke, by disabling it.

```bash
objection -g "$PKG" explore
# then at the prompt:  android sslpinning disable
```

If traffic flows only after `sslpinning disable`, pinning was enforced. If it flowed before, pinning was absent.

- **PASS:** with the proxy CA trusted in the system store, the app refuses to connect, and traffic only appears after pinning is explicitly disabled.
- **FAIL:** traffic intercepts with the proxy CA trusted and no pinning bypass required.
- **Evidence:** the proxy result before and after `sslpinning disable`.

> **References:** MASVS-NETWORK-2; MASWE-0047; MASTG-TEST-0022, MASTG-TECH-0051 (pinning bypass).

## MASVS-PLATFORM-1: The App Uses IPC Mechanisms Securely

PLATFORM-1 covers the app's edges to other apps on the device: exported components, `PendingIntent`, and deep links. Note the grounding here: most PLATFORM weaknesses in MASWE are still stubs, so the checks below are anchored to the finalized MASTG tests instead. The mapped weaknesses (all placeholder, Android unless noted) are MASWE-0058 deep links, 0059 unauthenticated IPC, 0062 services, 0063 broadcast receivers, 0064 content providers, 0066 intents, 0119 activities, plus iOS 0060 UIActivity and 0061 app extensions.

ContentProviders that expose stored *data* are covered under STORAGE-2 Check 2; this control is about components that expose *functionality* and about trusting incoming IPC data.

### Check 1: Exported components (MASTG-TEST-0364, 0365, 0366)

A component with `android:exported="true"` and no permission can be invoked by any app. Read every exported activity, service, and receiver and decide whether the functionality behind it should be reachable from outside.

```bash
grep -nE '<activity|<service|<receiver|<provider|android:exported|android:permission' apktool_out/AndroidManifest.xml
```

- **PASS:** components are exported only when they need to be, and each exported one that reaches sensitive functionality is guarded by a signature-level permission.
- **FAIL:** an activity, service, or receiver that performs a sensitive action is exported with no permission (or a `normal`-level one).
- **Evidence:** the component declaration, its `exported` and `permission` attributes, and what it does.

### Check 2: Insecure PendingIntent (MASTG-TEST-0381)

A `PendingIntent` that is mutable and wraps an implicit base intent can be intercepted and rewritten by another app, which then acts with your app's identity and permissions.

```bash
grep -rnE 'PendingIntent\.(getActivity|getService|getBroadcast)|FLAG_MUTABLE|FLAG_IMMUTABLE' "$PKGPATH/"
```

- **PASS:** `PendingIntent`s are created `FLAG_IMMUTABLE`, or where mutability is required the base intent is explicit (names its target component).
- **FAIL:** a mutable `PendingIntent` wraps an implicit intent.
- **Evidence:** the `PendingIntent` creation call and the base intent it wraps.

### Check 3: Deep link and URL scheme validation (MASTG-TEST-0028, 0394)

A deep link or custom scheme hands attacker-controlled data straight into the app. The failure is a handler that trusts the incoming URI and its parameters without validating them.

```bash
grep -nE '<intent-filter|android:scheme|android:autoVerify|BROWSABLE' apktool_out/AndroidManifest.xml
grep -rnE 'getData\(\)|getQueryParameter|getIntent\(\)\.get' "$PKGPATH/"
```

- **PASS:** app links use `android:autoVerify` where appropriate, and handlers validate the URI, its host, and every parameter before acting.
- **FAIL:** a handler reads a path or parameter from the incoming URI and uses it (a redirect, a file path, a WebView load) without validation.
- **Evidence:** the intent-filter and the handler code that consumes the URI.

### Dynamic confirmation

The clean proof is to invoke the surface yourself from another context.

```bash
# Fire an exported component directly
adb shell am start -n "$PKG"/.ExportedActivity
adb shell am broadcast -n "$PKG"/.ExportedReceiver -a com.example.ACTION

# Trigger a deep link with a crafted parameter
adb shell am start -a android.intent.action.VIEW -d "app://host/path?param=../../etc"
```

`drozer` automates enumerating and attacking exported components and providers.

- **PASS:** invoking exported components and deep links from outside cannot reach sensitive functionality or feed unvalidated data into the app.
- **FAIL:** an `am start`/`am broadcast` reaches a sensitive action, or a crafted deep-link parameter is acted on.
- **Evidence:** the command that triggered the behavior and what happened.

> **References:** MASVS-PLATFORM-1; MASWE-0058, MASWE-0059, MASWE-0062, MASWE-0063, MASWE-0066 (placeholder); MASTG-TEST-0029, MASTG-TEST-0364, MASTG-TEST-0365, MASTG-TEST-0366, MASTG-TEST-0381, MASTG-TEST-0394.

## MASVS-PLATFORM-2: The App Uses WebViews Securely

A WebView is a browser inside the app, and its security depends entirely on its configuration and what it loads. The mapped weaknesses (all placeholder) are MASWE-0068 JavaScript bridges, 0069 local resource access, 0070/0071 untrusted content, 0072 universal XSS, 0073 WebResourceResponse, 0074 web debugging; the checks come from the finalized MASTG tests.

### Check 1: JavaScript-to-native bridge (MASTG-TEST-0031, 0033)

`addJavascriptInterface` exposes a native object's methods to any JavaScript running in the WebView. Combined with JavaScript enabled and untrusted or cleartext content, web code can call into the app.

```bash
grep -rnE 'setJavaScriptEnabled\(true|addJavascriptInterface|@JavascriptInterface|loadUrl\(|loadData' "$PKGPATH/"
```

- **PASS:** no native bridge is exposed, or the bridge is exposed only to content the app fully controls and serves over HTTPS.
- **FAIL:** `addJavascriptInterface` is reachable by remote, cleartext, or user-influenced content.
- **Evidence:** the interface registration, the exposed methods, and the URL the WebView loads.

### Check 2: WebView local file and cross-origin access (MASTG-TEST-0252)

Relaxed file settings let `file://` content read other local files or reach any origin, turning a WebView bug into local-file theft.

```bash
grep -rnE 'setAllowFileAccess|setAllowFileAccessFromFileURLs|setAllowUniversalAccessFromFileURLs|setAllowContentAccess' "$PKGPATH/"
```

- **PASS:** file access from file URLs and universal access are disabled (the modern defaults), and file access is enabled only where genuinely needed.
- **FAIL:** `setAllowUniversalAccessFromFileURLs(true)` or `setAllowFileAccessFromFileURLs(true)` on a WebView that loads any untrusted content.
- **Evidence:** the WebView settings call and what the WebView loads.

### Check 3: Web debugging in production (MASTG-TEST-0074 family)

`setWebContentsDebuggingEnabled(true)` lets anyone with the device inspect and drive the WebView through Chrome DevTools. It belongs in debug builds only.

```bash
grep -rnE 'setWebContentsDebuggingEnabled\(true' "$PKGPATH/"
```

- **PASS:** debugging is off in release, or guarded by a `BuildConfig.DEBUG` check.
- **FAIL:** it is enabled unconditionally in the production build.
- **Evidence:** the call site and whether a build guard wraps it.

### Dynamic confirmation

Proxy the app and drive every WebView flow: note the URLs it loads and whether any arrive over HTTP or from a redirectable source. If web debugging is on, connect DevTools and confirm.

```bash
# With setWebContentsDebuggingEnabled(true), the WebView appears here
# open chrome://inspect on the host with the device connected
```

- **PASS:** WebViews load only trusted HTTPS content; no bridge is reachable by that content; DevTools shows nothing in release.
- **FAIL:** a WebView loads attacker-influenceable content with a bridge or relaxed file access, or DevTools attaches in the production build.
- **Evidence:** the loaded URL in the proxy, and the DevTools session if debugging is exposed.

> **References:** MASVS-PLATFORM-2; MASWE-0068, MASWE-0069, MASWE-0074 (placeholder); MASTG-TEST-0031, MASTG-TEST-0033, MASTG-TEST-0252, MASTG-TEST-0334.

## MASVS-PLATFORM-3: The App Uses the User Interface Securely

PLATFORM-3 covers data leaking through the UI surface: the task-switcher snapshot, the soft keyboard's cache, and notifications. Only MASWE-0055 (screenshots) is finalized; the others (0053 UI leak, 0054 notifications, 0056 tapjacking, 0057 task affinity) are placeholders.

### Check 1: Sensitive data in the task-switcher screenshot (MASWE-0055; MASTG-TEST-0291, 0292)

When the app backgrounds, Android snapshots the current screen for the recents list. Without `FLAG_SECURE`, a sensitive screen is captured to disk and shown in recents.

```bash
grep -rnE 'FLAG_SECURE|setFlags|addFlags|clearFlags|setRecentsScreenshotEnabled' "$PKGPATH/"
```

- **PASS:** sensitive screens set `FLAG_SECURE` (and no code path clears it), so they blank in recents.
- **FAIL:** a screen showing credentials, tokens, or PII is captured into the recents snapshot with no `FLAG_SECURE`.
- **Evidence:** the sensitive screen and whether `FLAG_SECURE` is applied to its window.

### Check 2: Keyboard caching of sensitive fields (MASTG-TEST-0258, 0316)

A text field without a non-caching input type lets the keyboard learn and later suggest what the user typed, including secrets.

```bash
grep -rnE 'android:inputType|setInputType' "$PKGPATH/" apktool_out/res/layout/ 2>/dev/null
```

- **PASS:** sensitive fields use a non-caching input type (`textPassword`, `textNoSuggestions`, or the numeric password variants).
- **FAIL:** a password or sensitive field uses a default suggesting input type.
- **Evidence:** the field and its `inputType`.

### Dynamic confirmation

Background the app on a sensitive screen and look at the recents thumbnail; try to take a screenshot (blocked if `FLAG_SECURE` is set). Then check the on-disk snapshot.

```bash
# The framework stores recents snapshots here (path varies by version)
adb shell ls /data/system_ce/0/snapshots 2>/dev/null
```

For keyboard caching, type into a suspect field and see whether the keyboard offers autocomplete of previously entered values.

- **PASS:** the recents thumbnail is blank on sensitive screens, and sensitive fields offer no suggestions.
- **FAIL:** the thumbnail shows sensitive content, or the keyboard suggests a previously typed secret.
- **Evidence:** the recents screenshot or the suggestion observed.

> **Deeper on L2:** notifications leaking sensitive content (MASWE-0054; MASTG-TEST-0315) and tapjacking/overlay via `filterTouchesWhenObscured` (MASWE-0056; MASTG-TEST-0340) are further checks in this control; treat them as review prompts pending finalized OWASP weakness text.

> **References:** MASVS-PLATFORM-3; MASWE-0055 (screenshots, finalized); MASTG-TEST-0010, MASTG-TEST-0258, MASTG-TEST-0291, MASTG-TEST-0292, MASTG-TEST-0316.

## MASVS-CODE-1: The App Requires an Up-to-Date Platform Version

An app that runs on, or targets, an old platform version inherits that version's unpatched weaknesses and opts out of newer platform hardening. Both mapped weaknesses (MASWE-0077 running on a recent version, MASWE-0078 targeting the latest) are placeholders; the check is anchored to MASTG-TEST-0245.

### Check 1: Minimum and target SDK (MASTG-TEST-0245)

`minSdkVersion` is the oldest OS the app installs on; a low value means it runs on versions that no longer receive security fixes. `targetSdkVersion` decides which platform behaviors apply; a low target keeps the app on legacy-compatibility paths that skip newer security defaults.

```bash
grep -nE 'minSdkVersion|targetSdkVersion' apktool_out/apktool.yml
```

- **PASS:** `minSdkVersion` is a currently supported Android release, and `targetSdkVersion` is recent (at or near the latest, as Play Store policy already requires).
- **FAIL:** the app supports or targets an Android version well behind current, exposing it to platform bugs fixed in later releases.
- **Evidence:** the `minSdkVersion` and `targetSdkVersion` values.

> **References:** MASVS-CODE-1; MASWE-0077, MASWE-0078 (placeholder); MASTG-TEST-0245.

## MASVS-CODE-2: The App Has a Mechanism to Enforce Updates

If a critical vulnerability is fixed in an update, the app needs a way to push users off the vulnerable version, either Android's in-app update flow or a server-driven version gate. MASWE-0075 is a placeholder, and this is largely a design and runtime property; the static pass only confirms the mechanism exists.

### Check 1: An update-enforcement mechanism is present (MASTG-TEST-0392)

```bash
grep -rnE 'AppUpdateManager|AppUpdateInfo|InstallStateUpdatedListener|IMMEDIATE|minimumVersion|forceUpdate' "$PKGPATH/"
```

- **PASS:** the app checks a server-controlled minimum version, or uses the in-app update API, and can block use of an outdated build.
- **FAIL:** there is no mechanism to force an update when a vulnerable version is in the field.
- **Evidence:** the update-check code, or its absence.

### Dynamic confirmation

Point the app at an older version state (or an older installed build) and confirm the server or the app actually blocks it rather than letting it run.

- **PASS:** an outdated version is refused and the user is required to update.
- **FAIL:** an outdated build keeps working with no enforcement.
- **Evidence:** the app's behavior when running an outdated version.

> **References:** MASVS-CODE-2; MASWE-0075 (placeholder); MASTG-TEST-0036, MASTG-TEST-0392.

## MASVS-CODE-3: The App Only Uses Components Without Known Vulnerabilities

Two concerns: third-party dependencies carrying known CVEs, and the app's own binaries built without the free compiler hardening. MASWE-0076 (dependencies) is finalized; MASWE-0116 (compiler features) is a placeholder anchored to MASTG-TEST-0044.

### Check 1: Dependencies with known vulnerabilities (MASWE-0076; MASTG-TEST-0272)

The developer owns every bundled SDK and library, including transitive ones. Enumerate what ships in the package, pin each to a version, and check those versions against vulnerability databases.

```bash
# Native libraries bundled in the APK, with their file names (often versioned)
ls apktool_out/lib/*/
# Third-party SDK packages present in the decompiled tree
ls jadx_out/sources/ | grep -vE "^${PKG%%.*}$"
```

Run an automated scan for depth: MobSF surfaces bundled components, and OWASP Dependency-Check maps artifacts to CVEs (`dependency-check --scan target.apk`). Cross-reference identified versions against `osv.dev`.

- **PASS:** no bundled dependency maps to a known, exploitable CVE affecting the version in use.
- **FAIL:** a shipped library or SDK matches a known CVE relevant to how the app uses it.
- **Evidence:** the library, its version, and the CVE it matches.

### Check 2: Compiler-provided security features (MASWE-0116; MASTG-TEST-0044)

Native libraries should ship with stack canaries and position-independent code (PIC), the free protections against memory-corruption exploitation. Check every `.so`.

```bash
for so in apktool_out/lib/*/*.so; do echo "== $so =="; rabin2 -I "$so" | grep -E 'canary|pic|nx|relro'; done
```

- **PASS:** every native library reports `canary true` and `pic true` (and NX and RELRO where applicable).
- **FAIL:** a bundled `.so` is built without stack canaries or PIC.
- **Evidence:** the library and the missing protection from the `rabin2` output.

> **References:** MASVS-CODE-3; MASWE-0076 (dependencies, finalized), MASWE-0116 (placeholder); MASTG-TEST-0042, MASTG-TEST-0044, MASTG-TEST-0222, MASTG-TEST-0223, MASTG-TEST-0272.

## MASVS-CODE-4: The App Validates and Sanitizes All Untrusted Inputs

The trust-boundary control. Data arriving from the network, a backup, IPC, local storage, or the UI is all attacker-influenceable and must be validated before use. The MASWE family 0079-0084 states that principle per source; the concrete sinks below (all placeholder weaknesses, finalized MASTG tests) are where it goes wrong: SQL injection (0086), insecure deserialization (0088), and unsafe dynamic code loading (0085).

### Check 1: SQL injection (MASWE-0086; MASTG-TEST-0025, 0339)

Raw SQL built by concatenating untrusted input is injectable, whether in the app's own database calls or in a ContentProvider `selection` passed to another app.

```bash
grep -rnE 'rawQuery|execSQL|SQLiteDatabase|SELECT .*\+|selection' "$PKGPATH/"
```

- **PASS:** queries use parameterized `selectionArgs` or a query builder; no untrusted value is concatenated into SQL.
- **FAIL:** a query string is built by concatenating input from an intent, a URI parameter, or the network.
- **Evidence:** the query construction and the untrusted input that feeds it.

### Check 2: Insecure deserialization (MASWE-0088; MASTG-TEST-0337)

Deserializing attacker-controlled bytes into objects can trigger unexpected code paths. Java `Serializable`/`ObjectInputStream` over untrusted data is the classic case.

```bash
grep -rnE 'readObject|ObjectInputStream|Serializable|readSerializable|getSerializableExtra' "$PKGPATH/"
```

- **PASS:** untrusted data is parsed into typed models with validation (a checked JSON parse), not deserialized into arbitrary objects.
- **FAIL:** the app deserializes data from an intent, a file, or the network into objects without validation.
- **Evidence:** the deserialization call and where its input comes from.

### Check 3: Unsafe dynamic code loading (MASWE-0085)

Loading code from a writable or external location lets an attacker who can write there run code in the app's process.

```bash
grep -rnE 'DexClassLoader|PathClassLoader|System\.load\(|loadLibrary|createPackageContext' "$PKGPATH/"
```

- **PASS:** the app loads only code bundled inside the package from read-only locations.
- **FAIL:** it loads a DEX, JAR, or `.so` from external storage, a cache it shares, or a network download.
- **Evidence:** the loader call and the path it loads from.

### Dynamic confirmation

Drive malicious input through the entry points you mapped in PLATFORM-1. A ContentProvider is the cleanest SQLi target.

```bash
# Probe a provider's selection for injection
adb shell content query --uri content://<authority>/<path> --where "1=1) UNION SELECT ..."
```

For deserialization and dynamic loading, send a crafted intent extra or point a loadable path at attacker-writable storage and watch the result.

- **PASS:** crafted input is rejected or safely handled at every entry point.
- **FAIL:** an injected `--where`, a crafted extra, or a swapped code path changes behavior or returns unauthorized data.
- **Evidence:** the input sent and the app's response.

> **References:** MASVS-CODE-4; MASWE-0085, MASWE-0086, MASWE-0088 (placeholder); MASTG-TEST-0025, MASTG-TEST-0034, MASTG-TEST-0337, MASTG-TEST-0339.

## MASVS-RESILIENCE: Reading This Group Correctly

RESILIENCE is the **R profile**, not L1 or L2. It applies only to apps whose threat model includes a hostile user on their own device (banking, payments, DRM, high-value accounts). If the engagement is scoped to L1 or L2, this whole group is out of scope; confirm the profile before spending time here.

The finding logic is also inverted. For every group above, the finding was a weakness present. Here the concern is a **defense absent**. And OWASP is explicit, as it is with pinning, that every client-side resilience control is ultimately bypassable by a determined attacker with the device. So bypassing a control at runtime is expected and is not itself the finding. The finding is a control being **absent** or **trivially defeated** (a single boolean, no obfuscation, broken in seconds). You are judging whether it raises the attacker's cost meaningfully. The one exception is the debuggable flag under RESILIENCE-4, which is a clear misconfiguration with a hard pass or fail.

## MASVS-RESILIENCE-1: The App Validates the Integrity of the Platform

The app should detect an untrustworthy runtime, a rooted device, an emulator, or a virtualized clone, and respond (refuse to run, limit functionality, alert the backend). Weaknesses are all placeholder and R-profile: MASWE-0097 root/jailbreak detection, 0098 virtualization, 0099 emulator, 0100 device attestation.

### Check 1: Root and emulator detection (MASTG-TEST-0045, 0049)

Look for detection logic: checks for the `su` binary and common root paths, the RootBeer library, `test-keys` in the build tags, or emulator tells like a `goldfish` kernel or a generic `Build.FINGERPRINT`.

```bash
grep -rnE 'RootBeer|/system/xbin/su|/system/bin/su|test-keys|isDeviceRooted|Superuser\.apk|magisk|ro\.kernel\.qemu|goldfish|Build\.FINGERPRINT' "$PKGPATH/"
```

- **PASS:** the app detects root and emulator conditions through several independent checks and reacts, and stronger builds add hardware-backed attestation (Play Integrity).
- **FAIL:** no detection at all, or a single check that a bypass flips in one place.
- **Evidence:** the detection code and how the app responds when it triggers.

### Check 2: Device secure-lock verification (MASWE-0008; MASTG-TEST-0247)

An app holding sensitive data should confirm the device itself has a secure lock (PIN, pattern, password) set, since without one the lock screen protecting the app's data is meaningless. Android exposes this through `KeyguardManager.isDeviceSecure()` (stronger than `isKeyguardSecure()`) and `BiometricManager.canAuthenticate()`.

```bash
grep -rnE 'isDeviceSecure|isKeyguardSecure|KeyguardManager|BiometricManager|canAuthenticate' "$PKGPATH/"
```

- **PASS:** the app checks for a secure device lock through `isDeviceSecure()` (or `canAuthenticate()`) and restricts sensitive functionality when none is set.
- **FAIL:** the app never verifies a secure lock and exposes sensitive data on a device with no passcode.
- **Evidence:** the secure-lock check, or its absence, and what it gates.

### Dynamic confirmation

Run the app on a rooted device or emulator and watch whether it reacts. Then attempt the standard bypass and judge how much effort it takes. Separately, remove the device passcode and confirm whether the app notices the insecure lock state.

```bash
objection -g "$PKG" explore
# then:  android root disable
```

- **PASS:** the app reacts to the rooted environment, and defeating it takes real effort (multiple checks, native code, obfuscated logic), not a one-line hook.
- **FAIL:** the app runs unmodified on a rooted device with no reaction, or `android root disable` defeats it instantly.
- **Evidence:** the app's behavior before and after the bypass.

> **References:** MASVS-RESILIENCE-1; MASWE-0008 (secure lock), MASWE-0097, MASWE-0098, MASWE-0099, MASWE-0100 (placeholder, R profile); MASTG-TEST-0045, MASTG-TEST-0049, MASTG-TEST-0247, MASTG-TEST-0249, MASTG-TEST-0324, MASTG-TEST-0325.

## MASVS-RESILIENCE-2: The App Implements Anti-Tampering Mechanisms

The app should detect that it has been repackaged or modified, by verifying its own signing certificate and the integrity of its code and resources at runtime. Weaknesses are placeholder and R-profile: MASWE-0104 app integrity, 0105 resource integrity, 0106 store verification, 0107 runtime code integrity.

### Check 1: Signature and integrity verification (MASTG-TEST-0047, 0050)

Look for the app reading its own signing certificate and comparing it to an expected value, or checksumming its DEX or resources. Also confirm the app itself is signed with a modern scheme.

```bash
grep -rnE 'getPackageInfo|GET_SIGNATURES|GET_SIGNING_CERTIFICATES|signingInfo|checksum|CRC32|MessageDigest.*(dex|apk)' "$PKGPATH/"
apksigner verify --print-certs target.apk
```

- **PASS:** the app verifies its signing certificate (and ideally code and resource integrity) at runtime and refuses to run when they do not match, and it is signed with v2 or v3.
- **FAIL:** no integrity check, so a repackaged and re-signed build runs normally.
- **Evidence:** the verification code, or its absence, and the signature scheme.

### Dynamic confirmation

Repackage the app: decode, make a trivial change, rebuild, and re-sign with your own key. If it still runs, there is no effective tamper check.

```bash
apktool b apktool_out -o tampered.apk
apksigner sign --ks test.keystore tampered.apk
adb install tampered.apk
```

- **PASS:** the repackaged, re-signed build detects the mismatch and refuses to run or degrades.
- **FAIL:** the tampered build runs as normal.
- **Evidence:** the repackaged build and its behavior on launch.

> **References:** MASVS-RESILIENCE-2; MASWE-0104, MASWE-0105, MASWE-0106, MASWE-0107 (placeholder, R profile); MASTG-TEST-0038, MASTG-TEST-0047, MASTG-TEST-0050, MASTG-TEST-0224.

## MASVS-RESILIENCE-3: The App Implements Anti-Static-Analysis Mechanisms

The app should resist static reverse engineering: obfuscated security-relevant code, stripped debug symbols, and no leftover non-production code. Weaknesses are placeholder and R-profile: MASWE-0089 code obfuscation, 0090 resource obfuscation, 0093 debug symbols not removed, 0094 non-production resources, 0095 disable-security code not removed.

### Check 1: Obfuscation of security-relevant code (MASTG-TEST-0051, 0368)

Open the decompiled code and read the classes that handle crypto, auth, and the resilience checks themselves. Meaningful names and readable logic mean no obfuscation; mangled names (`a.a.b`) from R8 or DexGuard mean it is present.

```bash
ls "$PKGPATH" | head        # meaningful package/class names vs single letters
grep -rnE 'class [a-z]{1,2} |void [a-z]{1,2}\(' "$PKGPATH/" | head
```

- **PASS:** security-relevant code is obfuscated, so reading and modifying it takes significant effort.
- **FAIL:** the security-relevant code is fully readable with original names and structure.
- **Evidence:** a sample of the decompiled security code showing whether it is obfuscated.

### Check 2: Debug symbols in native libraries (MASTG-TEST-0288)

Native `.so` files should be stripped of symbols that hand a reverser function names and structure.

```bash
for so in apktool_out/lib/*/*.so; do echo "== $so =="; nm -D "$so" 2>/dev/null | head -3; done
```

- **PASS:** native libraries are stripped (few or no meaningful exported symbols).
- **FAIL:** libraries ship with full debugging symbols exposing internal function names.
- **Evidence:** the symbol listing for a bundled library.

> **Deeper on R:** the same control also covers anti-deobfuscation techniques not implemented (MASWE-0091) and static-analysis tools not prevented (MASWE-0092), both placeholder. These extend Check 1: beyond whether code is obfuscated, judge whether the obfuscation actively resists automated deobfuscation and tooling.

> **References:** MASVS-RESILIENCE-3; MASWE-0089, MASWE-0090, MASWE-0091, MASWE-0092, MASWE-0093, MASWE-0094, MASWE-0095 (placeholder, R profile); MASTG-TEST-0040, MASTG-TEST-0051, MASTG-TEST-0288, MASTG-TEST-0368, MASTG-TEST-0369.

## MASVS-RESILIENCE-4: The App Implements Anti-Dynamic-Analysis Mechanisms

The app should resist runtime analysis: the debuggable flag off, and detection of a debugger or a hooking framework. MASWE-0067 (debuggable flag) is the one finalized weakness in this group; 0101 debugger detection, 0102 dynamic-tool detection, and 0103 RASP are placeholder.

### Check 1: Debuggable flag disabled (MASWE-0067; MASTG-TEST-0226)

This is the hard pass or fail. A production build with `android:debuggable="true"` lets anyone attach a debugger to the running app and inspect or alter it.

```bash
grep -nE 'android:debuggable' apktool_out/AndroidManifest.xml
```

- **PASS:** `android:debuggable` is absent or `false` in the release manifest.
- **FAIL:** `android:debuggable="true"` ships in production.
- **Evidence:** the manifest `application` tag.

### Check 2: Debugger and hooking detection (MASTG-TEST-0046, 0341)

Look for runtime checks: `Debug.isDebuggerConnected()`, a `ptrace` self-attach, or Frida tells (the port 27042, `frida` in loaded libraries or `/data/local/tmp`, named pipes).

```bash
grep -rnE 'isDebuggerConnected|ptrace|TracerPid|27042|frida|gum-js-loop|xposed|substrate' "$PKGPATH/"
```

- **PASS:** the app detects a debugger and a hooking framework through several independent checks and reacts.
- **FAIL:** no detection, or a single check trivially bypassed.
- **Evidence:** the detection code and the app's response.

### Dynamic confirmation

Attach a debugger and run a Frida hook, and see whether the app notices. Then judge how hard its detection is to defeat.

```bash
frida -U -f "$PKG"     # does the app crash, exit, or ignore the injection?
```

- **PASS:** the app detects the debugger or Frida and reacts, and evading detection takes real effort.
- **FAIL:** Frida attaches with no reaction, or a one-line hook silences the check.
- **Evidence:** the app's behavior under a debugger and under Frida.

> **References:** MASVS-RESILIENCE-4; MASWE-0067 (debuggable flag, finalized), MASWE-0101, MASWE-0102, MASWE-0103 (placeholder, R profile); MASTG-TEST-0039, MASTG-TEST-0046, MASTG-TEST-0226, MASTG-TEST-0341, MASTG-TEST-0353.

## MASVS-PRIVACY: Reading This Group Correctly

PRIVACY is the **P profile**. Unlike the resilience group, every weakness here has finalized OWASP text, but part of the group is documentation and UX review rather than APK analysis: the adequacy of a privacy policy or a consent flow is not something you grep out of a package. The checks below cover the technically-testable core (permissions, data on the wire, tracking identifiers) and flag where the answer depends on comparing the app's behavior against its declarations.

The strongest instrument here is the same intercepting proxy from the NETWORK group: privacy is largely about what data leaves the device and who receives it, which you see on the wire.

## MASVS-PRIVACY-1: The App Minimizes Access to Sensitive Data and Resources

The app should request only the permissions and access its features genuinely need, and send sensitive data only where required. Two finalized weaknesses map here: MASWE-0117 inadequate permission management, and MASWE-0108 sensitive data in network traffic.

### Check 1: Permissions are minimized (MASWE-0117; MASTG-TEST-0254, 0255)

Read every requested permission and justify it against the app's actual features. Dangerous permissions (camera, microphone, fine location, contacts, SMS) need a clear reason, and a privacy-friendly alternative (coarse location, the photo picker) should be preferred where it exists.

```bash
grep -nE 'uses-permission|uses-feature' apktool_out/AndroidManifest.xml
```

- **PASS:** every requested permission maps to a feature the app actually provides, and less intrusive alternatives are used where possible.
- **FAIL:** the app requests dangerous permissions with no matching feature, or fine location where coarse would do.
- **Evidence:** the permission and the feature it is (or is not) justified by.

### Check 2: Sensitive data in network traffic (MASWE-0108; MASTG-TEST-0206)

This is a dynamic check. Proxy the app and drive its flows, then read the requests for PII the app sends: names, email, phone, precise location, contacts, device identifiers, especially to third-party hosts.

- **PASS:** sensitive data is sent only to first-party endpoints that need it, over TLS, and no more than the feature requires.
- **FAIL:** PII is sent to third-party analytics or ad hosts, or sensitive data is transmitted that the feature does not need.
- **Evidence:** the proxied request, the data it carries, and the destination host.

### Check 3: Sensitive data removed after use (MASWE-0118)

Data minimization includes cleanup at the end of a session: WebView cookies and storage, cached responses, and temporary files holding sensitive data should be cleared, not left on disk after they are no longer needed.

```bash
grep -rnE 'removeAllCookies|WebStorage|deleteAllData|clearCache|deleteRecursively|evictAll|clearHttpAuthUsernamePassword' "$PKGPATH/"
```

- **PASS:** the app clears WebView state, caches, and temporary sensitive files at logout or session end.
- **FAIL:** sensitive session data (WebView cookies, cached responses, temp files) persists on disk after it is no longer needed.
- **Evidence:** the sensitive data left behind after logout, from the on-disk sandbox pull in STORAGE-1.

> **References:** MASVS-PRIVACY-1; MASWE-0108, MASWE-0117, MASWE-0118; MASTG-TEST-0206, MASTG-TEST-0254, MASTG-TEST-0255.

## MASVS-PRIVACY-2: The App Prevents Identification of the User

The app should avoid persistent identifiers and unconsented tracking that let a user be recognized over time and across apps. Two finalized weaknesses: MASWE-0110 unique identifiers for tracking, and MASWE-0109 lack of anonymization.

### Check 1: Persistent tracking identifiers and SDKs (MASWE-0110; MASTG-TEST-0318, 0281)

Look for non-resettable identifiers (`ANDROID_ID`, hardware serial, MAC, IMEI) and resettable ones used without consent (the advertising ID), plus embedded tracking SDKs (ad networks, analytics).

```bash
grep -rnE 'ANDROID_ID|Settings\.Secure|AdvertisingIdClient|getAdvertisingId|getSerial|getMacAddress|getImei|getDeviceId|getSubscriberId' "$PKGPATH/"
ls jadx_out/sources/com/ | grep -iE 'google/android/gms/ads|facebook|appsflyer|adjust|amplitude|mixpanel|flurry'
```

- **PASS:** the app uses resettable identifiers only where needed and with consent, avoids non-resettable hardware identifiers, and does not link identifiers across services.
- **FAIL:** the app collects non-resettable identifiers, or uses the advertising ID for tracking without consent.
- **Evidence:** the identifier read and where it is sent.

### Dynamic confirmation

With the proxy running, watch for calls to known tracker domains and for identifiers on the wire. Compare the destination hosts against a public tracker list (the Exodus or DuckDuckGo tracker databases).

- **PASS:** no unconsented identifier reaches a tracking host.
- **FAIL:** an advertising or device identifier is sent to a known tracker domain without consent.
- **Evidence:** the request to the tracker host and the identifier it carries.

> **References:** MASVS-PRIVACY-2; MASWE-0109, MASWE-0110; MASTG-TEST-0281, MASTG-TEST-0318, MASTG-TEST-0319.

## MASVS-PRIVACY-3: The App is Transparent About Data Collection and Usage

The app's stated data practices should match what it actually does. Two finalized weaknesses: MASWE-0111 inadequate privacy policy, and MASWE-0112 inadequate data collection declarations. This control is partly a documentation comparison, not a pure code check.

### Check 1: Declarations match observed behavior (MASWE-0112; MASTG-TEST-0318)

Take the data and identifiers you found in PRIVACY-1 and PRIVACY-2, and the SDKs present, and compare them against the app's Play Store Data Safety declaration and privacy policy. The finding is a gap: data collected or shared that the app does not declare.

```bash
# The SDKs and permissions you already enumerated are the input to this comparison
grep -nE 'uses-permission' apktool_out/AndroidManifest.xml
```

- **PASS:** the declared data collection and sharing covers everything the app actually accesses and transmits.
- **FAIL:** the app collects or shares data (a tracking SDK, a permission-gated resource) that its Data Safety declaration or policy omits.
- **Evidence:** the observed collection and the declaration that fails to mention it.

> **References:** MASVS-PRIVACY-3; MASWE-0111, MASWE-0112; MASTG-TEST-0318.

## MASVS-PRIVACY-4: The App Provides User Control Over Their Data

The user should be able to consent before collection and to control their data afterward. The finalized weaknesses (MASWE-0113 data management, MASWE-0114 data visibility, MASWE-0115 consent) are largely UX and backend properties, so this control is mostly review rather than static analysis.

### Review prompts

- **Consent before collection:** is consent obtained before any tracking or non-essential collection begins, rather than collecting first and asking later? Confirm dynamically that no tracker call fires before consent.
- **Opt-out and control:** can the user decline tracking and still use the app, and reset or delete their data?
- **Granularity:** is consent specific per purpose, not a single all-or-nothing prompt?

```bash
# Static lead: where the app gates collection on a consent flag
grep -rnE 'consent|optOut|opt_out|gdpr|trackingEnabled|analyticsEnabled' "$PKGPATH/"
```

- **PASS:** consent is obtained up front and per purpose, and users can opt out and manage their data.
- **FAIL:** collection or tracking starts before consent, or there is no way to opt out.
- **Evidence:** the consent flow behavior, and any tracker call observed before consent in the proxy.

> **References:** MASVS-PRIVACY-4; MASWE-0113, MASWE-0114, MASWE-0115.
