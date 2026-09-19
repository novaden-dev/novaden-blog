---
title: "Automated Analysis with MobSF"
slug: mobsf
category: notes
format: guide
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-15T00:00:00+03:00
description: "MobSF for Android: running it in Docker, the static-analysis report, driving the dynamic analyzer against a rooted VM, the REST API for CI, and where automated triage stops and manual work begins."
---

MobSF (Mobile Security Framework) does the first pass for you. Point it at an APK and it unpacks the archive, reads the manifest, decompiles the code, and returns a report: permissions, exported components, hardcoded secrets, weak crypto, the signing certificate, the domains it connects to. It does in a couple of minutes what would take you an hour of `jadx` and `grep`.

## What It Does

MobSF has two engines, both driven from the web UI:

- **Static analysis**: works on the file alone, no device. Decompiles the APK, parses `AndroidManifest.xml`, runs pattern-based code analysis, extracts strings and secrets, checks the certificate, lists trackers and network endpoints. This is the part you will use every time.
- **Dynamic analysis**: runs the app on a connected Android VM and observes it. Runtime API monitoring, traffic capture through its own CA, SSL-pinning bypass, and an activity tester. It takes more setup and breaks more easily, but it catches what only appears at runtime.

The tool also scans iOS IPAs, but the procedure below is the Android side: APK, manifest, ADB, a rooted Android VM. The iOS workflow differs enough to get its own section here once the iOS material lands.

## Running It

Use Docker, because MobSF depends on a decompiler toolchain, a JDK, and a lot of Python packages that are a pain to install by hand:

```bash
docker pull opensecurity/mobile-security-framework-mobsf:latest
docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf:latest
```

The UI comes up on `http://localhost:8000`. Recent versions require a login and print the credentials or an API key to the container console on first start.

From source, when you want the dynamic analyzer to reach a local emulator without Docker networking in the way:

```bash
git clone https://github.com/MobSF/Mobile-Security-Framework-MobSF.git
cd Mobile-Security-Framework-MobSF
./setup.sh          # Linux/macOS; setup.bat on Windows
./run.sh            # serves on 127.0.0.1:8000
```

## Static Analysis

Drag an APK onto the upload box. MobSF decompiles and scans, then shows the report.

## Dynamic Analysis

The dynamic analyzer needs a rooted Android VM it can drive over ADB. Genymotion works well, and a rootable Android Studio AVD (see [Android Lab Setup](/collections/mobile/android-lab-setup)) also works. MobSF documents which system images it supports. Point MobSF at the device with the `MOBSF_ANALYZER_IDENTIFIER` setting (the `adb devices` serial), start the analyzer from the report, and it installs its own instrumentation and launches the app.

What it gives you once the app is running:

- **Traffic capture**: MobSF runs its own HTTPS proxy and installs its CA, so requests and responses show up without a separate Burp setup.
- **SSL-pinning bypass**: it ships Frida scripts and toggles them for you, the same job done by hand in [Intercepting Traffic with Burp Suite](/collections/mobile/intercepting-mobile-traffic).
- **Runtime API monitoring**: logs calls to crypto, file, network, and IPC APIs as the app uses them.
- **Activity tester**: launches each activity, exported ones included, and screenshots them, which surfaces screens reachable without authentication.

MobSF drives Frida under the hood. When you need a hook it does not offer, drop to Frida directly ([Dynamic Instrumentation with Frida](/collections/mobile/frida)); the two are the same engine at different levels of control.

## REST API

MobSF has a REST API that mirrors the UI, which is how it goes into a pipeline to scan each build. Every call carries an `Authorization` header with the API key from the UI's API docs page:

```bash
KEY="<your-api-key>"

# Upload, then scan by the returned hash
curl -F "file=@app.apk" http://localhost:8000/api/v1/upload -H "Authorization:$KEY"
curl -X POST http://localhost:8000/api/v1/scan       -H "Authorization:$KEY" -d "hash=<hash>"

# Pull the report
curl -X POST http://localhost:8000/api/v1/report_json -H "Authorization:$KEY" -d "hash=<hash>"
curl -X POST http://localhost:8000/api/v1/report_pdf  -H "Authorization:$KEY" -d "hash=<hash>" -o report.pdf
```

For scanning source rather than a built artifact, the same team's **`mobsfscan`** (`pip install mobsfscan`) is a standalone SAST tool that runs in CI without the full framework:

```bash
mobsfscan /path/to/android-project
```

## Where It Stops

| Watch for | Why |
|---|---|
| False positives | Pattern-based static analysis over-reports. Confirm each finding in the decompiled code. |
| A quiet dynamic run | Emulator-aware or Frida-aware apps detect MobSF's instrumentation and change behavior or exit. |
| Analyzer will not attach | Wrong device identifier, an unsupported system image, or a non-rooted VM. Check `adb devices` and the MobSF docs for supported images. |
| Native code | MobSF flags native libraries but does not analyze the C/C++. That is Ghidra's job. |

MobSF is a triage tool. It narrows the code down quickly, and the actual finding almost always comes from reading that code by hand.
