---
title: "Password Spraying"
slug: password-spraying
category: notes
handbook: oscp
tags: ["password-attacks", "active-directory"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Spraying is the inverse of [Brute Forcing Logins](/collections/oscp/brute-forcing-logins): one password tried across many accounts, instead of many passwords against one account."
---
Spraying is the inverse of [Brute Forcing Logins](/collections/oscp/brute-forcing-logins): one password tried across many accounts, instead of many passwords against one account. Testing a single password per round keeps every account well under its lockout threshold, so a whole domain can be swept without locking anyone out. It is a core early-access technique on the exam, the usual way a validated user list turns into a first credential.

The password comes from somewhere plausible: a value pulled from a share or GPP, a hash already cracked ([Kerberoasting](/collections/oscp/kerberoasting), [AS-REP Roasting](/collections/oscp/as-rep-roasting)), an organisation-flavoured guess (`Season+Year!`, `CompanyName1`), or a known credential swept for reuse across the domain.

## Inputs

- A user list. From a foothold, build one by RID cycling the DC (see [NetExec](/collections/oscp/netexec)); with no access, gather names by OSINT or [kerbrute](/collections/oscp/kerbrute) user enumeration.
- One password to test this round.

## Spray

```bash
nxc smb <DC_IP> -d <domain> -u users.txt -p 'Season2024!' --continue-on-success
```

- `-u users.txt` reads the user list from file; `-p` is the single password for this round.
- `--continue-on-success` keeps going after the first hit, so every reuse is caught, not just the first.
- Point it at the DC and use `-d <domain>` to validate domain accounts. Spraying is domain-scoped: a user list from one domain's DC only contains that domain's accounts, and a child domain's users are validated against the child DC, not the root.

### Domain versus local authentication

The username alone does not identify the account database. `secura.yzx\eric.wallows` is a domain principal, while `ERA\eric.wallows` is local to `ERA`. The same username and password can fail in the domain scope and succeed locally.

```bash
# Domain account spray
nxc smb <DC_IP> -d secura.yzx -u users.txt -p 'Season2024!' --continue-on-success

# Local account spray on one host
nxc winrm TARGET --local-auth -u users.txt -p 'Season2024!' --continue-on-success
```

Use `--local-auth` when the credential came from the target's local SAM or a host-specific configuration. Local spraying is per host, not a sweep of the domain. An ambiguous name such as `administrator` may need testing in both scopes.

## Read the NTSTATUS lines

A spray is judged by the NTSTATUS on each line, not by scanning for `[+]`. Several codes on a `[-]` line still mean the password was right:

| Status | Meaning |
| --- | --- |
| `STATUS_LOGON_FAILURE` | Wrong password, or the user does not exist. |
| `STATUS_PASSWORD_MUST_CHANGE` | Password is correct; it is expired and must be reset. A real hit. |
| `STATUS_PASSWORD_EXPIRED` | Password is correct; the account password has expired. A real hit. |
| `STATUS_ACCOUNT_DISABLED` | The account is disabled. Fires regardless of the password. |
| `STATUS_ACCOUNT_RESTRICTION` | The account is restricted (logon hours, or logon-workstation bound). May be a valid password blocked by policy, but it can also fire regardless of the password, so flag it and verify separately rather than trusting it. |
| `STATUS_ACCOUNT_LOCKED_OUT` | Lockout is being tripped. Stop and back off. |

`STATUS_ACCOUNT_RESTRICTION` is the subtle one. An account bound to specific logon workstations returns it for any password over NTLM, before the password is even checked, so it does not confirm a guess on its own. Kerberos pre-auth (`kerbrute passwordspray`, `impacket-getTGT`) validates the password independently of that restriction if it needs to be resolved.

## Lockout discipline

The reason spraying exists is to stay under lockout. One password per round, then wait out the observation window before the next. On the exam assume a real threshold and never loop passwords back to back; a lockout that alerts a defender or blocks a needed account is worse than a slow spray.

**Every host is a separate set of failed attempts.** One round across seven hosts is seven bad passwords per user, not one, so a multi-host round burns the threshold seven times faster than the same round against the DC alone. On Medtech a single rabbit round across all seven hosts locked five accounts, three of them working credentials, mid-sweep. The split output is the fingerprint of crossing the threshold during the run: hosts tried early report `STATUS_LOGON_FAILURE`, hosts tried late report `STATUS_ACCOUNT_LOCKED_OUT`.

Which is why the policy gets read before the first round, not after the lockout: with a threshold of 4 and seven hosts, a multi-host round is a mathematical certainty of lockout for every wrong-password user. The deeper point: in a single domain, authentication validity is domain-wide, so spraying the fleet answers nothing that spraying the DC alone does not. One host (the DC) per round, one password per round, and a wrong-password user costs exactly one attempt; a validated hit then works on every member server automatically.

Read the policy first when any credential is in hand. `--pass-pol` returns the three numbers that set the pace: the lockout threshold (bad attempts allowed before lockout), the observation window (how long before the bad-password count resets), and the lockout duration:

```bash
nxc smb <DC_IP> -u user -p pass --pass-pol
rpcclient -U 'user%pass' <DC_IP> -c getdompwinfo    # same policy over RPC
```

From a domain-joined foothold the same policy reads with no tools transferred:

```cmd
net accounts /domain
```

A threshold of 0 means no lockout, so spray freely. Otherwise keep one or two guesses under the threshold per window. With no credential to read the policy, assume a low threshold (3 to 5) and go slow.

## When Accounts Lock Anyway

Stop spraying on the first `STATUS_ACCOUNT_LOCKED_OUT` - every further failure can keep the clock running. The lockout blocks *new* domain logons only, so three things survive: already-authenticated sessions keep working, the machine account still authenticates, and the passwords themselves remain valid - nothing needs changing, just waiting.

The timer comes from the machine context, no user credential needed:

```cmd
net accounts /domain
```

`Lockout duration` counted from the *last* failed attempt is when the account unlocks, so the countdown restarts with every guess. Work on anything that does not need a domain logon while it runs (established shells, collected graphs, file loot, anonymous services), then test the unlock with exactly one known-good password rather than a guess, or the round starts over.

## Once a credential lands

A validated pair feeds straight into authenticated enumeration and the rest of the chain: [BloodHound](/collections/oscp/bloodhound) collection, [Kerberoasting](/collections/oscp/kerberoasting), and eventually [DCSync](/collections/oscp/dcsync) or [AD Lateral Movement](/collections/oscp/ad-lateral-movement) if it holds the rights.
