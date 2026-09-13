---
title: "PrivescCheck PowerUp SharpUp"
slug: privesccheck-powerup-sharpup
category: notes
handbook: oscp
tags: ["privilege-escalation", "windows"]
draft: false
pubDatetime: 2026-08-29T09:33:29+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Three Windows privilege escalation enumerators that sit between [winPEAS](/collections/oscp/winpeas) and manual triage."
---
Three Windows privilege escalation enumerators that sit between [winPEAS](/collections/oscp/winpeas) and manual triage. All are read-only checkers; abusing what they find is the job of [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows). Preference order: PrivescCheck is the most complete and current sweep, PowerUp is the older classic whose value is built-in abuse commands for service and MSI vectors, and SharpUp is the cmd-only .NET port for shells where PowerShell is unusable. All three overlap heavily with winPEAS, so the real payoff is cross-checking what one misses.

## PrivescCheck (itm4n)

A single dependency-free PowerShell script, and the most thorough of the three: services and their ACLs, scheduled tasks, registry autoruns and autologon, AlwaysInstallElevated, credentials in registry and Windows Vault, token privileges, UAC configuration, hotfixes, LSA protection, AppLocker, and more.

```bash
curl -L https://github.com/itm4n/PrivescCheck/releases/latest/download/PrivescCheck.ps1 -o PrivescCheck.ps1
```

Transfer per [File Transfers](/collections/oscp/file-transfers), then dot-source and invoke:

```powershell
powershell -ep bypass -c ". .\PrivescCheck.ps1; Invoke-PrivescCheck"
```

Inside an evil-winrm session the shell is already PowerShell, so the dot-source and invoke run directly. An AMSI block on load is common on Defender-enabled hosts; spawning a fresh `powershell -ep bypass` from cmd usually clears it, and an AMSI bypass is the fallback.

Console output scrolls fast, so write the report and read the file instead:

```powershell
Invoke-PrivescCheck -Report PrivescCheck -Format TXT,HTML
```

Each check prints a status (EXTENDED, SUCCESS, FAILURE); the FAILURE entries are the leads. Feed them into the triage order in [Privilege Escalation (Windows)](/collections/oscp/privilege-escalation-windows) rather than acting blindly.

## PowerUp (PowerSploit)

Older and narrower, but the only one of the three with built-in abuse: for several findings it hands over the command that performs the escalation, not just the finding.

```bash
curl -L https://github.com/PowerShellMafia/PowerSploit/raw/master/Privesc/PowerUp.ps1 -o PowerUp.ps1
```

```powershell
powershell -ep bypass -c ". .\PowerUp.ps1; Invoke-AllChecks"
```

Defender signature-detects PowerUp almost on sight, so on any host with real AV expect an AMSI block; obfuscate, or fall back to SharpUp for the same checks in executable form.

What it checks and what it hands over:

- `Get-ServiceUnquoted`: unquoted service paths containing spaces; the abuse is planting a binary earlier in the path.
- `Get-ModifiableService`: services whose configuration the current user can change. The output carries an `AbuseFunction`, typically `Invoke-ServiceAbuse -Name <svc> -Command "net localgroup administrators <user> /add"`, which rewrites the service to run that command as SYSTEM.
- `Get-ModifiableServiceFile`: service binaries or their folders writable; replace the binary and restart or wait.
- `Get-RegistryAlwaysInstallElevated`: if both MSI keys are set, `Write-UserAddMSI` generates an installer that adds a user to administrators when anyone runs it.
- `Get-RegistryAutoLogon`: autologon credentials in the registry.
- `Get-ModifiableRegistryAutoRun`, `Find-PathDLLHijack`, `Find-ProcessDLLHijack`: autorun and DLL hijack candidates.

## SharpUp (GhostPack)

PowerUp's checks ported to C#: a plain exe that runs from cmd with no PowerShell involved. Fewer checks and no abuse functions, but immune to AMSI and constrained language mode, which makes it the tool of choice in a bare cmd shell.

```bash
curl -L https://github.com/r3motecontrol/Ghostpack-CompiledBinaries/raw/master/SharpUp.exe -o SharpUp.exe
```

Prebuilt binaries live in the Ghostpack compiled-binaries repo (the same source as [Rubeus](/collections/oscp/rubeus)); compiling locally is not worth it when the exe is already built.

```cmd
SharpUp.exe
```

It audits modifiable services, service registry keys and binaries, unquoted service paths, AlwaysInstallElevated, registry autoruns, %PATH% hijack candidates, and token privileges, printing each vulnerability as plain text with no flags to learn.

## Where each fits

- First pass on a Windows foothold: [winPEAS](/collections/oscp/winpeas) or PrivescCheck.
- PowerShell available and AV quiet: PrivescCheck for the sweep; PowerUp when it flags a service or MSI vector and the AbuseFunction saves writing one.
- cmd-only, AMSI hostile, or PowerShell broken: SharpUp.
