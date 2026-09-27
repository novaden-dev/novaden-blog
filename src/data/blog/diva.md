---
author: Kayra
pubDatetime: 2026-09-27T00:00:00+03:00
title: "DIVA Lab Writeups"
slug: "diva"
category: notes
format: writeup
handbook: mobile
tags: ["android"]
draft: false
featured: false
description: "Writeups for the DIVA (Damn Insecure and Vulnerable App) Android labs: each solved lab gets a section with the task, the vulnerable code, the exploit, and the finding, covering Insecure Logging, the hardcoded vendor key, the third-party credentials stored plaintext in SharedPreferences, a SQLite database, a temp file, and external storage, a SQL injection, and a WebView loading attacker content with JavaScript enabled."
---

DIVA (Damn Insecure and Vulnerable App) is Payatu's deliberately insecure Android app, built for practicing Android weaknesses. It ships as a beta APK, installs cleanly on an API 33 emulator, and its thirteen labs each exercise one weakness, which makes it a fast drill for the checks in this handbook. This page collects the writeups, one section per solved lab, as they are worked.

## The Lab List

| # | Lab | Status |
|---|---|---|
| 1 | Insecure Logging | Solved |
| 2 | Hardcoding Issues, Part 1 | Solved |
| 3 | Insecure Data Storage, Part 1 | Solved |
| 4 | Insecure Data Storage, Part 2 | Solved |
| 5 | Insecure Data Storage, Part 3 | Solved |
| 6 | Insecure Data Storage, Part 4 | Solved |
| 7 | Input Validation Issues, Part 1 | Solved |
| 8 | Input Validation Issues, Part 2 | Solved |
| 9 | Access Control Issues, Part 1 | Open |
| 10 | Access Control Issues, Part 2 | Open |
| 11 | Access Control Issues, Part 3 | Open |
| 12 | Hardcoding Issues, Part 2 | Open |
| 13 | Input Validation Issues, Part 3 | Open |

## Lab 1: Insecure Logging

The Insecure Logging screen takes a credit card number and a checkout button, shows an error toast, and writes the card number to the system log in the clear.

The Insecure Logging screen has one text field and a checkout button. Entering a card number and tapping checkout shows the toast "An error occured. Please try again later". The card number never appears on screen and the transaction never succeeds, but the number is written to logcat under the tag `diva-log`.

`LogActivity` reads the card field and passes it to `processCC`, which always throws. The catch block logs the card number:

```java
public void checkout(View view) {
    EditText cctxt = (EditText) findViewById(R.id.ccText);
    try {
        processCC(cctxt.getText().toString());
    } catch (RuntimeException e) {
        Log.e("diva-log", "Error while processing transaction with credit card: " + cctxt.getText().toString());
        Toast.makeText(this, "An error occured. Please try again later", 0).show();
    }
}

private void processCC(String ccstr) {
    RuntimeException e = new RuntimeException();
    throw e;
}
```

`processCC` throws unconditionally, so the checkout can never succeed and the error path runs every time. That error path interpolates the card number into a `Log.e` call, so the value reaches the system log, which any process with adb access can read.

![LogActivity source logging the credit card number to diva-log](/images/diva/lab1-log-source.png)

Clear the log buffer, then watch the tag while using the app:

```bash
adb logcat -c
adb logcat | grep diva-log
```

Enter a card number, for example `211133222222`, and tap checkout. The line that appears:

```text
09-27 22:21:10.161  4358  4358 E diva-log: Error while processing transaction with credit card: 211133222222
```

![logcat showing the diva-log line with the credit card in the clear](/images/diva/lab1-logcat.png)

The card number is in the log in the clear. That is the whole finding: a sensitive value written to a log call on a code path that runs in the shipping app. The category is MASWE-0001, sensitive data written to logs, checked by MASTG-TEST-0203, runtime use of logging APIs. The pattern generalizes to every logging bug: any `catch` block, request/response logger, or exception printer that interpolates a variable into a `Log` call is a candidate, and the error and authentication paths come first.

```bash
grep -rnE 'Log\.(v|d|i|w|e)|System\.out\.print|printStackTrace' jadx_out/sources/
```

- **Pass**: no sensitive value reaches a log call, or logging is stripped in the release build.
- **Fail**: a token, credential, card, or PII value is passed to a log call.
- **Evidence**: the log call site and the value it prints, plus the logcat line that captured it.

## Lab 2: Hardcoding Issues, Part 1

The vendor key screen has a text field and an access button, and nothing else. The instruction reads: find out what is hardcoded and where, then enter the vendor key to access.

![The vendor key screen asking for the hardcoded key](/images/diva/lab2-vendor-screen.png)

`HardcodeActivity.access` compares the field directly against a literal:

```java
public void access(View view) {
    EditText hckey = (EditText) findViewById(R.id.hcKey);
    if (hckey.getText().toString().equals("vendorsecretkey123")) {
        Toast.makeText(this, "Access granted! See you on the other side :)", 0).show();
    } else {
        Toast.makeText(this, "Access denied! See you in hell :D", 0).show();
    }
}
```

![HardcodeActivity comparing the input against the hardcoded vendor key](/images/diva/lab2-vendor-source.png)

The gate is a string constant compiled into the app. Finding it is a static read: decompile with jadx and read the class, or pull the string out of the DEX directly, because an APK is a zip:

```bash
unzip -o app.apk classes.dex
strings classes.dex | grep -i secret
```

`vendorsecretkey123` shows up without any Android tooling. That is the point of the lab: a secret shipped inside the app is extractable by anyone with the APK, so it cannot gate anything.

Type `vendorsecretkey123` and tap access. The toast reads "Access granted! See you on the other side :)".

![The access granted toast after entering the vendor key](/images/diva/lab2-vendor-success.png)

- **Pass**: secrets are not shipped in code; credentials come from configuration or are fetched from a server.
- **Fail**: a gate compares user input to a literal credential in the app.
- **Evidence**: the class and line holding the hardcoded string, plus the `strings` hit that finds it without decompiling.

## Lab 3: Insecure Data Storage, Part 1

The 3rd party credentials screen has username and password fields and a Save button. `saveCredentials` writes both to the app's default SharedPreferences file, which is plaintext XML in the sandbox. The full technique for this store is in [SharedPreferences on Android](/collections/mobile/android-shared-preferences).

![The 3rd party credentials screen with username and password fields](/images/diva/lab3-ids1-screen.png)

The write:

```java
public void saveCredentials(View view) {
    SharedPreferences spref = PreferenceManager.getDefaultSharedPreferences(this);
    SharedPreferences.Editor spedit = spref.edit();
    EditText usr = (EditText) findViewById(R.id.ids1Usr);
    EditText pwd = (EditText) findViewById(R.id.ids1Pwd);
    spedit.putString("user", usr.getText().toString());
    spedit.putString("password", pwd.getText().toString());
    spedit.commit();
    Toast.makeText(this, "3rd party credentials saved successfully!", 0).show();
}
```

![saveCredentials writing the username and password to the default preferences file](/images/diva/lab3-ids1-source.png)

Two details decide the readback. The file is created only when the Save button runs, so typing alone writes nothing. And the store is the default preferences file, named `<package>_preferences.xml`, here `jakhar.aseem.diva_preferences.xml`.

Read it back with `run-as`, which works because the app is debuggable. List the directory first, then read the file by name, because a `*` is expanded by the device shell before `run-as` changes into the sandbox:

```bash
adb shell run-as jakhar.aseem.diva ls shared_prefs/
adb shell run-as jakhar.aseem.diva cat shared_prefs/jakhar.aseem.diva_preferences.xml
# or expand the glob after the change of directory:
adb shell run-as jakhar.aseem.diva sh -c 'cat shared_prefs/*.xml'
```

The file holds the credentials in the clear:

```xml
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="user">the entered username</string>
    <string name="password">the entered password</string>
</map>
```

![run-as readback of the preferences XML holding the credentials in the clear](/images/diva/lab3-ids1-readback.png)

This is MASTG-TEST-0287, runtime storage of unencrypted data via the SharedPreferences API: the values are stored in a plaintext XML file rather than in `EncryptedSharedPreferences` with a keystore-backed key.

- **Pass**: credentials reach only `EncryptedSharedPreferences` or another keystore-backed store.
- **Fail**: the username and password are readable as plaintext in a SharedPreferences XML file.
- **Evidence**: the file path and the plaintext values, tied to the save flow that wrote them.

## Lab 4: Insecure Data Storage, Part 2

The screen asks for the same 3rd party credentials, but the write path is a SQLite database instead of preferences. `onCreate` opens a database named `ids2` and creates a `myuser(user, password)` table, and the Save button inserts into it. The database file is created when the activity opens, so it exists before any save.

![The credentials screen for the SQLite lab](/images/diva/lab4-ids2-screen.png)

The setup and the write:

```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    try {
        this.mDB = openOrCreateDatabase("ids2", 0, null);
        this.mDB.execSQL("CREATE TABLE IF NOT EXISTS myuser(user VARCHAR, password VARCHAR);");
    } catch (Exception e) {
        Log.d("Diva", "Error occurred while creating database: " + e.getMessage());
    }
    setContentView(R.layout.activity_insecure_data_storage2);
}

public void saveCredentials(View view) {
    EditText usr = (EditText) findViewById(R.id.ids2Usr);
    EditText pwd = (EditText) findViewById(R.id.ids2Pwd);
    try {
        this.mDB.execSQL("INSERT INTO myuser VALUES ('" + usr.getText().toString() + "', '" + pwd.getText().toString() + "');");
        this.mDB.close();
    } catch (Exception e) {
        Log.d("Diva", "Error occurred while inserting into database: " + e.getMessage());
    }
    Toast.makeText(this, "3rd party credentials saved successfully!", 0).show();
}
```

![The saveCredentials and onCreate source for the SQLite lab](/images/diva/lab4-ids2-source.png)

The database lives at `databases/ids2`. `adb shell` rewrites line endings in the stream, so pull it with `exec-out`, which passes bytes through unchanged, then open it on the host:

```bash
adb exec-out run-as jakhar.aseem.diva cat databases/ids2 > ids2.db
sqlite3 ids2.db
sqlite> .tables
android_metadata  myuser
sqlite> SELECT * FROM myuser;
test|tototo
```

![sqlite3 showing the myuser table with the credentials in plaintext](/images/diva/lab4-ids2-readback.png)

The credentials sit in a plaintext table. This is the same failure as Lab 3 with a different store, and it is MASTG-TEST-0207, runtime storage of unencrypted data in the app sandbox.

The concatenated INSERT is a second finding on its own: a value containing a quote breaks out of the string literal, so a password of `b'),('c','d` turns one INSERT into two rows. The credentials are stored unencrypted and the write path is injectable, so both the store and the sink fail.

- **Pass**: database writes use parameterized queries, and sensitive columns are encrypted or the database itself is encrypted with SQLCipher.
- **Fail**: credentials are readable in plaintext columns, and the write path concatenates user input into SQL.
- **Evidence**: the pulled database and the rows read back, plus the concatenated `execSQL` call.

## Lab 5: Insecure Data Storage, Part 3

The same credentials screen, but this time `saveCredentials` writes to a temporary file in the app's data directory instead of preferences or a database. The file is created with `File.createTempFile`, using the app's data directory as the location:

```java
public void saveCredentials(View view) {
    EditText usr = (EditText) findViewById(R.id.ids3Usr);
    EditText pwd = (EditText) findViewById(R.id.ids3Pwd);
    File ddir = new File(getApplicationInfo().dataDir);
    try {
        File uinfo = File.createTempFile("uinfo", "tmp", ddir);
        uinfo.setReadable(true);
        uinfo.setWritable(true);
        FileWriter fw = new FileWriter(uinfo);
        fw.write(usr.getText().toString() + ":" + pwd.getText().toString() + "\n");
        fw.close();
        Toast.makeText(this, "3rd party credentials saved successfully!", 0).show();
    } catch (Exception e) {
        Toast.makeText(this, "File error occurred", 0).show();
        Log.d("Diva", "File error: " + e.getMessage());
    }
}
```

![The credentials screen for the temp file lab](/images/diva/lab5-screen.png)

![The saveCredentials source writing to a temp file](/images/diva/lab5-source.png)

`createTempFile("uinfo", "tmp", ddir)` creates a file named `uinfo<random>tmp` in `getApplicationInfo().dataDir`, which is `/data/data/jakhar.aseem.diva/`. The suffix is `tmp`, not `.tmp`, and each save creates a new file. The credentials are written as `username:password` plus a newline.

List the data directory and read the file by name:

```bash
adb shell run-as jakhar.aseem.diva ls -l /data/data/jakhar.aseem.diva/
adb shell run-as jakhar.aseem.diva cat uinfo6528482017877167631tmp
# testing_3:test
```

![run-as listing the data directory and reading the uinfo temp file](/images/diva/lab5-readback.png)

The `setReadable(true)` and `setWritable(true)` calls used the default `ownerOnly=true`, so both were no-ops: the file stayed `-rw-------` and the owner could already read and write it. The developer's attempt to widen access never took effect. The finding is the plaintext credential file in the sandbox, the same class as Labs 3 and 4 with a third store, and it is MASTG-TEST-0207, runtime storage of unencrypted data in the app sandbox.

- **Pass**: sensitive values are written only to encrypted stores such as `EncryptedFile`, or protected by a keystore-backed key.
- **Fail**: credentials are readable in plaintext in a file inside the app's data directory.
- **Evidence**: the file path and the plaintext line, plus the listing that shows the file.

## Lab 6: Insecure Data Storage, Part 4

The same credentials screen, and this time the write target is external storage. `saveCredentials` takes `Environment.getExternalStorageDirectory()`, the root of the shared storage volume, and writes a hidden file there:

```java
public void saveCredentials(View view) {
    EditText usr = (EditText) findViewById(R.id.ids4Usr);
    EditText pwd = (EditText) findViewById(R.id.ids4Pwd);
    File sdir = Environment.getExternalStorageDirectory();
    try {
        File uinfo = new File(sdir.getAbsolutePath() + "/.uinfo.txt");
        uinfo.setReadable(true);
        uinfo.setWritable(true);
        FileWriter fw = new FileWriter(uinfo);
        fw.write(usr.getText().toString() + ":" + pwd.getText().toString() + "\n");
        fw.close();
        Toast.makeText(this, "3rd party credentials saved successfully!", 0).show();
    } catch (Exception e) {
        Toast.makeText(this, "File error occurred", 0).show();
        Log.d("Diva", "File error: " + e.getMessage());
    }
}
```

![The credentials screen for the external storage lab](/images/diva/lab6-screen.png)

![The saveCredentials source writing to external storage](/images/diva/lab6-source.png)

On a modern device `getExternalStorageDirectory()` returns `/storage/emulated/0`, and the file is written to `/sdcard/.uinfo.txt`, a dotfile at the root of the shared volume. The `setReadable(true)` and `setWritable(true)` calls are no-ops again, and the file is owned by `media_rw` on the emulated volume.

External storage has a permission gate. DIVA declares `WRITE_EXTERNAL_STORAGE` in the manifest but never asks for it at runtime, so on Android 6 and later the permission starts denied and the write throws: the save shows the "File error occurred" toast and no file appears. The grant has to come from outside:

```bash
adb shell pm grant jakhar.aseem.diva android.permission.WRITE_EXTERNAL_STORAGE
adb shell am force-stop jakhar.aseem.diva
```

The force-stop matters: a running app keeps the permission state it started with, so the grant only takes effect after the process restarts. Reopen the lab, save again, and the file appears. Read it straight from the shell, with no `run-as`, because shared storage is visible to the shell and to any app holding `READ_EXTERNAL_STORAGE`:

```bash
adb shell ls -la /sdcard/.uinfo.txt
-rw-rw---- 1 u0_a170 media_rw 14 2026-09-27 23:06 /sdcard/.uinfo.txt
adb shell cat /sdcard/.uinfo.txt
testy:bigtick
```

![run-as free readback of the .uinfo.txt file](/images/diva/lab6-readback.png)

This is the worst store of the four. External storage is shared space: any app with the read permission can read the file, the data outlives the app's uninstall, and the credentials are in plaintext. The weakness is MASWE-0007, unencrypted sensitive data in shared storage, checked by MASTG-TEST-0200, files written to external storage.

- **Pass**: no sensitive value is written to external storage, or anything written there is encrypted with a keystore-backed key.
- **Fail**: credentials are readable in plaintext in a file on external storage, reachable by other apps with the storage permission.
- **Evidence**: the file path, the plaintext line, and the permission state the write needed.

## Lab 7: Input Validation Issues, Part 1

The screen asks for a username to search. `onCreate` opens a SQLite database named `sqli`, creates a `sqliuser(user, password, credit_card)` table, and seeds three rows, each with a password and a credit card. The search handler builds the query by concatenating the input:

```java
public void search(View view) {
    EditText srchtxt = (EditText) findViewById(R.id.ivi1search);
    try {
        Cursor cr = this.mDB.rawQuery("SELECT * FROM sqliuser WHERE user = '" + srchtxt.getText().toString() + "'", null);
        StringBuilder strb = new StringBuilder("");
        if (cr != null && cr.getCount() > 0) {
            cr.moveToFirst();
            do {
                strb.append("User: (" + cr.getString(0) + ") pass: (" + cr.getString(1) + ") Credit card: (" + cr.getString(2) + ")\n");
            } while (cr.moveToNext());
        } else {
            strb.append("User: (" + srchtxt.getText().toString() + ") not found");
        }
        Toast.makeText(this, strb.toString(), 0).show();
    } catch (Exception e) {
        Log.d("Diva-sqli", "Error occurred while searching in database: " + e.getMessage());
    }
}
```

![The search source concatenating the input into rawQuery](/images/diva/lab7-source.png)

The query becomes `SELECT * FROM sqliuser WHERE user = '<input>'`. A username of `test' OR 1=1 --` closes the string, makes the predicate always true, and comments out the trailing quote:

```sql
SELECT * FROM sqliuser WHERE user = 'test' OR 1=1 --'
```

Every seeded row comes back, and the handler prints them in a toast, passwords and credit cards included:

![The toast leaking every seeded user, password, and credit card](/images/diva/lab7-payload.png)

The finding is SQL injection in an app-local database, with the injected result displayed on screen. The query has no parameterization, and the result set proves it: three users with their passwords and card numbers from one input.

- **Pass**: queries use parameterized `selectionArgs` (or a library such as Room or SQLCipher), and no user input is concatenated into SQL.
- **Fail**: a query string concatenates user input, and the injected payload reveals rows beyond the searched user.
- **Evidence**: the concatenated `rawQuery` call and the leaked rows returned by the payload.

## Lab 8: Input Validation Issues, Part 2

The screen is a WebView with a URL field and a Go button. `onCreate` enables JavaScript on the WebView, and the Go button loads whatever is typed, with no scheme check and no allowlist:

```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.activity_input_validation2_urischeme);
    WebView wview = (WebView) findViewById(R.id.ivi2wview);
    WebSettings wset = wview.getSettings();
    wset.setJavaScriptEnabled(true);
}

public void get(View view) {
    EditText uriText = (EditText) findViewById(R.id.ivi2uri);
    WebView wview = (WebView) findViewById(R.id.ivi2wview);
    wview.loadUrl(uriText.getText().toString());
}
```

![The WebView source with JavaScript enabled and loadUrl on the raw input](/images/diva/lab8-source.png)

Pointing the WebView at `https://evil.com` loads the attacker's page inside the app:

![The WebView rendering the attacker page](/images/diva/lab8-evil.png)

The depth is the combination. JavaScript is enabled, and the input is trusted into `loadUrl`, so an attacker page loaded this way runs its scripts in the app's WebView context, and the same field accepts `javascript:` and `data:` URLs directly without any page. The mitigation is an allowlist of schemes and hosts, with JavaScript off for content the app does not control. The full WebView settings review is in [WebViews in Android Apps](/collections/mobile/android-webviews).

- **Pass**: the WebView loads only allowlisted HTTPS content the app controls, and JavaScript is enabled only where the app owns the page.
- **Fail**: the WebView loads attacker-influenced content (an arbitrary URL, or a `javascript:` or `data:` scheme) with JavaScript enabled.
- **Evidence**: the URL entered and the page or script result rendered in the WebView.

The MASVS control mapping for these labs is in [The OWASP MAS Project](/collections/mobile/mas-project).