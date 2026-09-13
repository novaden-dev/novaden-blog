---
name: GlucoBar
tagline: Accu-Chek CGM readings in the Linux panel, no phone in hand.
status: prototype
stack: ["Python", "GTK", "GNOME"]
repo: https://github.com/KayraNafi/GlucoBar
order: 2
draft: true
---

Checking my glucose meant unlocking my phone every time. Now it is a number in
the top bar, with 3 to 24 hours of history behind it, an icon that changes
colour when things go sideways, and notifications only on the transitions that
matter.

It reads from the SmartGuide cloud, so it needs no ADB bridge, no companion
app, no homelab. Unofficial and not a medical device: the real alarms stay on
the real app. Working prototype, first-run auth and packaging still to come.
