---
title: "Tunneling and Pivoting"
slug: tunneling-and-pivoting
category: notes
handbook: oscp
tags: ["pivoting"]
draft: false
pubDatetime: 2026-08-01T10:35:17+03:00
modDatetime: 2026-09-13T17:46:18+03:00
description: "Pivoting uses a compromised host as a path into a network the attacker machine has no route to."
---
Pivoting uses a compromised host as a path into a network the attacker machine has no route to. Tunneling carries traffic across that path. In these notes the attacker machine is Kali.

Typical position:

```text
Kali                   Pivot                     Internal target
192.168.45.10  <---->  192.168.45.20
                       10.10.10.5       <---->   10.10.10.20
```

Kali can reach the pivot's first interface but has no route to `10.10.10.0/24`. After an agent runs on the pivot, a tunnel and route make the internal subnet reachable from Kali.

The addresses in this note are examples, not real targets. `192.168.45.0/24` stands for the Kali-side network and `10.10.10.0/24` for the hidden internal one throughout. OSCP internal subnets are not known in advance, so substitute whatever the pivot's `ip route` and `ifconfig` report.

## Recognizing a Pivot

After gaining a shell, check the host's interfaces and routes:

```bash
ip -br addr
ip route
```

On Windows:

```powershell
ipconfig /all
route print
```

A pivot is likely when the compromised host has:

- An interface or route for a subnet that was not visible from Kali.
- A service bound only to another interface or to localhost.
- Access to hosts that Kali cannot reach.

The subnet to tunnel is whichever one the pivot sits on that Kali has no route to. The shell was reached over the pivot interface Kali already reaches, so every other connected subnet is a candidate. Confirm against `ip route` on Kali: the pivot subnet missing from it is the target.

Route the network address, not the pivot's host address. Drop the host bits of the interface address, which the prefix length marks. For a `/24` that means zeroing the last octet, so an interface on `172.16.74.129/24` becomes the route `172.16.74.0/24`. A `/16` zeroes the last two octets, a `/8` the last three.

Record the pivot address, hidden subnet, and expected route before changing anything.

## Traffic Directions

### Kali to an internal service

This is the normal pivot:

```text
Kali tool -> tunnel -> pivot -> internal service
```

Examples include Nmap, SMB clients, WinRM, RDP, SSH, and a browser.

### Internal host back to Kali

A reverse shell from an internal target may not be able to reach Kali directly:

```text
Internal target -> listener on pivot -> tunnel -> Kali listener
```

Ligolo-ng listeners bind a port on the pivot and relay connections back to a port on Kali. The payload uses the pivot's internal IP as its callback address, not Kali's VPN address.

### Pivot localhost to Kali

A service bound to `127.0.0.1` on the pivot is not part of the routed internal subnet. Ligolo-ng maps `240.0.0.1` to the selected agent's localhost, allowing the service to be reached through a separate route.

## Ligolo-ng Model

Ligolo-ng uses two components:

- The proxy runs on Kali and creates a TUN interface.
- The agent runs on the pivot and makes an outbound TLS connection to the proxy.

A TUN interface is a virtual network interface with no hardware behind it. Packets the kernel routes into it are handed to a userspace program instead of being put on a wire, and packets written back in are treated as if they arrived from the network. TUN carries IP packets at layer 3, while TAP carries Ethernet frames at layer 2 and is not used here. This is the same mechanism behind a VPN's `tun0`.

Routing the hidden subnet into that interface therefore gives every packet for it to `ligolo-proxy`. The proxy does not forward those packets to the pivot untouched. It feeds them into a TCP/IP stack running in userspace on Kali, which terminates the connection locally, and the agent then makes an ordinary `connect()` from the pivot. That is why the agent needs no privileges on the pivot, and why raw-packet techniques stop meaning anything: the first handshake completes against Ligolo-ng's own stack, not against the target.

The result behaves more like a VPN route than a SOCKS proxy, so tools do not need proxychains.

### SOCKS proxies and proxychains

SOCKS is a proxy protocol that works per connection rather than per packet. The client opens a TCP connection to the proxy and asks it, in the protocol, to connect to `10.10.10.20:445`. The proxy dials it and relays bytes. The application has to speak SOCKS, which `curl --socks5` and Firefox do and most offensive tooling does not.

proxychains fills that gap with an `LD_PRELOAD` shim that overrides libc's `connect()` and DNS calls, so a dynamically linked binary gets wrapped in the SOCKS handshake without knowing it. The proxy is configured in `/etc/proxychains4.conf` and the tool is run as `proxychains nmap ...`. The shim is also where the problems come from:

- Go and statically linked binaries ignore `LD_PRELOAD` and bypass the proxy silently.
- `sudo` strips `LD_PRELOAD`, so anything run as root escapes the chain.
- There is no ICMP, so `ping` and `nmap -sn` are meaningless.
- DNS is resolved separately and either leaks or breaks.
- Multi-port Nmap runs are slow.

A TUN route is applied by the kernel, so it covers every process without a wrapper. [Chisel](/collections/oscp/chisel) and the `ssh -D` proxy in [SSH Tunnels](/collections/oscp/ssh-tunnels) still produce SOCKS proxies, so proxychains remains worth knowing as a fallback.

### Finding live hosts

Host discovery is better done on the pivot than through the tunnel. The pivot sits on the internal segment at layer 2, so it resolves ARP directly, and ARP is definitive: every live host on a local `/24` has to answer it, firewalled or not. The tunnel only carries layer 3, so ARP and ICMP discovery do not cross it and a Kali-side sweep is reduced to slow TCP connects.

Passive first, since the pivot often already knows its neighbours:

```bash
ip neigh          # or arp -a, the ARP cache
ss -tn            # established connections to internal hosts
cat /etc/hosts    # can name the next host outright
```

Then force ARP across the range and read the cache, which finds hosts that drop ICMP:

```bash
for i in $(seq 1 254); do ping -c1 -W1 10.10.10.$i >/dev/null 2>&1 & done; sleep 3
ip neigh
```

`sleep` rather than a bare `wait` here on purpose. `wait` with no arguments blocks on every background job in the shell, so with the Ligolo agent backgrounded in the same shell it never returns even though the pings finished in about a second. `arp-scan -l -I <iface>` does the same in one command where it is installed. With the live hosts in hand, switch to Kali and scan only those through the tunnel.

### Scanning through the tunnel

Both approaches share the raw-socket limit, so treat scans through the tunnel as TCP connect scans:

```bash
nmap -Pn -n -sT -p- --min-rate 500 10.10.10.20
nmap -Pn -n -sT -sC -sV -p22,80,445 10.10.10.20
```

Find the live hosts before deep-scanning. A full `-Pn` scan of a whole `/24` through the tunnel is the slow case: `-Pn` treats all 254 addresses as alive, so every port on the roughly 252 hosts that do not exist becomes a TCP connect that has to time out, each one relayed through the pivot. ICMP host discovery (`-sn`) does not survive the unprivileged tunnel, so a light TCP top-ports sweep stands in for it, then only responders get the full scan:

```bash
nmap -Pn -n -sT --top-ports 20 --open --max-retries 1 10.10.10.0/24   # locate hosts
nmap -Pn -n -sT -p- --min-rate 1000 --max-retries 1 10.10.10.20       # then deep-scan one
```

Start conservatively. Tunnel latency and the pivot's connection limits can make aggressive scans unreliable, and a `--min-rate` set too high causes dropped probes and retransmits that end up slower. UDP discovery is slower and less dependable, so investigate it only when the target or lab path gives a reason.

## Workflow

1. Enumerate the compromised host's interfaces and routes.
2. Identify the exact hidden subnet. Do not route a larger range than needed.
3. Transfer and start the Ligolo-ng agent.
4. Select the agent on the proxy.
5. Create a TUN interface and add the hidden subnet route.
6. Start the tunnel.
7. Test one known host and port before scanning the subnet.
8. Enumerate internal targets with TCP connect scans.
9. Add a Ligolo-ng listener if an internal reverse connection cannot reach Kali.
10. Remove listeners and stop the tunnel when finished.

Commands and installation are in [Ligolo-ng](/collections/oscp/ligolo-ng). A self-built two-network lab with one dual-homed pivot is enough to practice this workflow end to end.

## Verify the Path Before Trusting It

A pivot fails silently more often than loudly: the route persists, tools keep running, and nothing prints an error while packets vanish into a dead tunnel. Walk the path from Kali outward, and each step localizes the break to one hop:

1. **Interface**: `ip addr show pivot1` exists, is UP, and has an address.
2. **Route**: `ip route show dev pivot1` contains the internal subnet. A missing or wrong-prefix route blackholes traffic in the kernel before the tunnel is ever involved.
3. **Agent session**: the proxy console lists the agent under `session`. An agent that reconnected appears as a *new* session while the tunnel stays bound to the dead one, so select the new session and `tunnel_start` again. This is the most common silent death.
4. **End-to-end TCP to a known-open port**: `nc -vz -w 3 TARGET <port>`. Only `succeeded!` counts, and the port must be one seen open on that host before: a timeout against a port that answered an hour ago is a tunnel verdict, not a target verdict. `-w 3` caps the wait, because against a dead route an untimed `nc` hangs for minutes and poisons the whole check.
5. **Scope**: every internal host failing means the tunnel broke; one host failing while its neighbours answer means that host changed.
6. **Isolate the hop**: from the pivot's own shell, test the same port to the target (`Test-NetConnection TARGET -Port 445`). Pivot-to-target working while Kali-to-target fails puts the break in the tunnel leg, not the target.

The habit matters more than the commands. Ten seconds of `nc -vz -w 3` against a known-open port before launching any tool batch saves the ten minutes a hung tool costs, and a hung tool is indistinguishable from a filtered port unless the path is already known good.

## Troubleshooting

### The agent does not connect

- Confirm the proxy is listening on TCP `11601`.
- Confirm the pivot can reach Kali on that address and port.
- Use Kali's VPN address for an OSCP lab, not a NAT-only or loopback address.
- Confirm the proxy and agent versions are compatible.

### The agent connects but the subnet is unreachable

- Confirm the correct agent is selected.
- Check that the tunnel is running on the intended TUN interface.
- Check the route with `ip route`.
- Ensure the route is the network address, such as `10.10.10.0/24`, not a single pivot address.
- Check for an overlapping local, VPN, or Docker route.
- Test a known TCP port with `nc -vz TARGET PORT` before blaming Nmap.

### Nmap reports misleading results

Use `-Pn -sT`. SYN scans and other raw-packet techniques do not pass through an unprivileged Ligolo-ng agent in the usual way.

### A reverse shell does not arrive

- Start the Kali listener first.
- Confirm the Ligolo-ng listener is bound on the pivot.
- Make the payload connect to the pivot's internal IP and Ligolo listener port.
- Make the listener relay to the actual port used by the Kali catcher.
