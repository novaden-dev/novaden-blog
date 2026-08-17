---
author: Kayra
pubDatetime: 2025-11-01T00:00:00Z
title: Fed Fed Fedora
slug: fed-fed-fedora
featured: false
draft: false
tags: ["linux", "fedora"]
category: journal
description: How a dying laptop, a warranty saga, and a "your Windows license only supports one display language" middle finger pushed me to Fedora KDE — and what worked, broke, and surprised me.
---

I don't know the exact breaking point. I was fine on Windows, if you ignore the "Finish setting up your account" nag, the forced Microsoft account, the ads/news in the start menu, and the few other messy things here and there. Yet, I've always wanted to move to Linux, the superior, open-source operating system, but never had the time. Then my laptop made the decision for me, random crashes followed by blue screens. Normally, I would have opened the back and started checking what's messed up but it was still in warranty and I was a bit overloaded off to the service center it goes.

<figure><img src="/images/migrated/fedora-01-bluescreen.png" alt="" width="299"><figcaption></figcaption></figure>

## My "Fight" with Lenovo

I sent it to Lenovo and reported two issues: an old one, screen flicker under load, and then the random crashes. I got lucky and reproduced the crash right in front of the service desk. A few days later I got the pickup message. They'd replaced the screen which is great. As for the crashes? The note translates to: "**Installed a new Windows, all issues gone."**

<figure><img src="/images/migrated/fedora-02-ssd-diag.png" alt="" width="188"><figcaption></figcaption></figure>

I'm not sure whether that says more about the technician's competence or Windows' reputation. It took then multiple other trips to the service center before it got sorted out but at the end I got multiple things replaced and the laptop was good again.

## Comparing Distros (a.k.a. The Other Rabbit Hole)

Since my SSD was already replaced and I had to start fresh, I thought that's a perfect time to make the move to Linux. When the machine came back it had Windows in Turkish, and when I tried to switch languages I got: "**Your Windows license only supports one display language."** Thanks for the parting middle finger, Windows. I didn't take a screenshot of it but that's how it looked like,

<figure><img src="/images/migrated/fedora-03-one-language.png" alt="" width="375"><figcaption></figcaption></figure>

A proper farewell from Windows I assume.

I wanted something good-looking, stable, and supports the software I use on daily basis, I checked reddit and multiple other blog posts and at times it felt like it is a religious war, everyone claiming what they are using is the superior OS that everyone should use.

- Ubuntu: popular, but there is the snap situation and then it's too mainstream.
- Arch: superior in many ways… if you survive the installation.
- Linux Mint: Windows-7 vibes. Your grandma (the chill and boring one) would love it.
- Debian, CentOS, and many others.

As I didn't want to go down a huge rabbit hole, I settled on Fedora. It checked my boxes, frequent updates yet stable. It comes in 2 flavors, KDE or GNOME. Rabbit Hole #2.

- KDE lets you customize *everything.* literally, *everything.*
- GNOME allows some customization via extensions, but nowhere near KDE.

KDE sounded better, but with great customization sometimes come great bugs. Reddit says KDE can be less stable than GNOME, others said it's solid now. I took the risk and went KDE. Install was smooth and straightforward. I'd already created the USB with Fedora Media Writer.

## First Boot: Updates and Repos

I opened Discover and updated the system. Then I launched Konsole (Not sure why it's with a K) and ran:

```bash
sudo dnf install \
  https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
  https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
```

That enables the **RPM Fusion** "free" and "nonfree" repositories, extra app sources Fedora doesn't ship by default. Why? I don't know but ChatGPT says, "Fedora avoids patent-encumbered codecs, DMCA-mess DVD libs, and proprietary drivers for legal/policy reasons. You can add them yourself if you accept the local legal implications." Once you are convinced:

```bash
sudo dnf install libavcodec-freeworld
```

Hardware status: touchscreen, Bluetooth mouse/headset, Wi-Fi, everything worked out of the box. At one point while I was playing around in the settings, the system started narrating literally everything I did (keys, text, content on the screen). Creepy. It stopped on its own, so I assume I accidentally toggled a screen reader shortcut.

## Theming, Crashes, and Random Turkish

I wanted to try the SweetKDE theme but I couldn't get it to install and it was just too bright for me. Ended up with:

- Reversal-Dark Icons
- Inter font
- Breeze Dark colors

Then, randomly: "maliit-keyboard killed by SIGABRT" popped up, in Turkish. I don't know why but that was weird, it went away on its own later on.

## App Sources in the Store (What's What)

In Fedora's app store, you'll see three flavors:

- Fedora Flatpak – curated by Fedora; fewer apps; sandboxed.
- Flathub – the big public Flatpak repo; more apps; sandboxed.
- Fedora Linux (RPM) – installed via `dnf`; *not* sandboxed; best for drivers/low-level stuff or when you need deep system integration.

Rule of thumb: If there's a Fedora Flatpak, use that. If not, use Flathub. Use RPMs when you need tight OS access (drivers, CLI tools, IDEs that need to poke around a lot, etc.).

I started installing my applications and at one point I saw: "Multiple matches of pycharm-community;2025.2.0.1-1.fc42;…copr…" Neat. Point 2 on the I fucked up scoreboard...

### The Good

#### KDE Connect

It embarrasses Windows "Phone Link." Install the app on your phone and you got file browsing, clipboard sharing, and remote control that actually feels like magic.

#### Performance

Fedora's performance is just… better. Typical day for me: two .NET backends, one Next.js frontend, one Electron desktop app, each in its own VSCodium instance, plus Cloud SQL proxy, pgAdmin, AI coding agents (Claude Code/Codex/Cursor/etc.), Zoom, and multiple browser profiles. A few brief freezes when RAM is fully utilized but just the fact that I can run all of this and the laptop not crashing is amazing.

#### Customization

I can tweak literally everything. I get bored fast, and even though I am still on the default widget, I can definitely see myself tweaking around and playing with the layout.

#### Virtual Desktops

I finally use them properly. Backend on one desktop, frontend on another. I believe there is such an option on Windows but I never used it, here it's daily use. 

Future update, I stopped using it that much because I got a second screen but still it's quite useful to have.

#### "Where's My Mouse?" and OS Zoom

If you move your mouse repeatedly, the cursor grows. Apparently I spin it when stressed or bored, this feature made me more aware of the times I do this. There's also an OS-level zoom I discovered by panic when I enabled it by accident and freaked out for minutes trying to figure out what happened.

<figure><img src="/images/migrated/fedora-04-os-zoom.png" alt="" width="162"><figcaption></figcaption></figure>

Plus: shortcuts everywhere. I just hate using the mouse, I am more of a keyboard guy, having the ability to create different shortcuts is just amazing.

#### Scripting and Systemctl

I wanted something to yell at me every 40 minutes to stop being a shrimp over the laptop. (I have been messing up my neck and back with 300hrs+ working months lately) On Windows I remember trying to do this with Task Scheduler and it wasn't a pleasant experience.

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/break-notify.sh <<'EOF'
#!/usr/bin/env bash

# Make sure desktop apps can see us
export DISPLAY=${DISPLAY:-:0}
export XDG_RUNTIME_DIR=/run/user/$UID

# Messages
titles=(
  "Break time"
  "Move your neck"
  "Un-hunch"
  "Water break"
)
bodies=(
  "40 minutes done. Stand up and roll shoulders."
  "Look 20s away from the screen."
  "Chest stretch + chin tuck."
  "Get up, walk 1 minute."
)

i=$((RANDOM % ${#titles[@]}))
j=$((RANDOM % ${#bodies[@]}))

# Notification (with icon)
notify-send -u normal -i dialog-information "${titles[$i]}" "${bodies[$j]}"

# Sound (optional, comment out if annoying)
if command -v paplay >/dev/null 2>&1; then
  paplay /usr/share/sounds/freedesktop/stereo/complete.oga
fi
EOF

chmod +x ~/.local/bin/break-notify.sh

nano ~/.config/systemd/user/break-notify.service

# Paste this in
[Unit]
Description=Show desktop break reminder

[Service]
Type=oneshot
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/%U
ExecStart=/home/%u/.local/bin/break-notify.sh

nano ~/.config/systemd/user/break-notify.timer

# Paste this in
[Unit]
Description=Run break reminder every 40 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=40min
Persistent=true

[Install]
WantedBy=default.target

# reload
systemctl --user daemon-reload
systemctl --user enable --now break-notify.timer
systemctl --user start break-notify.service
```

Done. Now every 40 minutes KDE taps me on the shoulder like "get up, grandpa".

That later was turned into a full product with customization, TouchGrass if you want to check it out.
### The Bad (Nitpicks)

System set to English, yet some errors and Konsole output, showed up in Turkish. Konsole itself claimed English (primary) and Turkish (fallback). It was weird af because English was already at the top of the list system-wide, and Konsole's own settings also said English first. I tried a few things (and argued with ChatGPT for a bit, increasing my odds of being hunted by robots later), but what actually worked was removing all other languages from Konsole's settings and restarting the laptop. After that, it behaved. I filed a bug with Fedora, the process was easy on their ticketing system, but it's low impact, so I'm not expecting fireworks or instant fixes.

SSH Keys for GitHub: I had to set up SSH keys + agent/unlock flow to avoid typing my key passphrase every push. Easy, but manual. On Windows/macOS, you often get smoother defaults. But again the whole thing didn't take over 5 minutes to setup.

Another thing I had to change: I encrypted my disk and, as always, I picked a really, really long password. With each reboot I had to type it again, I was making progress day by day but then it's just too slow. I looked for a way to unlock it automatically (I'm talking about the **drive encryption** password, not the normal user login password).

```bash
cat /etc/crypttab
sudo systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7 /dev/your_luks_partition_uuid
sudo dracut -f --regenerate-all
```

It worked… until after a few days and an update it started randomly asking for the passphrase again. Re-ran the commands, and it was all good again. Don't ask me, I don't know what happened.

Updates: Frequent, but you're not forced to reboot immediately. I download in the morning, install at day's end.

As for the apps, I didn't miss much. The only thing I kind of miss is WhatsApp Desktop, not a big deal, I just open it in the browser. What I really miss is Samsung Second Screen, which lets you use a Samsung tablet as an external monitor on Windows. I tried things like Weylus or VNC, but the quality is nowhere close. I'm still exploring options.

Desktop Ghosts: I added icons to my desktop and changed their order one day. After a restart, they reverted to the old order. I didn't care too much, but it was weird, especially because a few days later they changed again on their own. Ghosts, maybe. (Update, I finally found out what it's, sometimes I used to change the scale of the display which was causing the order of the desktop icons to change, dumb of me that I didn't notice it before but now we know)

<figure><img src="/images/migrated/fedora-05-ghost-icons.png" alt="" width="250"><figcaption></figcaption></figure>

Virtual Machines: One thing I haven't tested yet is VMs. I've been told VMware works fine, but there's a better option for Linux, KVM. I just haven't had enough time to try it yet.

Zoom Sounds: I can't get past how Zoom sounds on Fedora. You could grab a random piece of metal, shake it violently, and it would still sound better than whatever Zoom is doing here. Other applications are mostly fine but when increasing/decreasing the volume there is this sound that I don't mind but it just sounds trash, I thought that's how things are but turn out it's not. After some back and forth with ChatGPT this is where we got: Fedora ships PipeWire with flat volumes ON meaning that every app can drag the device to 100%. That's why sound was awful. (I don't fully trust that but the fix actually worked and the volume change sound was much better)

```bash
mkdir -p ~/.config/pipewire/pipewire-pulse.conf.d
cat > ~/.config/pipewire/pipewire-pulse.conf.d/20-noflat.conf <<'EOF'
pulse.properties = { flat-volumes = false }
EOF
systemctl --user restart pipewire-pulse
```

That worked and turns out the actual sound is much more better! Water drops sound. However, each time I restart my laptop it would go back to the shitty sound. To make it persistent, I create this simple setup,

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/pipewire-pulse-restart.service

[Unit]
Description=Restart pipewire-pulse after session starts
After=default.target pipewire-pulse.socket
Wants=pipewire-pulse.socket

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'sleep 7 && systemctl --user restart pipewire-pulse'

[Install]
WantedBy=default.target
```

It simply restarts the service. The reason why added the sleep 7 is because without it, it was restarting it right away, but it was still in the middle of "I just started, I'm socket-activated, I'm still wiring nodes". Which meant that sometimes the restart worked, sometimes it didn't, sometimes the app reconnected to the old one. After the sleep 7 thing it worked perfectly! There were 2 more issues, the zoom sounding garbage and that the system volume doesn't affect the application volumes but that's for another day.

## Verdict

No regrets. Fedora KDE gives me performance, control, and fewer corporate handcuffs. Sure, I had a few "why is this in Turkish" moments, an accidental screen-reader seance, one Sweet KDE install crash, and some desktop-icon moving on their own. But overall the experience is excellent. If you can survive a warranty saga and a light Linux learning curve, the payoff is worth it.

<figure><img src="/images/migrated/fedora-06-verdict.png" alt="" width="188"><figcaption></figcaption></figure>
