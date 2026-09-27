---
author: Kayra
pubDatetime: 2026-09-27T00:00:00+03:00
title: "Local Storage on Android"
slug: "android-local-storage"
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "Testing Android on-disk storage beyond SharedPreferences: internal files, cache, SQLite and Room databases, and external storage, plus reading the sandbox back with run-as and adb."
---

Beyond SharedPreferences, an app keeps data in files, databases, and caches. Where a value is written decides who can read it: internal storage is private to the app by default, external storage is shared space, and neither is encrypted just because of where it sits. This page covers the storage locations and how to read them back. The key-value store gets its own page in [SharedPreferences on Android](/collections/mobile/android-shared-preferences), and the sandbox layout and `run-as` mechanics are in [Android ADB](/collections/mobile/android-adb).

## The Storage Surface

| Where | Path | API |
|---|---|---|
| Internal files | `/data/data/<pkg>/files/` | `getFilesDir`, `openFileOutput` |
| Databases | `/data/data/<pkg>/databases/` | `SQLiteDatabase`, Room |
| Cache | `/data/data/<pkg>/cache/` | `getCacheDir` |
| External app-specific | `/sdcard/Android/data/<pkg>/` | `getExternalFilesDir` |
| External public | `/sdcard/Download`, MediaStore | `getExternalStoragePublicDirectory` |

Find every write call site first, then judge the location each value is written to:

```bash
grep -rnE 'openFileOutput|getFilesDir|getCacheDir|getExternalFilesDir|getExternalStoragePublicDirectory|SQLiteDatabase|Room\.databaseBuilder|MediaStore' jadx_out/sources/
```

Then check whether the writes are encrypted with a keystore-backed key:

```bash
grep -rnE 'EncryptedFile|MasterKey|AndroidKeyStore|net\.zetetic' jadx_out/sources/
```

`EncryptedFile` (Jetpack Security) and SQLCipher are the encrypted shapes; `net.zetetic` is the SQLCipher package.

## Internal Files

Internal files are private to the app by default, but private is not encrypted. A token written through `openFileOutput` is readable on a rooted device, through a device backup, or from a debug build. Two extra weaknesses expose the data beyond the encryption question:

- **World-accessible modes**: the deprecated `MODE_WORLD_READABLE` and `MODE_WORLD_WRITEABLE`, or `setReadable(true)` and `setWritable(true)`, let other apps read or write the file. They were deprecated in Android 4.2 and throw from Android 7.0 onward.
- **A provider over the data**: an exported `ContentProvider`, or a `FileProvider` whose declared paths cover the whole `files/` directory, lets other apps reach the app's files through a `content://` URI. Testing the provider as a component is in [Exported Components and the IPC Attack Surface](/collections/mobile/android-exported-components).

## Databases

SQLite and Room databases are plaintext files in `databases/`. Tokens, PII, or chat history in a column are readable with the `sqlite3` client once the file is out of the sandbox. Room does not add encryption; a database written through `Room.databaseBuilder` without SQLCipher stores the same cleartext.

```bash
grep -rnE 'SQLiteDatabase|Room\.databaseBuilder|getWritableDatabase' jadx_out/sources/
```

### Injection in App Databases

The query builders are injection sinks on top of the storage. A handler that concatenates user input into `rawQuery` or `execSQL` lets a value break out of the string, and the query runs against the app's own data. The classic proof is `' OR 1=1 --` against a `WHERE user = '<input>'` query, which returns every row instead of one:

```bash
grep -rnE 'rawQuery|execSQL|\.query\(' jadx_out/sources/
```

Read the hits that build a query string with `+` and pass user input into it.

- **Pass**: queries pass user input through `selectionArgs` or a parameterized API such as Room or SQLCipher.
- **Fail**: a query concatenates user input into SQL, and an injected value returns rows beyond the intended one.
- **Evidence**: the concatenated query call and the injected payload result.

## Cache

Cache files hold copies of whatever the app fetched, and session data or tokens can be written there through `getCacheDir`. Cache is private but not encrypted, and the system can clear it, so an app should not rely on it for anything that must survive. The check is the same: a sensitive value in a cache file is a finding.

## External Storage

External storage is shared space, and the reading rules differ by Android version:

- On Android 10 and earlier, any app holding the storage permission can read anything there with no user interaction.
- On Android 11 and later, scoped storage stops other apps from another app's app-specific directory (`/sdcard/Android/data/<pkg>/`), but public directories such as Download remain reachable by any app with the permission.

In both cases the data is not encrypted, and data in a public directory survives the app's uninstall. A token or PII written to external storage in cleartext is the finding, and it is MASTG-TEST-0200. A location the user picks explicitly through the system document picker counts as user interaction and is not a weakness.

## Reading the Sandbox Back

The on-disk files are the authoritative answer, so pull them after exercising the flows that store something sensitive. On a rooted device or a debuggable build, the whole private sandbox comes out at once:

```bash
# The whole private sandbox (root or debuggable build)
adb shell run-as com.example.app tar c . > sandbox.tar
# or, rooted: adb pull /data/data/com.example.app
```

Databases are easiest to read after pulling the file to the host, because the device image often has no `sqlite3`:

```bash
adb exec-out run-as com.example.app cat databases/app.db > app.db
sqlite3 app.db '.dump'
```

External storage is a plain listing:

```bash
adb shell ls -R /sdcard/Android/data/com.example.app
adb shell ls -R /sdcard/Download
```

Then grep the extracted tree for known secrets:

```bash
grep -rniE 'token|password|Bearer|<known-secret-value>' sandbox_extracted/
```

- **Pass**: sensitive values reach only encrypted stores (`EncryptedFile`, SQLCipher, or another keystore-backed wrapper); internal files use private modes; no exported provider or `FileProvider` points at the data directory; nothing sensitive sits on external storage.
- **Fail**: a token, credential, or PII value is readable in a file, a database column, a cache file, or external storage.
- **Evidence**: the write call site, the file path, and the value read back from disk.

These checks fall under MASVS-STORAGE-1 and MASVS-STORAGE-2, the controls for data the app stores and data that leaks from it; the MASVS system and the testing profiles that set the bar are in [The OWASP MAS Project](/collections/mobile/mas-project).