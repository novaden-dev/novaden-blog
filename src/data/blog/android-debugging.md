---
title: "Android Debugging"
slug: android-debugging
category: notes
handbook: mobile
tags: ["android"]
draft: false
pubDatetime: 2026-09-27T00:00:00+03:00
description: "How a crash shows up in logcat and how to isolate it: the ring buffers, priority and tag filters, the clear-reproduce-read sequence, and reading the FATAL EXCEPTION trace down to the line that caused it."
---

When an app crashes on Android, the full trace is written to `logcat`, the device's central log. The problem is not finding the trace; it is that logcat holds messages from every process on the device, and a crash you care about sits inside thousands of lines of system noise. The technique is isolation: clear the buffer, reproduce the crash, filter the view, then read the trace backwards from its root cause.

## What Logcat Is

`logcat` is a ring buffer of tagged messages. Every process on the device writes to it, and when the buffer fills, the oldest entries are dropped to make room for new ones. Each line has the same shape:

```text
09-27 19:15:28.715  5957  5957 E AndroidRuntime: FATAL EXCEPTION: main
```

Reading left to right: timestamp, process id, thread id, priority letter, the tag that logged the message, then the message itself. Two of those matter for isolating a crash:

- **Priority**: `V` verbose, `D` debug, `I` info, `W` warn, `E` error, `F` fatal, and `S` which silences a tag entirely.
- **Tag**: the component that wrote the line. The crash reporter is always `AndroidRuntime`.

The buffer is split into named sub-buffers, each holding a different class of message. You read the default `main` buffer with a plain `adb logcat`. The one you want for crashes is `crash`, which holds only crash traces and little else:

```bash
adb logcat -b crash
```

The `system`, `events`, and `radio` buffers hold framework, high-level event, and telephony messages respectively. When a crash does not show up where you expect, it is usually because it is in a different buffer, not because it was never logged.

## The Clear, Reproduce, Read Sequence

Logcat shows whatever is currently in the buffer, and the buffer is always full. Looking at it before reproducing a crash means sorting your crash out of history. The sequence that removes that ambiguity:

```bash
adb logcat -c                 # clear the buffer
# launch the app and trigger the crash
adb logcat -d                 # dump what is buffered, then exit
```

`-c` empties the buffers, so everything after it was logged by your session. `-d` prints and returns, which is what you want when you are done reproducing; without it `adb logcat` streams forever until you interrupt it.

You still have to find your app among the noise. Two filters handle that. The first matches the app's own process, whatever tags it uses:

```bash
adb logcat --pid=$(adb shell pidof -s com.example.app)
```

`pidof -s` prints the app's process id, and `--pid` keeps only lines from that process. The second filter uses the tag and priority syntax, which is useful when the crashing process died and you want to watch the reporter itself:

```bash
adb logcat "AndroidRuntime:E" "*:S"
```

`Tag:Level` keeps lines from that tag at that priority or higher, and `*:S` silences every other tag. Combined they mean "only fatal messages from AndroidRuntime", which is the crash reporter and almost nothing else.

## Reading a Crash Trace

A Java or Kotlin crash appears as one block. It opens with a `FATAL EXCEPTION` line, then names the process and thread, then prints the exception and its stack:

```text
E AndroidRuntime: FATAL EXCEPTION: main
E AndroidRuntime: Process: com.mobilehackinglab.iotconnect, PID: 5957
E AndroidRuntime: java.lang.RuntimeException: Unable to start activity
E AndroidRuntime:     at com.mobilehackinglab.iotconnect.CommunicationManager.initialize(CommunicationManager.kt:39)
E AndroidRuntime:     at com.mobilehackinglab.iotconnect.LoginActivity.onCreate(LoginActivity.kt:38)
E AndroidRuntime: Caused by: java.lang.SecurityException: One of RECEIVER_EXPORTED or RECEIVER_NOT_EXPORTED should be specified when a receiver isn't being registered exclusively for system broadcasts
E AndroidRuntime:     at android.os.Parcel.createExceptionOrNull(Parcel.java:3242)
```

Two things in that block identify the defect:

- **`Caused by`**: the exception that actually started the chain. The `RuntimeException` on the first line is a wrapper, the Android framework's generic "activity could not start" message. The `Caused by` clause names the real exception and the one line of app code that triggered it, `CommunicationManager.kt:39` in this case. When a trace has several `Caused by` clauses, the last one is the root cause.
- **The frames under it**: the topmost line whose class is in your app's package is where the failing call was made. Framework frames below it tell you which system path reached it, useful when the app's own frame says nothing about the trigger.

The trace also carries the process id on the `Process:` line, so when the app does not restart you can check it died for real with `adb shell pidof` and see the id change on relaunch.

The exception in the example is the one you hit when an app targets Android 14 or newer and registers a `BroadcastReceiver` without the `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED` flag. Reading the trace tells you that in one pass: the wrapper is meaningless, the `Caused by` is the finding, and the line number points at the code. The same shape appears for `NullPointerException` inside `onCreate`, a missing native library, or a missing activity in the manifest.

## When There Is No FATAL EXCEPTION

Two common failure modes never print a `FATAL EXCEPTION` block.

**ANR (Application Not Responding)** is a blocked main thread, not a crash. The process stays alive and the system shows the "App isn't responding" dialog. The trace lands in the `events` buffer as an `am_anr` entry:

```bash
adb logcat -b events -d | grep am_anr
```

The fix path is different too: the trace points at what the main thread was doing when it stopped responding, usually a network call or disk I/O on the UI thread, not an exception to patch.

**Native crashes** come from C and C++ code (JNI libraries, or the runtime itself) and are reported by a different logger under the `libc` and `DEBUG` tags. The process dies with `SIGSEGV` or similar and the output is a signal line followed by a `backtrace:`. An ARM-only native library on an x86_64 emulator is a different case: it fails during install with `INSTALL_FAILED_NO_MATCHING_ABIS`, or at load time with an `UnsatisfiedLinkError`, which is a Java exception and prints a normal `FATAL EXCEPTION`.
