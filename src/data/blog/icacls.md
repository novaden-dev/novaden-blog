---
title: "icacls"
slug: icacls
category: notes
handbook: oscp
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-08-25T22:37:50+03:00
modDatetime: 2026-09-09T21:52:45+03:00
description: "Built-in Windows tool that prints and changes NTFS permissions on files and folders."
---
Built-in Windows tool that prints and changes NTFS permissions on files and folders. Already on the target, so no transfer. Use it to confirm winPEAS "writable folder / insecure executable" hits before dropping a payload. For services and registry, [accesschk](/collections/oscp/accesschk) is still needed; for paths on disk, `icacls` is enough.

## View permissions

```cmd
icacls C:\xampp\apache\bin
icacls C:\xampp\apache\bin\httpd.exe
icacls "C:\Program Files\Some Service"
```

Output is one path, then one line per principal with its rights:

```
C:\xampp\apache\bin NT AUTHORITY\Authenticated Users:(OI)(CI)(W)
                    BUILTIN\Users:(OI)(CI)(RX)
                    BUILTIN\Administrators:(I)(F)
                    NT AUTHORITY\SYSTEM:(I)(F)
```

Match principal names to the current identity (`whoami`, `whoami /groups`). `Authenticated Users` and `Users` usually include a normal domain logon.

## Rights that matter

| Mask / flag | Meaning for privesc |
|---|---|
| `(F)` | Full control: read, write, delete, change the ACL |
| `(M)` | Modify: write and delete, enough to replace a file |
| `(W)` | Write: create/overwrite depending on the object |
| `(RX)` | Read and execute only: not enough to plant a binary |
| `(R)` | Read only |
| `WriteData` / `CreateFiles` | On a **directory**: create new files inside (DLL drop, new exe) |
| `AppendData` / `CreateFolders` | Create subdirs; alone does not replace an existing file |
| `(OI)` | Object inherit: applies to files created in the folder |
| `(CI)` | Container inherit: applies to subfolders |
| `(I)` | Inherited from a parent; still effective |
| `(N)` | No access |

**Directory writable, file not:** can drop a new name (DLL hijack) but cannot overwrite `httpd.exe` / `mysqld.exe`.  
**File writable:** can replace the service binary (back it up first).  
**Neither:** dead end for that path.

## Confirm before exploit

winPEAS may flag `Authenticated Users [Allow: WriteData/CreateFiles]` on a service bin folder. Prove it as the current user:

```cmd
whoami
icacls C:\xampp\apache\bin
icacls C:\xampp\apache\bin\httpd.exe
```

If the dir shows `(W)` / `CreateFiles` for a group you are in, DLL hijack or a new file in that folder is on the table. If the exe shows `(M)` or `(F)` for you, overwrite is simpler ([Windows Service Exploits](/collections/oscp/windows-service-exploits) §4 and §5).

## Change permissions (rare on exam)

Changing an ACL is almost never the privesc step itself; the finding is usually that the ACL is already weak. The one common case is `takeown` + `icacls /grant` after a privilege allows seizing an object, shown with the commands in [Windows Token Privileges](/collections/oscp/windows-token-privileges#setakeownershipprivilege).

## icacls vs accesschk

| | `icacls` | `accesschk` |
|---|---|---|
| On target by default | Yes | No (Sysinternals, upload) |
| Files / folders | Yes | Yes |
| Services (`sc` ACLs) | No | Yes (`-c`) |
| Registry keys | No | Yes (`-k`) |
| Effective access for one user | Manual read of the DACL | Direct (`-uwcqv user object`) |

Start with `icacls` on paths winPEAS named. Reach for [accesschk](/collections/oscp/accesschk) when the question is service start/stop/change-config or a registry `ImagePath`.
