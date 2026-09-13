---
title: OSCP
description: "A practical PEN-200 field manual: enumeration through Active Directory, built from lab work and repeatable attack paths."
kind: handbook
status: ongoing
draft: false
entries:
  - id: oscp-s01
    post: active-directory-concepts
    section: "Concepts"
  - id: oscp-002
    post: base64-and-encodings
    section: "Concepts"
  - id: oscp-s02
    post: linux-permissions
    section: "Concepts"
  - id: oscp-004
    post: network-services-handbook
    section: "Concepts"
  - id: oscp-005
    post: information-gathering
    section: "Methodology"
  - id: oscp-s04
    post: privilege-escalation-linux
    section: "Methodology"
  - id: oscp-007
    post: privilege-escalation-windows
    section: "Methodology"
  - id: oscp-s03
    post: active-directory
    section: "Methodology"
  - id: oscp-s05
    post: smb-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-010
    post: ftp-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-011
    post: smtp-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-012
    post: snmp-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-013
    post: dns-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-014
    post: rpc-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-015
    post: database-enumeration
    section: "Techniques/Service Enumeration"
  - id: oscp-s06
    post: sql-injection
    section: "Techniques/Web"
  - id: oscp-017
    post: command-injection
    section: "Techniques/Web"
  - id: oscp-018
    post: file-inclusion
    section: "Techniques/Web"
  - id: oscp-s07
    post: file-upload
    section: "Techniques/Web"
  - id: oscp-020
    post: server-side-template-injection
    section: "Techniques/Web"
  - id: oscp-021
    post: mass-assignment
    section: "Techniques/Web"
  - id: oscp-022
    post: web-content-discovery
    section: "Techniques/Web"
  - id: oscp-023
    post: virtual-hosts
    section: "Techniques/Web"
  - id: oscp-024
    post: webdav
    section: "Techniques/Web"
  - id: oscp-025
    post: webshells
    section: "Techniques/Web"
  - id: oscp-026
    post: imagemagick
    section: "Techniques/Web"
  - id: oscp-027
    post: exiftool-djvu-injection
    section: "Techniques/Web"
  - id: oscp-028
    post: text4shell
    section: "Techniques/Web"
  - id: oscp-s08
    post: reverse-shells
    section: "Techniques/Shells and Access"
  - id: oscp-030
    post: ssh-key-access
    section: "Techniques/Shells and Access"
  - id: oscp-031
    post: file-transfers
    section: "Techniques/Shells and Access"
  - id: oscp-032
    post: fixing-public-exploits
    section: "Techniques/Shells and Access"
  - id: oscp-033
    post: libreoffice-macros
    section: "Techniques/Shells and Access"
  - id: oscp-034
    post: restricted-shells
    section: "Techniques/Shells and Access"
  - id: oscp-035
    post: cron-jobs
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-s09
    post: suid-binaries
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-037
    post: sudo
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-038
    post: linux-capabilities
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-039
    post: linux-groups
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-040
    post: nfs-no-root-squash
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-041
    post: service-exploits
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-042
    post: kernel-exploits
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-043
    post: mysql-privilege-escalation
    section: "Techniques/Privilege Escalation (Linux)"
  - id: oscp-044
    post: windows-service-exploits
    section: "Techniques/Privilege Escalation (Windows)"
  - id: oscp-045
    post: windows-autoruns-and-scheduled-tasks
    section: "Techniques/Privilege Escalation (Windows)"
  - id: oscp-s10
    post: windows-token-privileges
    section: "Techniques/Privilege Escalation (Windows)"
  - id: oscp-047
    post: weak-file-permissions
    section: "Techniques/Privilege Escalation (Windows)"
  - id: oscp-048
    post: windows-remote-access
    section: "Techniques/Privilege Escalation (Windows)"
  - id: oscp-049
    post: credential-hunting
    section: "Techniques/Credentials"
  - id: oscp-050
    post: windows-credential-hunting
    section: "Techniques/Credentials"
  - id: oscp-051
    post: brute-forcing-logins
    section: "Techniques/Credentials"
  - id: oscp-052
    post: password-spraying
    section: "Techniques/Credentials"
  - id: oscp-053
    post: password-cracking
    section: "Techniques/Credentials"
  - id: oscp-054
    post: active-directory-enumeration
    section: "Techniques/Active Directory"
  - id: oscp-055
    post: as-rep-roasting
    section: "Techniques/Active Directory"
  - id: oscp-s11
    post: kerberoasting
    section: "Techniques/Active Directory"
  - id: oscp-057
    post: kerberos-delegation
    section: "Techniques/Active Directory"
  - id: oscp-058
    post: silver-and-golden-tickets
    section: "Techniques/Active Directory"
  - id: oscp-059
    post: acl-abuse
    section: "Techniques/Active Directory"
  - id: oscp-060
    post: ad-lateral-movement
    section: "Techniques/Active Directory"
  - id: oscp-061
    post: dcsync
    section: "Techniques/Active Directory"
  - id: oscp-062
    post: ntds-dit-extraction
    section: "Techniques/Active Directory"
  - id: oscp-063
    post: laps
    section: "Techniques/Active Directory"
  - id: oscp-064
    post: llmnr-poisoning-and-ntlm-relay
    section: "Techniques/Active Directory"
  - id: oscp-065
    post: ad-persistence
    section: "Techniques/Active Directory"
  - id: oscp-066
    post: tunneling-and-pivoting
    section: "Techniques/Pivoting"
  - id: oscp-067
    post: accesschk
    section: "Tools"
  - id: oscp-068
    post: autorecon
    section: "Tools"
  - id: oscp-s12
    post: bloodhound
    section: "Tools"
    role: supplementary
  - id: oscp-070
    post: burp-suite
    section: "Tools"
  - id: oscp-071
    post: chisel
    section: "Tools"
  - id: oscp-072
    post: evil-winrm
    section: "Tools"
  - id: oscp-073
    post: feroxbuster
    section: "Tools"
  - id: oscp-074
    post: ffuf
    section: "Tools"
  - id: oscp-075
    post: git-dumper
    section: "Tools"
  - id: oscp-076
    post: hashcat
    section: "Tools"
  - id: oscp-077
    post: icacls
    section: "Tools"
  - id: oscp-078
    post: impacket
    section: "Tools"
  - id: oscp-079
    post: john
    section: "Tools"
  - id: oscp-080
    post: kerbrute
    section: "Tools"
  - id: oscp-081
    post: ligolo-ng
    section: "Tools"
  - id: oscp-082
    post: linenum
    section: "Tools"
  - id: oscp-083
    post: linpeas
    section: "Tools"
  - id: oscp-084
    post: linux-exploit-suggester
    section: "Tools"
  - id: oscp-085
    post: linux-smart-enumeration
    section: "Tools"
  - id: oscp-086
    post: metasploit
    section: "Tools"
  - id: oscp-087
    post: mimikatz
    section: "Tools"
  - id: oscp-088
    post: msfvenom
    section: "Tools"
  - id: oscp-089
    post: nc
    section: "Tools"
  - id: oscp-090
    post: netexec
    section: "Tools"
  - id: oscp-091
    post: powercat
    section: "Tools"
  - id: oscp-092
    post: privesccheck-powerup-sharpup
    section: "Tools"
  - id: oscp-093
    post: pspy
    section: "Tools"
  - id: oscp-094
    post: pygpoabuse
    section: "Tools"
  - id: oscp-095
    post: rubeus
    section: "Tools"
  - id: oscp-096
    post: searchsploit
    section: "Tools"
  - id: oscp-097
    post: ssh-tunnels
    section: "Tools"
  - id: oscp-098
    post: tmux
    section: "Tools"
  - id: oscp-099
    post: winpeas
    section: "Tools"
  - id: oscp-100
    post: wpscan
    section: "Tools"
---

The offensive-security body I built preparing for PEN-200 and the OSCP: a repeatable path from the first scan to Domain Admin, and the technique and tool notes it leans on.

Read the methodology first for the decision workflow, then drop into a technique or tool note as a specific target calls for it. Nothing here walks through a named machine; it is the reusable method, not the answers. The methodology grew from paths that actually worked in the labs, so it favours decisions and workflow over exhaustive documentation.
