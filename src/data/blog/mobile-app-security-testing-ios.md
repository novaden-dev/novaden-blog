---
author: Kayra
pubDatetime: 2026-07-06T00:00:00Z
title: "iOS App Security Testing: Static and Dynamic"
slug: "mobile-app-security-testing-ios"
description: "A per-control security-testing checklist for iOS apps against OWASP MASVS: how to unpack the app, and for each control the static checks (from a decrypted IPA) and the dynamic confirmation (on a jailbroken device), with PASS and FAIL conditions and the evidence to capture."
tags: ["ios", "security"]
category: notes
draft: true
featured: false
---

A per-control security-testing checklist for iOS apps against [OWASP MASVS](https://mas.owasp.org/MASVS/). Each control pairs a static pass (worked from a decrypted IPA) with a dynamic pass (worked against the app running on a jailbroken device): the static checks find the breadth, the dynamic checks confirm what only shows up at runtime. For the concepts behind it (static versus dynamic analysis, the MASVS profiles, why you always analyze the production build, and why scanner output is a lead rather than a verdict), start with [Mobile Security Testing Foundations](/posts/mobile-security-testing-foundations). This is the iOS counterpart to the [Android checklist](/posts/mobile-app-security-testing); the two mirror each other control for control.

## Setting Up the Static Pass

Before any control, you need the app in a readable form. On iOS that means dealing with two things Android does not. The binary is native machine code rather than bytecode, so it disassembles into rough pseudo-code instead of decompiling into near-source. And an App Store build is encrypted, so none of it is readable until you decrypt it.

### What an IPA actually is

An IPA is a ZIP. Unzip it and the app is a single bundle under `Payload/`, but most of what is inside is compiled or binary:

- `Payload/AppName.app`: the application bundle. Everything below lives inside it.
- The Mach-O executable (named after the app, no extension): the compiled code, as **native ARM64 machine code**. Not bytecode, not source.
- `Info.plist`: the app's declaration (bundle identifier, permission usage strings, URL schemes, App Transport Security settings). Usually a **binary plist**, so a text editor shows garbage.
- `embedded.mobileprovision`: the provisioning profile, carrying the signing certificate, the entitlements, and (for non-store builds) the list of allowed devices.
- `_CodeSignature/`: the code-signing hashes.
- `Frameworks/`: bundled dynamic libraries and third-party SDKs (`.framework`, `.dylib`).
- `Assets.car`, `.storyboardc`, `.nib`, `.strings`: compiled resources and UI.

### Decrypt first: the FairPlay check

An app downloaded from the App Store is encrypted with Apple's FairPlay DRM. Its Mach-O code section is ciphertext, so `class-dump`, a disassembler, and even `strings` return noise until it is decrypted. Check the encryption flag before anything else:

```bash
# cryptid 1 = still FairPlay-encrypted; 0 = decrypted and readable
otool -l "$BIN" | grep -A4 LC_ENCRYPTION_INFO
```

If `cryptid` is 1, you decrypt by running the app on a jailbroken device and dumping it from memory, with a tool like `frida-ios-dump` or `bagbak`. A build the client hands you directly (a development or enterprise IPA) is usually not FairPlay-encrypted and is ready as-is.

> **Watch out:** This step has no Android equivalent. A `cryptid` of 1 that you miss means every later search and disassembly runs against ciphertext, and you will wrongly conclude the app has no hardcoded strings or endpoints when you are really reading encrypted bytes.

### plutil and codesign: the declaration and entitlements

These read the app's declared posture, the iOS counterpart to Android's manifest.

- `plutil` converts the binary `Info.plist` to readable form and reads single keys. The plist holds the bundle identifier, the permission usage strings, the declared URL schemes, and any App Transport Security exceptions.

```bash
plutil -p "$APP/Info.plist"            # print the whole plist, readable
```

- `codesign` dumps the entitlements, which carry security-relevant grants: keychain access groups, app groups, and associated domains for universal links.

```bash
codesign -d --entitlements :- "$APP"   # print entitlements as XML
```

### class-dump and a disassembler: reading the code

iOS code does not decompile back to clean source the way DEX does. You reconstruct it from two angles.

- `class-dump` reads the Objective-C runtime metadata baked into the Mach-O and prints the class interfaces: class names, method signatures, and properties. It gives you the map of what the app defines, which is where you decide what to read.

```bash
class-dump "$BIN" > classes.h          # Objective-C interfaces
```

- A disassembler (**Hopper**, **Ghidra**, or **IDA**) loads the Mach-O and gives you the disassembly plus a best-effort pseudo-C decompilation of each function. This is the closest thing to jadx, but it is reconstructed from machine code, not bytecode, so it is rougher and needs more reading.

Swift changes this. `class-dump` relies on Objective-C metadata that Swift code largely does not emit, so a pure-Swift class barely shows up in its output. For Swift you lean on the disassembler and on demangling the symbol names:

```bash
nm "$BIN" | swift-demangle              # turn mangled Swift symbols into readable names
```

### Why you need both layers

The metadata layer (`plutil`, `codesign`, `otool`, `class-dump`) tells you the app's declared posture and its class and method map. The disassembler tells you what a given method actually does. One without the other is half a picture: the plist and interfaces show you that a keychain call exists and where it is, the disassembly shows you how the key is built and whether the stored value is protected. You move between them the same way every time, metadata to find the candidate, disassembly to judge it.

### Supporting tools

These cover the parts the two layers above do not.

- `otool -L "$BIN"`: list the dynamic libraries the binary links, to see which bundled SDKs and system frameworks are in use.
- `strings -a "$BIN"`: pull embedded strings (endpoints, tokens, key material, debug hints). On iOS this doubles as a decryption sanity check, since an encrypted Mach-O yields almost no readable strings.
- `security cms -D -i "$APP/embedded.mobileprovision"`: read the provisioning profile in full, including the raw entitlements and signing details.

### Run order

Order matters here, because later steps depend on the outputs of earlier ones.

1. **Get a decrypted IPA.** If the client hands you a development or enterprise build, it is usually already decrypted, so use it as-is. A copy from the App Store (for example through Apple Configurator 2) is FairPlay-encrypted and not usable for code analysis. To get a decrypted copy of a store app, dump it from a jailbroken device: `frida-ios-dump` and `bagbak` pull the app off the device and decrypt it in the same step, because they read the code out of memory after the OS has already decrypted it. `frida-ios-dump` needs `frida-server` running on the device first, so set that up before this step (see [Frida on Device](/posts/frida-on-device)). Without a jailbroken device you are limited to whatever decrypted build the client provides.

```bash
# Pull and decrypt a store app from a jailbroken device (frida running on it)
frida-ios-dump -o target.ipa <bundle-id>
```

2. **Unzip and locate the bundle**, then set shortcuts for the bundle and its executable.

```bash
unzip -q target.ipa -d ipa_out
APP=$(echo ipa_out/Payload/*.app)                                  # the .app bundle
BIN="$APP/$(plutil -extract CFBundleExecutable raw -o - "$APP/Info.plist")"

echo "$BIN"                                                        # sanity check: path to the Mach-O
```

3. **Confirm it is decrypted.**

```bash
otool -l "$BIN" | grep -A4 LC_ENCRYPTION_INFO                      # cryptid 0 = ready; 1 = decrypt first
```

4. **Read the declaration and entitlements.**

```bash
plutil -p "$APP/Info.plist"
codesign -d --entitlements :- "$APP"
```

5. **Dump the interfaces and open the binary in a disassembler.**

```bash
class-dump "$BIN" > classes.h                                      # then load "$BIN" in Hopper/Ghidra
```

> **Note:** iOS has no clean first-party path like Android's package directory. Bundled SDKs sit in `Frameworks/`, and static libraries are linked straight into the main Mach-O, so you cannot scope by folder. Scope instead by the app's class-name prefix or Swift module name (both visible in the `class-dump` output), and treat `Frameworks/` and system-framework hits as third-party unless a check is specifically about a dependency. The `APP` and `BIN` variables live only in the current terminal, so redefine them if you open a new one.

## Setting Up the Dynamic Pass

The static pass reads what the app *could* do; the dynamic pass watches what it *actually* does while running, which is the only way to confirm a runtime-built cipher string, a file written to disk, or a biometric gate that trusts a boolean. Each control below adds a dynamic check on top of its static ones. iOS dynamic testing needs a jailbroken device, because the app sandbox and the Keychain are otherwise closed to you.

- A **jailbroken device** on a version your jailbreak supports. Getting there (and installing `frida-server`) is covered in [Frida on-device setup](/posts/frida-on-device).
- **Frida** and **objection** for hooking and for pulling the app container (`ios-app-data`) without writing scripts.
- **`keychain-dumper`** (or objection's `ios keychain dump`) to read the Keychain items the app stored.
- An intercepting proxy (**Burp Suite** or **mitmproxy**) with its CA trusted on the device, for the network-facing checks once you reach NETWORK.

The core loop is the same as on Android: install, drive the feature you are testing, then inspect the container or hook the call while it happens. `objection -g "$BUNDLE_ID" explore` gives you `ios keychain dump` and `env` (which prints the container paths) in one session.

## MASVS-STORAGE-1: The App Securely Stores Sensitive Data

STORAGE-1 asks one thing: any sensitive data the app intentionally stores is protected wherever it lands. Build the sensitive-data map first (auth tokens, the session, PII, payment data, cryptographic keys); each check runs that list against a storage location. The control decomposes into two weaknesses, but only one applies to iOS:

- **MASWE-0006:** unencrypted sensitive data in private storage. Both platforms, profile L2.
- **MASWE-0007:** unencrypted sensitive data in shared storage that needs no user interaction. Scoped to Android; see Check 2 for why iOS is not affected.

Access restrictions, log leakage, and backup exposure belong to STORAGE-2, not here.

Hold one boundary. STORAGE-1 asks whether stored data is encrypted at all and whether its key lives in the Keychain. Whether the algorithm is strong or a key is hardcoded is why MASWE-0006 also maps to MASVS-CRYPTO-2; judge that under CRYPTO and note the crossover here rather than failing it in both places.

### Check 1: Unencrypted sensitive data in private storage (MASWE-0006)

The app sandbox is private, but a device backup, a jailbroken device, or a weak Data Protection class can still surface what is inside it. Confirm every sensitive value is either in the Keychain or in a file protected by iOS Data Protection.

iOS static analysis reads metadata and strings rather than source, so work from the `class-dump` output, the binary strings, and the disassembler. Find the storage call sites:

```bash
grep -nE 'NSUserDefaults|standardUserDefaults|writeToFile|writeToURL|NSKeyedArchiver|sqlite3_open|NSPersistentContainer' classes.h
strings -a "$BIN" | grep -iE 'NSUserDefaults|\.plist|\.sqlite|\.realm'
```

Then look for the protected paths, the Keychain and Data Protection:

```bash
grep -nE 'SecItemAdd|kSecClass|kSecAttrAccessible|NSFileProtection|completeFileProtection|FileProtectionType' classes.h
strings -a "$BIN" | grep -iE 'kSecAttrAccessible|NSFileProtection'
```

For a Swift app, `class-dump` shows little, so lean on the strings hits and the disassembly of the storage functions to confirm which value goes where.

- **PASS:** sensitive values live only in the Keychain, or in files and Core Data stores covered by Data Protection (the default class already protects files while the device is locked).
- **FAIL:** a token, password, key, or PII value sits in `NSUserDefaults`, a plaintext plist, or a file or database written with `NSFileProtectionNone`.
- **Evidence:** the storage call site, the value stored, and the Keychain accessibility or file protection class applied.

### Check 2: Unencrypted sensitive data in shared storage (MASWE-0007)

Not applicable on iOS, and worth recording as such rather than skipping silently. MASWE-0007 is scoped to Android because Android exposes external storage that any permitted app can read without user interaction. iOS enforces strict sandboxing: an app can only reach its own container, so there is no shared external storage to sweep.

The nearest iOS exposures, an App Group container shared with the vendor's other apps, the general `UIPasteboard`, and files surfaced through the Files app or iTunes file sharing, are real but fall under other controls (PLATFORM and STORAGE-2), so handle them there.

### Dynamic confirmation

Static reads the call sites; the container and the Keychain show what actually landed. Install the app, exercise every flow that stores something sensitive, then pull the container and dump the Keychain.

```bash
# Pull the app's data container from the jailbroken device
objection -g "$BUNDLE_ID" explore -c 'ios app-data'   # or frida-based ios-app-data

# Read the Keychain items the app stored, with their accessibility classes
objection -g "$BUNDLE_ID" explore -c 'ios keychain dump'   # or keychain-dumper on-device
```

Then grep the pulled container for the value you entered:

```bash
grep -rniE 'token|password|<known-secret-value>' container/
plutil -p container/Library/Preferences/*.plist    # NSUserDefaults lands here as plaintext
```

- **PASS:** the sensitive value lives only in the Keychain (with an appropriate accessibility class), or in a file covered by Data Protection; it does not appear in cleartext in a plist or an unprotected file.
- **FAIL:** the value you entered is readable in `NSUserDefaults`, a plist, or a file written with `NSFileProtectionNone`.
- **Evidence:** the container path or Keychain item and the cleartext value, tied to the flow that wrote it.

> **References:** MASVS-STORAGE-1; MASWE-0006 (iOS), MASWE-0007 (Android only); MASTG-TEST-0001, MASTG-TEST-0052.

## MASVS-STORAGE-2: The App Prevents Leakage of Sensitive Data

Where STORAGE-1 covers data the app deliberately stores, STORAGE-2 covers sensitive data that escapes by accident: into logs, through weak protections, or into a device backup. Of the four weaknesses under this control, three touch iOS:

- **MASWE-0001:** sensitive data written to logs. Both platforms, profiles L1, L2, P.
- **MASWE-0002:** insufficient access restrictions in internal storage. Scoped to Android for file permissions; the iOS-relevant part is weak Keychain accessibility, covered in Check 2.
- **MASWE-0003:** the app's backup is not encrypted. Android only; not applicable on iOS.
- **MASWE-0004:** sensitive data is not excluded from backup. Both platforms, profiles L1, L2, P.

### Check 1: Sensitive data written to logs (MASWE-0001)

A token, password, or PII value passed to a log call lands in the unified logging system, where it can be read from a connected device or a sysdiagnose. The check is whether sensitive values reach a log call in the shipping build.

```bash
grep -nE 'NSLog|os_log|OSLog|print\(|debugPrint' classes.h
strings -a "$BIN" | grep -iE 'password|token|secret|Authorization'
```

Since much iOS logging goes through `os_log` with format strings, read the disassembly of the logging call sites to see which arguments are sensitive.

- **PASS:** no sensitive value reaches a log call, or sensitive arguments are marked private in the `os_log` format (`%{private}@`) and logging is minimized in release.
- **FAIL:** a token, credential, session, or PII value is logged, including through a `%{public}@` or default specifier that prints it in the clear.
- **Evidence:** the log call site and the sensitive value it prints.

### Check 2: Weak Keychain accessibility for stored data (MASWE-0002)

MASWE-0002 is scoped to Android for file permissions, but its own text calls out the iOS analog: Keychain items holding sensitive data protected with an accessibility class that is too broad. `kSecAttrAccessibleAlways` keeps an item readable even when the device is locked, and the `...AfterFirstUnlock` and `...WhenUnlocked` classes without the `ThisDeviceOnly` suffix allow the item to migrate to a new device through a backup.

```bash
grep -nE 'kSecAttrAccessibleAlways|AfterFirstUnlock|WhenUnlocked|ThisDeviceOnly' classes.h
strings -a "$BIN" | grep -iE 'kSecAttrAccessible'
```

- **PASS:** sensitive Keychain items use an accessibility class no broader than needed, with the `...ThisDeviceOnly` suffix where the item should never leave the device.
- **FAIL:** a sensitive item uses `kSecAttrAccessibleAlways`, or uses a non-`ThisDeviceOnly` class while holding device-bound secrets.
- **Evidence:** the `SecItemAdd` call and the accessibility attribute set on the item.

### Check 3: Backup not encrypted (MASWE-0003)

Not applicable on iOS. MASWE-0003 is scoped to Android's backup device conditions. On iOS, backup encryption is controlled by the user (an encrypted Finder or iTunes backup) and iCloud backup is encrypted by the platform, so there is no app-level backup-encryption condition to test statically. Record it as not applicable; the app-side concern on iOS is what gets included, which is Check 4.

### Check 4: Sensitive data not excluded from backup (MASWE-0004)

iOS backs up the app container to iCloud and to local backups by default. Files the app writes into backed-up locations (the `Documents` and `Application Support` directories) are swept in unless explicitly excluded. An attacker with a backup can extract those files, or tamper and restore.

```bash
grep -nE 'isExcludedFromBackup|NSURLIsExcludedFromBackupKey|URLResourceValues' classes.h
strings -a "$BIN" | grep -iE 'ExcludedFromBackup'
```

- **PASS:** sensitive files are marked excluded from backup with `isExcludedFromBackup`, or they live in a non-backed-up location (`Caches`, `tmp`) or in the Keychain with a `ThisDeviceOnly` class.
- **FAIL:** a sensitive file in `Documents` or `Application Support` is written without the exclusion flag and is not otherwise protected.
- **Evidence:** the file write location and whether the exclusion flag is set.

### Dynamic confirmation

Watch the unified log while you drive the app, and check the backup path for the excluded-file question. For logs, stream the device log and filter to the app while you log in and perform a sensitive action.

```bash
# Stream the device log (libimobiledevice) while exercising the app
idevicesyslog | grep -iE "$BUNDLE_ID|token|password|Bearer"
```

For backup inclusion (MASWE-0004), take an unencrypted local backup and look for sensitive files that should have been excluded, or confirm the file carries the `isExcludedFromBackup` flag at runtime.

```bash
idevicebackup2 backup --full ./backup_out
# then browse the backup for the app's Documents/Application Support files
```

- **PASS:** no sensitive value prints to the log during real use; sensitive files are absent from the backup or live in the Keychain with a `...ThisDeviceOnly` class.
- **FAIL:** a token or PII value appears in the unified log, or a sensitive file from `Documents`/`Application Support` shows up in the backup.
- **Evidence:** the log line, or the sensitive file recovered from the backup.

> **References:** MASVS-STORAGE-2; MASWE-0001, MASWE-0002 (iOS Keychain accessibility), MASWE-0004; MASWE-0003 (Android only).

## MASVS-CRYPTO-1: The App Employs Current Strong Cryptography and Uses It According to Best Practices

CRYPTO-1 asks whether the cryptography itself is sound: the algorithm, the mode, the padding, and the randomness, independent of any key. Judge the primitive and its configuration here; key generation and storage are CRYPTO-2. For the model behind these checks (cipher modes, padding oracles, authenticated encryption, secure randomness), see [Cryptography Foundations](/posts/cryptography-foundations). Four weaknesses map to this control:

- **MASWE-0020:** improper encryption (broken algorithm, broken mode, short key, bad IV, or fake encryption). Both platforms, profiles L1, L2.
- **MASWE-0023:** risky padding that enables padding-oracle attacks. Both platforms, profiles L1, L2.
- **MASWE-0027:** improper random number generation. Both platforms, profiles L1, L2.
- **MASWE-0019:** risky or home-rolled cryptographic implementations. Both platforms, profile L2.

On iOS the primitives come from CommonCrypto (`CCCrypt` and the `kCCAlgorithm...` constants), the `SecKey` APIs for RSA, or CryptoKit. CryptoKit only exposes modern algorithms, so its presence is a good sign; the risk sits in CommonCrypto calls and any home-rolled code. Read the `class-dump` output, the binary strings, and the disassembly of the crypto call sites.

### Check 1: Broken algorithm, mode, or key length (MASWE-0020)

`kCCAlgorithmDES`, `3DES`, `RC4`, and `RC2` are retired. `kCCOptionECBMode` leaks structure the same way AES-ECB does on Android (identical plaintext blocks yield identical ciphertext blocks). `CC_MD5` and `CC_SHA1` are broken for security use. And XOR or Base64 in place of encryption is encoding, not protection.

```bash
grep -nE 'CCCrypt|kCCAlgorithm(DES|3DES|RC4|RC2|Blowfish|CAST)|kCCOptionECBMode|CC_MD5|CC_SHA1' classes.h
strings -a "$BIN" | grep -iE 'kCCAlgorithm|kCCOptionECB|MD5|SHA1'
```

- **PASS:** encryption uses AES with an authenticated or CBC mode and a 256-bit key, or CryptoKit; hashing uses SHA-256 or better.
- **FAIL:** a sensitive value is protected with DES, 3DES, RC4, or RC2; with ECB mode; with an AES key under 256 bits; with MD5 or SHA-1 for a security purpose; or with XOR or Base64 standing in for encryption.
- **Evidence:** the `CCCrypt` call site, the algorithm and mode constants passed, and the key length.

### Check 2: Risky padding (MASWE-0023)

The same padding-oracle exposure applies: RSA with PKCS#1 v1.5 (`kSecPaddingPKCS1` through `SecKeyEncrypt`), and AES-CBC with PKCS#7 (`kCCOptionPKCS7Padding`) when no separate MAC authenticates the ciphertext.

```bash
grep -nE 'kSecPaddingPKCS1|SecKeyEncrypt|SecKeyDecrypt|kCCOptionPKCS7Padding' classes.h
strings -a "$BIN" | grep -iE 'PKCS1|OAEP|PKCS7'
```

- **PASS:** RSA uses OAEP (`kSecPaddingOAEP` or `SecKeyCreateEncryptedData` with an OAEP algorithm); symmetric encryption uses an authenticated mode or pairs CBC with an Encrypt-then-MAC check.
- **FAIL:** RSA uses PKCS#1 v1.5, or AES-CBC with PKCS#7 carries no MAC and the decrypt path leaks distinct padding errors.
- **Evidence:** the padding constant, and for CBC whether any MAC covers the ciphertext.

### Check 3: Insecure random number generation (MASWE-0027)

`rand`, `random`, `srand`, and `drand48` are non-cryptographic and predictable. Security-relevant randomness on iOS should come from `SecRandomCopyBytes` or `arc4random` (both cryptographically secure); CryptoKit's key types seed from the system CSPRNG.

```bash
grep -nE '\brand\(|\brandom\(|\bsrand\(|drand48|SecRandomCopyBytes|arc4random' classes.h
strings -a "$BIN" | grep -iE 'SecRandom|arc4random'
```

- **PASS:** every security-relevant random value comes from `SecRandomCopyBytes`, `arc4random`, or CryptoKit.
- **FAIL:** a key, IV, token, salt, or nonce is drawn from `rand`, `random`, or `drand48`.
- **Evidence:** the generator call site and what the value is used for.

### Check 4: Risky or home-rolled cryptography (MASWE-0019, L2)

The standard is to use vetted libraries: CryptoKit, CommonCrypto, or Apple's `Security` framework. Hardcoded S-boxes, long chains of bit shifts and XORs, or a high-entropy blob hiding an algorithm signal a hand-rolled primitive that has not been reviewed.

```bash
strings -a "$BIN" | grep -iE 'aes|rc4|sbox|encrypt|decrypt'
```

Pair the strings hits with the disassembly of any function that does not resolve to a CommonCrypto, `SecKey`, or CryptoKit symbol.

- **PASS:** all cryptography runs through CryptoKit, CommonCrypto, or the `Security` framework.
- **FAIL:** the app implements its own cipher, hash, or PRNG, or links an unvetted crypto library.
- **Evidence:** the custom implementation and the operation it stands in for.

### Dynamic confirmation

CommonCrypto routes almost everything through one function, `CCCrypt`, whose arguments include the algorithm, the options (ECB, padding), the key, and the IV. Hooking it shows the real values at runtime, including algorithms selected from config that a static read of `classes.h` would miss.

```bash
# Log the algorithm, options, key length, and IV passed to CCCrypt
frida-trace -U -f "$BUNDLE_ID" -i 'CCCrypt'
# then edit the generated __handlers__/CCCrypt.js to print args:
#   onEnter: log('alg=' + args[1] + ' options=' + args[2] +
#                ' keyLen=' + args[4] + ' iv=' + args[5].readByteArray(16))
```

Drive an encrypt flow twice and compare IVs for reuse. OWASP's iOS crypto tests are static-reference plus runtime; this is the runtime half of MASTG-TEST-0061.

- **PASS:** every `CCCrypt` call at runtime uses an approved algorithm with no ECB option, a 256-bit key, and a fresh IV each time; or the app uses CryptoKit, which exposes only modern primitives.
- **FAIL:** a runtime call resolves to DES/RC4, sets the ECB option, uses a short key, or reuses an IV, where the static read did not reveal it.
- **Evidence:** the logged algorithm, option flags, key length, and IV values across runs.

> **Deeper on L2:** CRYPTO-1 has finer-grained placeholder weaknesses that the checks above partly cover: improper hashing (MASWE-0021, the MD5/SHA-1 part of Check 1), predictable IVs (MASWE-0022, the IV part of Check 1 and the dynamic reuse check), improper MAC use (MASWE-0024), and improper signature generation and verification (MASWE-0025, MASWE-0026). Where an app uses a MAC or digital signatures, review those explicitly against the same primitive-strength logic.

> **References:** MASVS-CRYPTO-1; MASWE-0019, MASWE-0020, MASWE-0023, MASWE-0027; MASTG-TEST-0061, MASTG-TEST-0063.

## MASVS-CRYPTO-2: The App Performs Key Management According to Best Practices

Where CRYPTO-1 judges the primitive, CRYPTO-2 judges the key: how it is generated, and where it lives. Two weaknesses carry current OWASP text:

- **MASWE-0009:** improper cryptographic key generation (weak size or weak source). Both platforms, profiles L1, L2.
- **MASWE-0014:** cryptographic keys not properly protected at rest. Both platforms, profiles L1, L2. Also maps MASVS-STORAGE-1.

This control is the home for the hardcoded-key finding raised under STORAGE-1. An app that encrypts with a strong algorithm but ships the key in its binary passes STORAGE-1's "is it encrypted" question and fails here; report it once, under CRYPTO-2.

### Check 1: Weak key generation (MASWE-0009)

RSA under 2048 bits and AES under 256 bits are below the floor for sensitive data. The key size on iOS is set through `kSecAttrKeySizeInBits` when creating a `SecKey`, or by the CryptoKit key type chosen.

```bash
grep -nE 'SecKeyCreateRandomKey|kSecAttrKeySizeInBits|kSecAttrKeyType|SymmetricKeySize' classes.h
strings -a "$BIN" | grep -iE 'kSecAttrKeySizeInBits|SymmetricKeySize'
```

- **PASS:** symmetric keys are at least 256 bits and RSA keys at least 2048 bits, created through `SecKeyCreateRandomKey` or CryptoKit from a secure source.
- **FAIL:** a key is created under the size floor, or derived from a predictable source such as `rand` (see CRYPTO-1 Check 3).
- **Evidence:** the key-creation call site and the size attribute.

### Check 2: Keys not protected at rest (MASWE-0014)

The strongest key is worthless if it sits next to the data it protects. Keys hardcoded in the binary, stored in `NSUserDefaults` or a plist, or built from a literal byte array are all extractable. Keys should be generated on-device and held in the Keychain, backed by the Secure Enclave (`kSecAttrTokenIDSecureEnclave`) where the use case allows.

```bash
grep -nE 'SecItemAdd|kSecAttrTokenIDSecureEnclave|SecKeyCreateRandomKey|SymmetricKey\(data' classes.h
strings -a "$BIN" | grep -iE '^[A-Fa-f0-9]{32,}$|secret|apikey|private_key'
```

Read the strings hits for anything that looks like a raw key, and confirm the app pulls keys from the Keychain rather than a constant.

- **PASS:** keys are generated into and retrieved from the Keychain (Secure Enclave where supported), never appearing as literals in the binary or in cleartext storage.
- **FAIL:** a key is hardcoded, built from a literal byte array, or written to `NSUserDefaults`, a plist, or a file in cleartext.
- **Evidence:** the key literal or the storage write, and the code path that reads it back.

> **Deeper on L2:** OWASP also tracks key derivation strength (MASWE-0010, PBKDF2 iteration count), key rotation (0011), wrong or reused key usage (0012), imported and exported keys (0016, 0017), and key access restrictions such as `SecAccessControl` with biometry (0018). These are placeholder weaknesses without finalized OWASP test text, so they are review prompts rather than fixed pass or fail checks for now.

### Dynamic confirmation

The runtime question is where the key comes from. Hook the same `CCCrypt` (its fourth argument is the key buffer) to capture the actual key bytes, and dump the Keychain to see whether the app stores keys there rather than deriving them from a constant. A key that is identical on every run and never came from the Keychain is hardcoded.

```bash
# Capture the key buffer CCCrypt receives (see the CRYPTO-1 handler)
frida-trace -U -f "$BUNDLE_ID" -i 'CCCrypt'   # print args[3] as a byte array

# See what keys the app actually holds in the Keychain
objection -g "$BUNDLE_ID" explore -c 'ios keychain dump'
```

- **PASS:** keys used at runtime are released from the Keychain (Secure Enclave where supported) and are not identical constants across runs.
- **FAIL:** the same key bytes appear on every run, revealing a hardcoded or constant-derived key.
- **Evidence:** the key bytes captured at `CCCrypt`, matched to their source in the static read.

> **References:** MASVS-CRYPTO-2; MASWE-0009, MASWE-0014; MASTG-TEST-0062. Key-at-rest also relates to MASVS-STORAGE-1.

## MASVS-AUTH-1: The App Uses Secure Authentication and Authorization Protocols

AUTH is the group where a static pass is deliberately narrow. Authentication and authorization decisions are made on the server, and local authentication is a runtime event, so most of this group is tested dynamically or against the backend. Of the AUTH weaknesses, only one carries finalized OWASP test text, and it is the thing the client package fully exposes: secrets that should never ship inside it.

- **MASWE-0005:** API keys hardcoded in the app package. Both platforms, profiles L1, L2.

Auth material stored unencrypted on the device (MASWE-0036) is the other static-visible AUTH-1 concern, but it is the same finding as STORAGE-1 Check 1 and CRYPTO-2 Check 2; judge it there and cross-reference rather than failing it a third time here.

### Check 1: Hardcoded API keys and auth secrets (MASWE-0005)

Anything embedded in the binary, the `Info.plist`, or a bundled resource is extractable by unzipping the IPA and running strings against the binary. Sweep the binary and the packaged resources for key-shaped values, then confirm each hit is a real secret rather than a public identifier.

```bash
strings -a "$BIN" | grep -iE 'api[_-]?key|secret|password|bearer|AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|sk_live_|-----BEGIN'
grep -iE 'api[_-]?key|secret|token|client_secret' Info.plist
```

A dedicated secret scanner catches formats a hand-written pattern misses:

```bash
gitleaks detect --no-git --source Payload/
```

- **PASS:** no live secret ships in the package; the app authenticates through short-lived tokens obtained at runtime, or any embedded key is a public client identifier scoped to the minimum permissions.
- **FAIL:** a usable API key, client secret, password, or private key is present in the binary, the `Info.plist`, or a bundled resource.
- **Evidence:** the location, the value, and what service it authenticates to. A key you can actually use against the backend is a confirmed finding, not a lead.

### Dynamic confirmation

A key in the binary is a lead; a key that works against the backend is the finding. Use the extracted key directly, and proxy the app's live traffic to see the key and any auth headers in flight.

```bash
# Use the extracted key against the API it targets
curl -s 'https://api.example.com/v1/resource?key=AIza...' | head

# Or route the app through a proxy (device HTTP proxy -> Burp/mitmproxy) and drive it
```

- **PASS:** the extracted key is rejected, is a public identifier, or is scoped so it cannot perform sensitive actions.
- **FAIL:** the key returns real data, performs billed operations, or unlocks restricted functionality.
- **Evidence:** the request sent with the extracted key and the backend's response.

> **Deeper on L2:** OWASP also tracks not using platform-provided authentication APIs (MASWE-0032), passwordless authentication not implemented (MASWE-0035), and authentication material sent over insecure connections (MASWE-0037, which overlaps the NETWORK-1 cleartext check). These are placeholder weaknesses without finalized test text; treat them as review prompts.

> **References:** MASVS-AUTH-1; MASWE-0005 (MASWE-0036 cross-references STORAGE-1 and CRYPTO-2).

## MASVS-AUTH-2: The App Performs Local Authentication Securely

Local authentication is a biometric (Face ID, Touch ID) or device-passcode unlock done on the device. The static question is not whether the app calls the biometric API, but whether a successful biometric actually releases a secret, or is just a boolean the app chooses to trust.

- **MASWE-0044:** biometric authentication can be bypassed. Both platforms, profile L2.
- **MASWE-0043:** a custom app PIN is not bound to the platform keystore. Both platforms, profile L2. Also maps MASVS-CRYPTO-2.

### Check 1: Local authentication gates a Keychain secret (MASWE-0044, MASWE-0043)

There are two ways to build a Face ID gate. The insecure one calls `LAContext.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics)` and proceeds when the completion handler returns `true`; that result is a boolean, and a boolean can be forced at runtime with a tool like objection, so the gate is cosmetic. The secure one stores the sensitive item in the Keychain guarded by a `SecAccessControl` created with a biometry flag, so the item is only released by the Secure Enclave on a real biometric match. There is no boolean to flip.

```bash
grep -nE 'LAContext|evaluatePolicy|LAPolicy|SecAccessControlCreateWithFlags|kSecAccessControlBiometry|kSecAccessControlUserPresence|kSecAccessControlTouchID|SecItemCopyMatching' classes.h
strings -a "$BIN" | grep -iE 'evaluatePolicy|BiometryCurrentSet|BiometryAny|TouchIDCurrentSet'
```

Read each `evaluatePolicy` call and each Keychain access: check whether the sensitive item is protected by a `SecAccessControl` biometry flag rather than gated by a bare policy evaluation.

- **PASS:** the sensitive secret is a Keychain item guarded by `SecAccessControl` with a biometry flag, ideally `...BiometryCurrentSet` so a new enrollment invalidates it; the app cannot proceed without the released item.
- **FAIL:** the flow relies on the `evaluatePolicy` boolean with no Keychain or crypto binding, or a Keychain item uses `kSecAttrAccessibleAlways`-style access with no biometry control, or a custom PIN is compared in code without unlocking a protected item.
- **Evidence:** the `evaluatePolicy` call site or the `SecAccessControl` flags, and what the success path actually gates.

### Dynamic confirmation

This is the most important dynamic check in the group. If the gate is an `evaluatePolicy` boolean, objection's biometrics bypass forces it to return success and you walk through without a valid Face ID or Touch ID. If the secret is a Keychain item guarded by `SecAccessControl`, the same attack fails because the item is never released.

```bash
objection -g "$BUNDLE_ID" explore
# then at the prompt:  ios ui biometrics_bypass
```

The technique is documented in objection's iOS biometrics bypass notes: it hooks `LAContext.evaluatePolicy` and flips the callback. If the bypass grants access, the gate was a trusted boolean. Separately, confirm server-side enforcement: proxy a sensitive action, then replay the request with the auth token stripped or altered and check the server rejects it.

- **PASS:** the bypass fails because access depends on a Keychain item that never gets released, and the server rejects a tampered or missing token.
- **FAIL:** forcing `evaluatePolicy` to succeed lets the app proceed, or the server accepts an action after the client-side gate is bypassed.
- **Evidence:** the bypass attempt and the app's response, plus the server's response to the tampered request.

> **Deeper on L2:** OWASP also tracks authentication and authorization enforced only locally instead of on the server (MASWE-0041, MASWE-0042), auth tokens not validated (MASWE-0038), and keys not invalidated on new biometric enrollment (MASWE-0046, which is why `...CurrentSet` is preferred over `...Any`). The server-side items cannot be proven from the client alone; statically, flag any security decision the app makes purely on local state with no backend call, and confirm it dynamically with the replay test above.

> **References:** MASVS-AUTH-2; MASWE-0043, MASWE-0044; MASTG-TEST-0064, MASTG-TEST-0266, MASTG-TEST-0268, MASTG-TEST-0270.

## MASVS-AUTH-3: The App Requests Re-Authentication for Sensitive Operations

AUTH-3 covers step-up authentication: re-prompting the user before a high-value action (a payment, a settings change, a credential update), and multi-factor flows. This is almost entirely a design and runtime property, so there is no finalized static check here; the weaknesses (MASWE-0028 MFA best practices, MASWE-0029 step-up after login, MASWE-0030 contextual re-authentication) are all placeholders.

Statically, you can record whether sensitive actions re-invoke the biometric or passcode prompt at all, as a lead for the dynamic pass:

```bash
grep -nE 'evaluatePolicy|deviceOwnerAuthentication|LAContext' classes.h
```

A single `LAContext` reused across the app with a long `touchIDAuthenticationAllowableReuseDuration` means one unlock covers a long window, which weakens step-up.

### Dynamic confirmation

Step-up is a runtime property, so this is where it is actually judged. Reach a sensitive action (a payment, a beneficiary or password change) and watch whether the app forces a fresh Face ID or passcode prompt, or rides the session from the initial login. Then test the server: proxy the request for the sensitive action and replay it without whatever step-up factor the client added.

- **PASS:** the sensitive action triggers a fresh prompt, and the server rejects the replayed request that lacks the step-up factor.
- **FAIL:** the action proceeds on the original session with no re-authentication, or the server accepts the replay without the step-up factor.
- **Evidence:** the action tested, whether a prompt appeared, and the server's response to the replayed request.

> **References:** MASVS-AUTH-3; MASWE-0028, MASWE-0029, MASWE-0030 (all placeholder; primarily dynamic).

## MASVS-NETWORK-1: The App Secures All Network Traffic According to Best Practices

NETWORK-1 is the baseline question: is every connection encrypted, authenticated, and made through an API that enforces both. On iOS the platform default is strong (App Transport Security blocks cleartext unless the app opts out), so much of the static work is reading what the app opted out of. Four finalized weaknesses map here:

- **MASWE-0050:** cleartext traffic. Both platforms, profiles L1, L2.
- **MASWE-0052:** insecure certificate validation. Both platforms, profiles L1, L2.
- **MASWE-0049:** proven networking APIs not used. Both platforms, profile L2.
- **MASWE-0051:** unprotected open ports. Both platforms, profile L2.

For the dynamic side you need an intercepting proxy in place: set the device proxy to Burp or mitmproxy and trust its CA profile, as described in Setting Up the Dynamic Pass.

### Check 1: Cleartext traffic (MASWE-0050)

ATS blocks cleartext by default; the finding is the app weakening it. Read the `NSAppTransportSecurity` dictionary in `Info.plist` for a global `NSAllowsArbitraryLoads` or per-domain `NSExceptionAllowsInsecureHTTPLoads`, and grep the binary for `http://` endpoints.

```bash
plutil -p "$APP/Info.plist" | grep -A20 NSAppTransportSecurity
strings -a "$BIN" | grep -iE 'http://[a-z]'
```

- **PASS:** ATS is left at its secure default, with no `NSAllowsArbitraryLoads` and only narrow, justified domain exceptions; all endpoints are HTTPS.
- **FAIL:** `NSAllowsArbitraryLoads` is true, a sensitive domain has `NSExceptionAllowsInsecureHTTPLoads`, or a sensitive endpoint is reached over `http://`.
- **Evidence:** the ATS exception in the plist, and the cleartext URL.

### Check 2: Insecure certificate validation (MASWE-0052)

HTTPS that does not verify the peer. On iOS this lives in the authentication-challenge handler: a `URLSession` delegate that answers a server-trust challenge with `.useCredential` and the presented trust without evaluating it, or a `WKWebView` navigation delegate doing the same.

```bash
grep -nE 'URLSession|didReceiveChallenge|NSURLAuthenticationMethodServerTrust|serverTrust|useCredential|SecTrustEvaluate|WKNavigationDelegate' classes.h
strings -a "$BIN" | grep -iE 'AllowsAnyHTTPSCertificate|kCFStreamSSLValidatesCertificateChain'
```

Read each challenge handler: calling the completion handler with `.useCredential` for every server-trust challenge, without a real `SecTrustEvaluateWithError`, trusts any certificate.

- **PASS:** the app relies on ATS default trust evaluation, or any custom handler calls `SecTrustEvaluateWithError` and rejects on failure.
- **FAIL:** a challenge handler accepts the server trust unconditionally, or `kCFStreamSSLValidatesCertificateChain` is disabled.
- **Evidence:** the challenge-handler method and how it resolves the trust.

### Check 3: Roll-your-own networking (MASWE-0049, L2)

Custom stacks and the deprecated `NSURLConnection` skip protections that `URLSession` handles for you. Prefer `URLSession` or a vetted library like Alamofire.

```bash
grep -nE 'NSURLConnection|CFStream|CFSocket|BSD socket|getaddrinfo' classes.h
```

- **PASS:** networking goes through `URLSession` or `Network.framework`, or a vetted library.
- **FAIL:** the app uses the deprecated `NSURLConnection` or a hand-built socket stack for sensitive traffic.
- **Evidence:** the low-level networking call site and what it carries.

### Check 4: Unprotected open ports (MASWE-0051, L2)

Less common on iOS but possible when an app embeds a local server or a peer-to-peer socket bound broadly.

```bash
grep -nE 'CFSocket|GCDAsyncSocket|NWListener|bindToPort|listen\(' classes.h
```

- **PASS:** the app opens no listening socket, or binds to loopback with authentication.
- **FAIL:** the app listens on a broadly bound socket with no authentication.
- **Evidence:** the listener setup and the interface and port it exposes.

### Dynamic confirmation

With the proxy in place, drive every network feature and read the flows. Cleartext shows up as plain HTTP in the proxy history. For certificate validation, present a certificate the device does not trust (the proxy's default, before you trust its CA profile): if the app still connects, it is accepting any certificate.

- **PASS:** no cleartext appears in the proxy; with the proxy CA untrusted, TLS connections fail; no unexpected listening port answers.
- **FAIL:** plain HTTP is observed, or traffic intercepts even though the proxy CA is untrusted (broken validation), or a service answers on an open port.
- **Evidence:** the proxy flow, or the connection to the open port.

> **Deeper on L2:** OWASP also tracks insecure machine-to-machine communication (MASWE-0048) and data sent unencrypted inside an otherwise encrypted connection (MASWE-0096, a second layer of plaintext within TLS). These are placeholder weaknesses; where the app has non-user M2M channels or wraps its own payload encoding, review them against the same transport logic.

> **References:** MASVS-NETWORK-1; MASWE-0048, MASWE-0049, MASWE-0050, MASWE-0051, MASWE-0052, MASWE-0096; MASTG-TEST-0065, MASTG-TEST-0066, MASTG-TEST-0067.

## MASVS-NETWORK-2: The App Performs Identity Pinning for Developer-Controlled Endpoints

Pinning ties the app to a specific certificate or public key, so that even a valid CA-issued certificate is rejected unless it matches the pin. Its absence is not a NETWORK-1 failure (ATS still validates the chain); it is a separate L2 expectation for endpoints the developer controls.

- **MASWE-0047:** insecure identity pinning. Both platforms, profile L2.

One framing to hold, straight from OWASP: pinning is defense-in-depth and is bypassable by anyone who can reverse the app, so bypassing it at runtime is expected and is not itself the finding. The finding is pinning being absent, or misconfigured so it does not actually enforce.

### Check 1: Pinning is present and correctly configured (MASWE-0047)

Look for a pinning library (TrustKit, Alamofire's `ServerTrustManager` / `PinnedCertificatesTrustEvaluator`) or pins declared in ATS, or a challenge handler that compares the server public key against an embedded pin.

```bash
grep -nE 'TrustKit|pinnedDomains|kTSKPublicKeyHashes|ServerTrustManager|PinnedCertificatesTrustEvaluator|publicKeyHash|SecTrustCopyKey' classes.h
strings -a "$BIN" | grep -iE 'TSKPublicKeyHashes|\.cer|pinned'
```

- **PASS:** pinning is enforced for developer-controlled endpoints through TrustKit, Alamofire, or a correct custom key comparison, with a backup pin.
- **FAIL:** no pinning on sensitive endpoints, pins fetched over an insecure channel, or a custom implementation that accepts any chain to a trusted root instead of the specific key.
- **Evidence:** the pinning config and the domains it covers.

### Dynamic confirmation

The decisive test runs in two steps. First, trust the proxy CA profile on the device. If the app now intercepts, there is no pinning. If it refuses to connect while your CA is trusted, pinning is present. Then confirm by disabling it.

```bash
objection -g "$BUNDLE_ID" explore
# then at the prompt:  ios sslpinning disable
```

If traffic flows only after `sslpinning disable`, pinning was enforced. If it flowed before, pinning was absent.

- **PASS:** with the proxy CA trusted, the app refuses to connect, and traffic only appears after pinning is explicitly disabled.
- **FAIL:** traffic intercepts with the proxy CA trusted and no pinning bypass required.
- **Evidence:** the proxy result before and after `sslpinning disable`.

> **References:** MASVS-NETWORK-2; MASWE-0047; MASTG-TEST-0068, MASTG-TECH-0051 (pinning bypass).

## MASVS-PLATFORM-1: The App Uses IPC Mechanisms Securely

PLATFORM-1 covers the app's edges to other apps: custom URL schemes, universal links, the share sheet, app extensions, and the pasteboard. iOS sandboxing means there are no exported components as on Android, so the surface is narrower and centers on what the app accepts from outside and what it hands out. Most PLATFORM weaknesses in MASWE are still stubs, so the checks are anchored to the finalized MASTG tests. Mapped weaknesses (placeholder): MASWE-0058 deep links, 0059 unauthenticated IPC, 0060 UIActivity, 0061 app extensions.

### Check 1: Custom URL scheme and universal link validation (MASTG-TEST-0075, 0370, 0371)

A custom scheme or universal link hands attacker-controlled data into the app. The failure is a handler that trusts the incoming URL and its parameters without validating them or checking the source.

```bash
plutil -p "$APP/Info.plist" | grep -A6 CFBundleURLSchemes
grep -nE 'application.*openURL|application.*continue.*restorationHandler|scene.*openURLContexts|URLComponents|queryItems' classes.h
```

- **PASS:** the app prefers universal links (which are bound to a verified domain), and every URL handler validates the URL, its host, and each parameter before acting.
- **FAIL:** a handler reads a parameter from the incoming URL and uses it (a redirect, a file path, a WebView load) without validation.
- **Evidence:** the declared schemes and the handler code that consumes the URL.

### Check 2: Pasteboard exposure (MASTG-TEST-0073, 0276)

`UIPasteboard.general` is shared with every app on the device and, with Universal Clipboard, can sync to the user's other devices. Sensitive data placed there without restriction leaks broadly.

```bash
grep -nE 'UIPasteboard|generalPasteboard|setItems|\.string ?=' classes.h
```

- **PASS:** sensitive values do not go to the general pasteboard, or use a named, local-only, expiring pasteboard.
- **FAIL:** a token, password, or PII value is written to `UIPasteboard.general` with no restriction.
- **Evidence:** the pasteboard write and the value it carries.

### Dynamic confirmation

Invoke the surface yourself and monitor what the app exposes.

```bash
# Open a custom scheme / universal link with a crafted parameter
# (from Safari or: on a jailbroken device, `uiopen "app://host/path?p=../../etc"`)

# Watch what the app puts on the pasteboard
objection -g "$BUNDLE_ID" explore -c 'ios pasteboard monitor'
```

- **PASS:** a crafted URL cannot reach sensitive functionality or feed unvalidated data in; nothing sensitive appears on the pasteboard.
- **FAIL:** a crafted scheme parameter is acted on, or a sensitive value shows up in the pasteboard monitor.
- **Evidence:** the URL that triggered the behavior, or the captured pasteboard value.

> **References:** MASVS-PLATFORM-1; MASWE-0058, MASWE-0059, MASWE-0060, MASWE-0061 (placeholder); MASTG-TEST-0071, MASTG-TEST-0073, MASTG-TEST-0075, MASTG-TEST-0370.

## MASVS-PLATFORM-2: The App Uses WebViews Securely

A WebView is a browser inside the app, and its security depends on its configuration and what it loads. On iOS this is `WKWebView` (the deprecated `UIWebView` is itself a finding). Mapped weaknesses (all placeholder): MASWE-0068 JavaScript bridges, 0069 local resource access, 0070/0071 untrusted content, 0072 universal XSS, 0074 web debugging; the checks come from the finalized MASTG tests.

### Check 1: JavaScript-to-native bridge (MASTG-TEST-0078, 0376)

A `WKScriptMessageHandler` exposes a native message handler to the JavaScript running in the WebView, and `evaluateJavaScript` pushes data the other way. Reachable by untrusted content, this bridges web code into the app.

```bash
grep -nE 'WKWebView|UIWebView|WKScriptMessageHandler|addScriptMessageHandler|evaluateJavaScript|WKUserContentController' classes.h
```

- **PASS:** no message handler is exposed to untrusted content; bridges are used only with content the app fully controls over HTTPS, ideally with content-world isolation.
- **FAIL:** a `WKScriptMessageHandler` is reachable by remote, cleartext, or user-influenced content, or the app uses the deprecated `UIWebView`.
- **Evidence:** the handler registration, the exposed functionality, and the URL the WebView loads.

### Check 2: WebView local file access (MASTG-TEST-0333, 0335)

`loadFileURL(_:allowingReadAccessTo:)` with an over-broad directory, or the private `allowFileAccessFromFileURLs` / `allowUniversalAccessFromFileURLs` settings, let WebView content read local files beyond what it should.

```bash
grep -nE 'loadFileURL|allowingReadAccessTo|allowFileAccessFromFileURLs|allowUniversalAccessFromFileURLs' classes.h
```

- **PASS:** file access is scoped to the specific file or directory the WebView needs; the relaxed cross-origin file settings are not enabled.
- **FAIL:** read access is granted to a broad directory (the app container or a parent), or the relaxed file-URL settings are enabled with untrusted content.
- **Evidence:** the load call and the directory it grants access to.

### Check 3: Web debugging in production (MASTG-TEST-0074 family)

On iOS 16.4 and later, `WKWebView.isInspectable = true` lets Safari Web Inspector attach to the WebView. It belongs in debug builds only.

```bash
grep -nE 'isInspectable' classes.h
```

- **PASS:** `isInspectable` is left false in release, or guarded by a debug check.
- **FAIL:** it is set true unconditionally in the production build.
- **Evidence:** the assignment and whether a build guard wraps it.

### Dynamic confirmation

Proxy the app and drive every WebView flow: note the URLs it loads and whether any arrive over HTTP or from a redirectable source. If `isInspectable` is on, attach Safari's Web Inspector and confirm.

- **PASS:** WebViews load only trusted HTTPS content; no bridge is reachable by that content; Web Inspector shows nothing in release.
- **FAIL:** a WebView loads attacker-influenceable content with a bridge or broad file access, or Web Inspector attaches in production.
- **Evidence:** the loaded URL in the proxy, and the inspector session if debugging is exposed.

> **References:** MASVS-PLATFORM-2; MASWE-0068, MASWE-0069, MASWE-0074 (placeholder); MASTG-TEST-0076, MASTG-TEST-0078, MASTG-TEST-0333, MASTG-TEST-0376.

## MASVS-PLATFORM-3: The App Uses the User Interface Securely

PLATFORM-3 covers data leaking through the UI surface: the app-switcher snapshot, the keyboard, and notifications. Only MASWE-0055 (screenshots) is finalized; the others (0053 UI leak, 0054 notifications, 0056 tapjacking) are placeholders.

### Check 1: Sensitive data in the app-switcher snapshot (MASWE-0055; MASTG-TEST-0059, 0290)

When the app backgrounds, iOS snapshots the current screen for the app switcher. Without a backgrounding blur or placeholder, a sensitive screen is captured to disk and shown in the switcher.

```bash
grep -nE 'applicationDidEnterBackground|sceneDidEnterBackground|willResignActive|snapshot|blur' classes.h
```

- **PASS:** the app hides sensitive content on backgrounding (overlays a placeholder or blurs the window in `sceneDidEnterBackground`/`applicationDidEnterBackground`).
- **FAIL:** a screen showing credentials, tokens, or PII is captured into the app-switcher snapshot with no masking.
- **Evidence:** whether a backgrounding handler masks the UI, and the snapshot content.

### Check 2: Keyboard caching of sensitive fields (MASTG-TEST-0346, 0347)

A `UITextField` without `isSecureTextEntry` lets the keyboard cache and later suggest what the user typed. Custom keyboards with full access can also exfiltrate keystrokes.

```bash
grep -nE 'isSecureTextEntry|secureTextEntry|UITextField|autocorrectionType' classes.h
```

- **PASS:** sensitive fields set `isSecureTextEntry = true` (and disable autocorrection), and the app restricts custom keyboards where warranted.
- **FAIL:** a password or sensitive field does not set `isSecureTextEntry`.
- **Evidence:** the field and its secure-entry setting.

### Dynamic confirmation

Background the app on a sensitive screen and look at the app switcher; then check the on-disk snapshot in the container.

```bash
# iOS stores app-switcher snapshots under the app's container (jailbroken device)
# .../Library/SplashBoard/Snapshots  or  /var/mobile/Containers/Data/.../Library/Caches/Snapshots
```

For the keyboard, type into a suspect field and see whether it offers autocomplete of previously entered values.

- **PASS:** the switcher shows a masked or blurred screen on sensitive views, and sensitive fields offer no suggestions.
- **FAIL:** the snapshot shows sensitive content, or the keyboard suggests a previously typed secret.
- **Evidence:** the switcher snapshot or the suggestion observed.

> **Deeper on L2:** notifications leaking sensitive content (MASWE-0054) and custom-keyboard full access (MASTG-TEST-0389, 0390) are further checks in this control; treat them as review prompts pending finalized OWASP weakness text.

> **References:** MASVS-PLATFORM-3; MASWE-0055 (screenshots, finalized); MASTG-TEST-0059, MASTG-TEST-0290, MASTG-TEST-0346, MASTG-TEST-0347.

## MASVS-CODE-1: The App Requires an Up-to-Date Platform Version

An app that runs on an old iOS version inherits that version's unpatched weaknesses. Both mapped weaknesses (MASWE-0077, MASWE-0078) are placeholders; the check is anchored to MASTG-TEST-0245.

### Check 1: Minimum deployment target (MASTG-TEST-0245)

`MinimumOSVersion` in `Info.plist` is the oldest iOS the app installs on. A low value means it runs on versions that no longer receive security fixes.

```bash
plutil -p "$APP/Info.plist" | grep -iE 'MinimumOSVersion|DTPlatformVersion'
```

- **PASS:** `MinimumOSVersion` is a currently supported iOS release.
- **FAIL:** the app supports an iOS version well behind current, exposing it to platform bugs fixed in later releases.
- **Evidence:** the `MinimumOSVersion` value.

> **References:** MASVS-CODE-1; MASWE-0077, MASWE-0078 (placeholder); MASTG-TEST-0245.

## MASVS-CODE-2: The App Has a Mechanism to Enforce Updates

If a critical vulnerability is fixed in an update, the app needs a way to push users off the vulnerable version. iOS has no platform-provided forced-update API, so this is a server-driven version gate. MASWE-0075 is a placeholder, and this is largely a design and runtime property.

### Check 1: An update-enforcement mechanism is present (MASTG-TEST-0383)

```bash
grep -nE 'minimumVersion|forceUpdate|requiredVersion|appStoreVersion|updateAvailable' classes.h
```

- **PASS:** the app checks a server-controlled minimum version and can block use of an outdated build.
- **FAIL:** there is no mechanism to force an update when a vulnerable version is in the field.
- **Evidence:** the update-check code, or its absence.

### Dynamic confirmation

Run an older build (or spoof the version the app reports) and confirm the server blocks it rather than letting it run.

- **PASS:** an outdated version is refused and the user is required to update.
- **FAIL:** an outdated build keeps working with no enforcement.
- **Evidence:** the app's behavior when running an outdated version.

> **References:** MASVS-CODE-2; MASWE-0075 (placeholder); MASTG-TEST-0080, MASTG-TEST-0383.

## MASVS-CODE-3: The App Only Uses Components Without Known Vulnerabilities

Two concerns: third-party dependencies carrying known CVEs, and the app's own binary built without the free compiler hardening. MASWE-0076 (dependencies) is finalized; MASWE-0116 (compiler features) is a placeholder anchored to MASTG-TEST-0087.

### Check 1: Dependencies with known vulnerabilities (MASWE-0076; MASTG-TEST-0273)

The developer owns every embedded framework and SDK. Enumerate what ships in the IPA, pin each to a version, and check those versions against vulnerability databases.

```bash
# Embedded frameworks and dylibs shipped in the app
ls "$APP/Frameworks/"
otool -L "$BIN"        # dynamic libraries the binary links against
```

Run an automated scan for depth: MobSF surfaces embedded components. Cross-reference identified framework versions against `osv.dev`.

- **PASS:** no embedded framework maps to a known, exploitable CVE affecting the version in use.
- **FAIL:** a shipped framework or SDK matches a known CVE relevant to how the app uses it.
- **Evidence:** the framework, its version, and the CVE it matches.

### Check 2: Compiler-provided security features (MASWE-0116; MASTG-TEST-0087)

The binary should ship with PIE (position-independent executable), stack canaries, and ARC. Their presence shows as build flags and symbols.

```bash
otool -hv "$BIN" | grep -i PIE                    # PIE flag set
nm "$BIN" | grep -E '__stack_chk_guard|__stack_chk_fail'   # stack canaries
otool -Iv "$BIN" | grep -E 'objc_autorelease|objc_release' # ARC symbols
```

- **PASS:** the main binary is PIE, links the stack-protector symbols, and shows ARC symbols; bundled libraries report `canary` and `pic` true under `rabin2 -I`.
- **FAIL:** the binary is not PIE, has no stack canaries, or an Objective-C target was built without ARC.
- **Evidence:** the missing flag or symbol from the tool output.

> **References:** MASVS-CODE-3; MASWE-0076 (dependencies, finalized), MASWE-0116 (placeholder); MASTG-TEST-0085, MASTG-TEST-0087, MASTG-TEST-0228, MASTG-TEST-0229, MASTG-TEST-0230, MASTG-TEST-0273.

## MASVS-CODE-4: The App Validates and Sanitizes All Untrusted Inputs

The trust-boundary control. Data arriving from the network, a backup, IPC, local storage, or the UI is all attacker-influenceable and must be validated before use. The MASWE family 0079-0084 states that principle per source; the concrete sinks below (placeholder weaknesses, finalized MASTG tests) are where it goes wrong: SQL injection (0086) and insecure deserialization (0088).

### Check 1: SQL injection (MASWE-0086; MASTG-TEST-0025)

Raw SQL built by concatenating untrusted input is injectable. On iOS this is usually the SQLite C API or a wrapper like FMDB.

```bash
grep -nE 'sqlite3_exec|sqlite3_prepare|executeQuery|executeUpdate|stringWithFormat.*SELECT' classes.h
```

- **PASS:** queries use bound parameters (`sqlite3_bind_*`, FMDB `?` placeholders); no untrusted value is concatenated into SQL.
- **FAIL:** a query string is built with `stringWithFormat` or concatenation from untrusted input.
- **Evidence:** the query construction and the untrusted input that feeds it.

### Check 2: Insecure deserialization (MASWE-0088; MASTG-TEST-0386)

Unarchiving attacker-controlled data without secure coding can instantiate unexpected classes. The insecure pattern is `NSKeyedUnarchiver.unarchiveObject(with:)` or `NSCoding` without `requiresSecureCoding`.

```bash
grep -nE 'NSKeyedUnarchiver|unarchiveObjectWithData|unarchivedObject|requiresSecureCoding|NSCoding' classes.h
```

- **PASS:** unarchiving uses the secure-coding API (`unarchivedObject(ofClass:from:)` with `requiresSecureCoding`), or untrusted data is parsed with a validating decoder (`Codable`).
- **FAIL:** the app unarchives data from a file, the network, or IPC without secure coding.
- **Evidence:** the unarchive call and where its input comes from.

### Dynamic confirmation

Drive malicious input through the entry points you mapped in PLATFORM-1: a crafted custom-scheme parameter, a pasteboard value, or a tampered stored file. For SQLi, feed a suspect field or URL parameter an injection payload and watch the query behavior; for deserialization, replace a stored archive with a crafted one.

- **PASS:** crafted input is rejected or safely handled at every entry point.
- **FAIL:** an injection payload changes query behavior, or a crafted archive alters app state.
- **Evidence:** the input sent and the app's response.

> **References:** MASVS-CODE-4; MASWE-0086, MASWE-0088 (placeholder); MASTG-TEST-0025, MASTG-TEST-0079, MASTG-TEST-0386.

## MASVS-RESILIENCE: Reading This Group Correctly

RESILIENCE is the **R profile**, not L1 or L2. It applies only to apps whose threat model includes a hostile user on their own device (banking, payments, DRM, high-value accounts). If the engagement is scoped to L1 or L2, this whole group is out of scope; confirm the profile before spending time here.

The finding logic is also inverted. For every group above, the finding was a weakness present. Here the concern is a **defense absent**. And OWASP is explicit, as it is with pinning, that every client-side resilience control is ultimately bypassable by a determined attacker with the device. So bypassing a control at runtime is expected and is not itself the finding. The finding is a control being **absent** or **trivially defeated** (a single boolean, no obfuscation, broken in seconds). You are judging whether it raises the attacker's cost meaningfully. The one exception is the debuggable entitlement under RESILIENCE-4, which is a clear misconfiguration with a hard pass or fail.

## MASVS-RESILIENCE-1: The App Validates the Integrity of the Platform

The app should detect a jailbroken device, the simulator, or a virtualized environment, and respond. Weaknesses are all placeholder and R-profile: MASWE-0097 jailbreak detection, 0098 virtualization, 0099 emulator, 0100 device attestation.

### Check 1: Jailbreak and simulator detection (MASTG-TEST-0088, 0092)

Look for detection logic: checks for jailbreak file paths (`/Applications/Cydia.app`, `/bin/bash`, `/usr/sbin/sshd`), a `fork` that should fail in the sandbox, `canOpenURL:` on `cydia://`, or `MobileSubstrate` presence.

```bash
grep -nE 'Cydia|/bin/bash|/usr/sbin/sshd|/etc/apt|jailbr|canOpenURL|MobileSubstrate|fork\(' classes.h
strings -a "$BIN" | grep -iE 'cydia|/bin/bash|jailbreak|MobileSubstrate|/private/'
```

- **PASS:** the app detects jailbreak and simulator conditions through several independent checks and reacts, and stronger builds add DeviceCheck or App Attest.
- **FAIL:** no detection at all, or a single check that a bypass flips in one place.
- **Evidence:** the detection code and how the app responds when it triggers.

### Check 2: Device secure-lock verification (MASWE-0008; MASTG-TEST-0248)

An app holding sensitive data should confirm the device has a passcode set, which on iOS is tightly coupled with Data Protection: without a passcode, the file encryption protecting the app's data is not in force. Before authenticating, the app should call `LAContext.canEvaluatePolicy`, and Keychain items should use the `kSecAttrAccessibleWhenPasscodeSet` (or `...ThisDeviceOnly`) protection class so they only exist when a passcode is set.

```bash
grep -nE 'canEvaluatePolicy|LAPolicyDeviceOwnerAuthentication|kSecAttrAccessibleWhenPasscodeSet' classes.h
```

- **PASS:** the app confirms a passcode is set (`canEvaluatePolicy`) and ties sensitive Keychain items to `kSecAttrAccessibleWhenPasscodeSet`, restricting sensitive functionality when none is set.
- **FAIL:** the app never verifies a passcode and exposes sensitive data on a device with none.
- **Evidence:** the secure-lock check or the Keychain protection class, or their absence.

### Dynamic confirmation

Run the app on a jailbroken device and watch whether it reacts. Then attempt the standard bypass and judge how much effort it takes. Separately, remove the device passcode and confirm whether the app notices the insecure lock state.

```bash
objection -g "$BUNDLE_ID" explore
# then:  ios jailbreak disable
```

- **PASS:** the app reacts to the jailbroken environment, and defeating it takes real effort, not a one-line hook.
- **FAIL:** the app runs unmodified on a jailbroken device with no reaction, or `ios jailbreak disable` defeats it instantly.
- **Evidence:** the app's behavior before and after the bypass.

> **References:** MASVS-RESILIENCE-1; MASWE-0008 (secure lock), MASWE-0097, MASWE-0098, MASWE-0099, MASWE-0100 (placeholder, R profile); MASTG-TEST-0088, MASTG-TEST-0092, MASTG-TEST-0246, MASTG-TEST-0248.

## MASVS-RESILIENCE-2: The App Implements Anti-Tampering Mechanisms

The app should detect that it has been repackaged or re-signed, by verifying its own code signature and provisioning, and confirm it was installed from the App Store. Weaknesses are placeholder and R-profile: MASWE-0104 app integrity, 0105 resource integrity, 0106 store verification, 0107 runtime code integrity.

### Check 1: Signature and store verification (MASTG-TEST-0081, 0090)

Look for the app checking its own code signature (`SecStaticCode`, `SecCode`), reading `embedded.mobileprovision`, or validating the App Store receipt.

```bash
grep -nE 'SecStaticCode|SecCode|embedded.mobileprovision|appStoreReceiptURL|SecCodeCheckValidity' classes.h
codesign -dv --verbose=4 "$APP" 2>&1
```

- **PASS:** the app verifies its signature and provenance at runtime and refuses to run when re-signed, and it validates the store receipt.
- **FAIL:** no integrity check, so a re-signed build runs normally.
- **Evidence:** the verification code, or its absence.

### Dynamic confirmation

Re-sign the app with your own certificate and install it on the device. If it still runs, there is no effective tamper check.

```bash
# Re-sign the IPA with your own signing identity, then install
codesign -f -s "Your Identity" "$APP"
# install the resigned build (ios-deploy / Sideloadly) and launch
```

- **PASS:** the re-signed build detects the mismatch and refuses to run or degrades.
- **FAIL:** the re-signed build runs as normal.
- **Evidence:** the re-signed build and its behavior on launch.

> **References:** MASVS-RESILIENCE-2; MASWE-0104, MASWE-0105, MASWE-0106, MASWE-0107 (placeholder, R profile); MASTG-TEST-0081, MASTG-TEST-0090, MASTG-TEST-0220.

## MASVS-RESILIENCE-3: The App Implements Anti-Static-Analysis Mechanisms

The app should resist static reverse engineering: obfuscated security-relevant code and stripped symbols. Weaknesses are placeholder and R-profile: MASWE-0089 code obfuscation, 0090 resource obfuscation, 0093 debug symbols not removed, 0094 non-production resources.

### Check 1: Obfuscation and symbols (MASTG-TEST-0093, 0391)

Objective-C exposes method names to `class-dump` by design, so readable, meaningful selectors in the security code mean no obfuscation. Also check whether the binary is stripped of symbols.

```bash
head -60 classes.h            # meaningful ObjC selectors vs mangled/absent
nm "$BIN" | head              # symbols present vs stripped
strings -a "$BIN" | grep -iE 'password|secret|jailbreak|debug' | head
```

- **PASS:** security-relevant code is obfuscated or, for Swift, symbol-stripped, so reading it takes significant effort.
- **FAIL:** the security-relevant code and symbols are fully readable with original names.
- **Evidence:** a sample of the `class-dump` output or symbol listing.

> **Deeper on R:** the same control also covers anti-deobfuscation techniques not implemented (MASWE-0091) and static-analysis tools not prevented (MASWE-0092), both placeholder. These extend Check 1: beyond whether code is obfuscated, judge whether the obfuscation actively resists automated deobfuscation and tooling.

> **References:** MASVS-RESILIENCE-3; MASWE-0089, MASWE-0090, MASWE-0091, MASWE-0092, MASWE-0093, MASWE-0094 (placeholder, R profile); MASTG-TEST-0083, MASTG-TEST-0093, MASTG-TEST-0219, MASTG-TEST-0391.

## MASVS-RESILIENCE-4: The App Implements Anti-Dynamic-Analysis Mechanisms

The app should resist runtime analysis: the debuggable entitlement off, and detection of a debugger or a hooking framework. MASWE-0067 (debuggable flag) is the one finalized weakness in this group; 0101 debugger detection, 0102 dynamic-tool detection, and 0103 RASP are placeholder.

### Check 1: Debuggable entitlement disabled (MASWE-0067; MASTG-TEST-0261)

This is the hard pass or fail. A production build with the `get-task-allow` entitlement lets a debugger attach to the running app.

```bash
codesign -d --entitlements :- "$APP" 2>/dev/null | grep -i 'get-task-allow'
```

- **PASS:** `get-task-allow` is absent or `false` in the release build.
- **FAIL:** `get-task-allow` is `true` in production.
- **Evidence:** the entitlements listing.

### Check 2: Debugger and hooking detection (MASTG-TEST-0089, 0354)

Look for runtime checks: `ptrace(PT_DENY_ATTACH)`, a `sysctl` query for `P_TRACED`, `getppid`, or Frida tells (port 27042, injected dylibs, `MSHookFunction`).

```bash
grep -nE 'ptrace|PT_DENY_ATTACH|sysctl|P_TRACED|getppid|frida|27042|MSHookFunction|dyld_image' classes.h
strings -a "$BIN" | grep -iE 'frida|cycript|PT_DENY_ATTACH'
```

- **PASS:** the app detects a debugger and a hooking framework through several independent checks and reacts.
- **FAIL:** no detection, or a single check trivially bypassed.
- **Evidence:** the detection code and the app's response.

### Dynamic confirmation

Attach a debugger and run a Frida hook, and see whether the app notices.

```bash
frida -U -f "$BUNDLE_ID"     # does the app crash, exit, or ignore the injection?
# and: lldb attach to the running process
```

- **PASS:** the app detects the debugger or Frida and reacts, and evading detection takes real effort.
- **FAIL:** Frida attaches with no reaction, or a one-line hook silences the check.
- **Evidence:** the app's behavior under a debugger and under Frida.

> **References:** MASVS-RESILIENCE-4; MASWE-0067 (debuggable flag, finalized), MASWE-0101, MASWE-0102, MASWE-0103 (placeholder, R profile); MASTG-TEST-0082, MASTG-TEST-0089, MASTG-TEST-0261, MASTG-TEST-0354, MASTG-TEST-0402.

## MASVS-PRIVACY: Reading This Group Correctly

PRIVACY is the **P profile**. Unlike the resilience group, every weakness here has finalized OWASP text, but part of the group is documentation and UX review rather than binary analysis: the adequacy of a privacy policy or a consent flow is not something you extract from an IPA. The checks below cover the technically-testable core (permissions and purpose strings, data on the wire, tracking identifiers) and flag where the answer depends on comparing the app's behavior against its declarations.

The strongest instrument here is the same intercepting proxy from the NETWORK group: privacy is largely about what data leaves the device and who receives it, which you see on the wire.

## MASVS-PRIVACY-1: The App Minimizes Access to Sensitive Data and Resources

The app should request only the resources its features genuinely need, with an accurate purpose string for each, and send sensitive data only where required. Two finalized weaknesses map here: MASWE-0117 inadequate permission management, and MASWE-0108 sensitive data in network traffic.

### Check 1: Permissions and purpose strings (MASWE-0117; MASTG-TEST-0360, 0362)

On iOS, access to protected resources is gated by a purpose string in `Info.plist` (`NSCameraUsageDescription`, `NSLocationWhenInUseUsageDescription`, and so on) and by entitlements. Read each one and justify it against an actual feature; an inaccurate or boilerplate purpose string is itself a finding.

```bash
plutil -p "$APP/Info.plist" | grep -iE 'UsageDescription'
codesign -d --entitlements :- "$APP" 2>/dev/null
```

- **PASS:** every purpose string and entitlement maps to a feature the app provides, with an accurate, specific explanation.
- **FAIL:** the app declares access to a resource it does not use, or a purpose string is missing, boilerplate, or misleading.
- **Evidence:** the purpose string or entitlement and the feature it is (or is not) justified by.

### Check 2: Sensitive data in network traffic (MASWE-0108; MASTG-TEST-0206)

This is a dynamic check. Proxy the app and drive its flows, then read the requests for PII the app sends: names, email, phone, precise location, contacts, device identifiers, especially to third-party hosts.

- **PASS:** sensitive data is sent only to first-party endpoints that need it, over TLS, and no more than the feature requires.
- **FAIL:** PII is sent to third-party analytics or ad hosts, or sensitive data is transmitted that the feature does not need.
- **Evidence:** the proxied request, the data it carries, and the destination host.

### Check 3: Sensitive data removed after use (MASWE-0118)

Data minimization includes cleanup at the end of a session: WebView cookies and storage, cached URL responses, and temporary files holding sensitive data should be cleared, not left on disk after they are no longer needed.

```bash
grep -nE 'WKWebsiteDataStore|removeData|nonPersistent|removeCookies|removeAllCachedResponses|removePersistentDomain' classes.h
```

- **PASS:** the app clears WebView state (`WKWebsiteDataStore.removeData` or a non-persistent store), URL caches, and temporary sensitive files at logout or session end.
- **FAIL:** sensitive session data (WebView cookies, cached responses, temp files) persists in the container after it is no longer needed.
- **Evidence:** the sensitive data left behind after logout, from the container pull in STORAGE-1.

> **References:** MASVS-PRIVACY-1; MASWE-0108, MASWE-0117, MASWE-0118; MASTG-TEST-0206, MASTG-TEST-0360, MASTG-TEST-0362.

## MASVS-PRIVACY-2: The App Prevents Identification of the User

The app should avoid persistent identifiers and unconsented tracking that let a user be recognized over time and across apps. Two finalized weaknesses: MASWE-0110 unique identifiers for tracking, and MASWE-0109 lack of anonymization.

### Check 1: Tracking identifiers and consent (MASWE-0110; MASTG-TEST-0281)

The advertising identifier (IDFA) via `ASIdentifierManager` requires explicit user consent through App Tracking Transparency; using it without an `ATTrackingManager.requestTrackingAuthorization` prompt is a violation. The vendor identifier (IDFV) and any hardware identifiers are the other things to look for.

```bash
grep -nE 'ASIdentifierManager|advertisingIdentifier|identifierForVendor|ATTrackingManager|requestTrackingAuthorization' classes.h
ls "$APP/Frameworks/" | grep -iE 'facebook|appsflyer|adjust|amplitude|firebase|flurry'
```

- **PASS:** the IDFA is accessed only after ATT consent, the IDFV and identifiers are not linked across services, and no hardware identifier is used for tracking.
- **FAIL:** the app reads the IDFA without an ATT prompt, or uses persistent identifiers to track the user.
- **Evidence:** the identifier read, whether an ATT prompt precedes it, and where it is sent.

### Dynamic confirmation

With the proxy running, watch for calls to known tracker domains and for identifiers on the wire. Compare the destination hosts against a public tracker list (the Exodus or DuckDuckGo tracker databases).

- **PASS:** no unconsented identifier reaches a tracking host.
- **FAIL:** an advertising or device identifier is sent to a known tracker domain without consent.
- **Evidence:** the request to the tracker host and the identifier it carries.

> **References:** MASVS-PRIVACY-2; MASWE-0109, MASWE-0110; MASTG-TEST-0281.

## MASVS-PRIVACY-3: The App is Transparent About Data Collection and Usage

The app's stated data practices should match what it actually does. Two finalized weaknesses: MASWE-0111 inadequate privacy policy, and MASWE-0112 inadequate data collection declarations. On iOS the app ships a privacy manifest (`PrivacyInfo.xcprivacy`) declaring collected data types and required-reason API use, which you compare against observed behavior.

### Check 1: Declarations match observed behavior (MASWE-0112)

Take the resources, identifiers, and hosts you found in PRIVACY-1 and PRIVACY-2, and compare them against the privacy manifest and the App Store nutrition labels. The finding is a gap: data collected or shared that the app does not declare.

```bash
plutil -p "$APP/PrivacyInfo.xcprivacy" 2>/dev/null
```

- **PASS:** the declared data collection and sharing covers everything the app actually accesses and transmits.
- **FAIL:** the app collects or shares data (a tracking SDK, a protected resource) that its privacy manifest or nutrition labels omit.
- **Evidence:** the observed collection and the declaration that fails to mention it.

> **References:** MASVS-PRIVACY-3; MASWE-0111, MASWE-0112; MASTG-TEST-0318.

## MASVS-PRIVACY-4: The App Provides User Control Over Their Data

The user should be able to consent before collection and to control their data afterward. The finalized weaknesses (MASWE-0113 data management, MASWE-0114 data visibility, MASWE-0115 consent) are largely UX and backend properties, so this control is mostly review rather than binary analysis.

### Review prompts

- **Consent before collection:** is the ATT prompt (and any GDPR consent) shown before any tracking or non-essential collection begins? Confirm dynamically that no tracker call fires before consent.
- **Opt-out and control:** can the user decline tracking and still use the app, and reset or delete their data?
- **Granularity:** is consent specific per purpose, not a single all-or-nothing prompt?

```bash
# Static lead: where the app gates collection on consent
grep -nE 'ATTrackingManager|requestTrackingAuthorization|consent|gdpr|optOut|trackingEnabled' classes.h
```

- **PASS:** consent is obtained up front and per purpose, and users can opt out and manage their data.
- **FAIL:** collection or tracking starts before consent, or there is no way to opt out.
- **Evidence:** the consent flow behavior, and any tracker call observed before consent in the proxy.

> **References:** MASVS-PRIVACY-4; MASWE-0113, MASWE-0114, MASWE-0115.
