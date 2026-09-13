---
title: "Burp Suite"
slug: burp-suite
category: notes
handbook: oscp
tags: ["web"]
draft: false
pubDatetime: 2026-07-22T21:58:53+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "Intercepting proxy for web testing."
---
Intercepting proxy for web testing. Community Edition ships with Kali.

## Window stuck, cannot resize or maximize

Symptom: the Burp window opens at a fixed size, the maximize button and window edges do nothing, and it stays broken across closing and reopening Burp, logging out, and locking the screen.

Cause: Burp saves its window geometry through the Java Preferences API in `~/.java/.userPrefs/burp/prefs.xml`. Once that saved size or position goes bad, from a resolution change, HiDPI scaling, or an unclean exit, Burp restores the same broken geometry on every launch. The bad state lives on disk, not in the running process, so restarting never helps.

Fix, with Burp closed:

```bash
rm -rf ~/.java/.userPrefs/burp
```

Reopen Burp and the window returns to its default size. This clears only UI preferences, not saved projects.

The window-manager shortcuts (`Alt`+`F10` to maximize, double-click the title bar, `Alt`+left-drag to move, `Alt`+`F8` to resize) only help when the window is merely off-screen. When the cause is the saved geometry, they do nothing, and removing the prefs is the only thing that recovers it. Worth knowing before the exam, where a stuck proxy costs real time.

## Intruder in Community Edition

Community throttles Intruder to roughly one request per second, and the throttle is the point of the free version, not a setting to find. Anything past a few hundred payloads will not finish, so Intruder is for shaping a request rather than for volume. Work out the position and the payload processing there, confirm it fires, then hand the actual run to a purpose-built tool: hydra for a login ([Brute Forcing Logins](/collections/oscp/brute-forcing-logins)), `ffuf` for anything path or parameter shaped ([Web Content Discovery](/collections/oscp/web-content-discovery)).

**Payload processing** is the reason to use it at all. Rules apply in order to each payload before it is sent, which encodes a credential that cannot be expressed as a plain wordlist entry. For an `Authorization: Basic` header, mark the base64 blob as the position and add **Add Prefix** `admin:` then **Base64-encode**, and a plain password list becomes a stream of encoded `admin:<password>` values. On Walla that found the panel password, though the run was 96507 payloads and never had a chance of completing at Community speed.

Results are held in memory in the attack window. Closing it, or Burp failing, loses them, and there is no saved attack state to reopen in Community. Copy a hit out as soon as it appears.

## Copying encoded values out of a response

The **Pretty** view reflows and indents the response, inserting whitespace and line breaks that are not in the real bytes. Selecting an encoded token (base64, hex) from Pretty can pull in those extra spaces or stop short at a wrap. This breaks the value whether it is copied out by hand or decoded in place: the **Inspector** decodes exactly what is selected, so an incomplete Pretty selection decodes to a wrong or truncated value just the same. The Inspector is not a fix for a bad selection. Read encoded tokens from the **Raw** view, where the bytes are unmodified, and only feed a complete, whitespace-free token to any decoder. On Nickel a base64 SSH password selected from Pretty decoded short in the Inspector too, and only the full token from Raw gave the real password.
