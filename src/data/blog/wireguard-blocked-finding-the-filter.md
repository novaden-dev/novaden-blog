---
author: Kayra
pubDatetime: 2026-10-17T12:00:00Z
title: "WireGuard Blocked in One Country: Finding the Filter and Tunnelling Around It"
slug: wireguard-blocked-finding-the-filter
featured: false
draft: false
tags: ["networking"]
category: journal
format: writeup
description: "Why the team VPN failed for developers in one country: the checks that ruled out the server, a reproduction through a relay inside that country, packet tests showing the first packet of a UDP flow decides whether it is dropped, and the fix of carrying WireGuard inside TLS on port 443 with wstunnel."
---

At work, our internal tools (Grafana, PostgreSQL, a few admin pages) run on a single dedicated server and are not exposed to the internet. Developers reach them over WireGuard: they import a profile, activate it, and get a route to the server's private address, `10.99.0.1`.

Developers in one country started reporting that the VPN did not work. Some had never connected once. One had connected the night before and then stopped. Teammates in other countries had no problems. I wanted to reproduce the failure myself before changing anything.

## What "Active" meant

The first screenshot from an affected developer showed the tunnel as **Active** in the WireGuard client. Below that, the counters showed data sent, **0 bytes received**, and no "Latest handshake" line at all.

In WireGuard, "Active" only means the tunnel interface is up on the laptop. A working tunnel also needs a completed handshake with the server. Their client log showed the handshake retrying:

```text
Sending handshake initiation to peer 1 (203.0.113.10:51820)
Handshake for peer 1 (203.0.113.10:51820) did not complete after 5 seconds, retrying (try 9)
Sending handshake initiation to peer 1 (203.0.113.10:51820)
Handshake for peer 1 (203.0.113.10:51820) did not complete after 5 seconds, retrying (try 10)
```

The log had 995 handshake attempts and no response recorded. The handshake never completed, so no traffic reached Grafana or the database.

There were three possible causes:

- The initiation packet never reached the server.
- The server sent a response, and the response never reached the client.
- A packet arrived but failed validation (wrong key, wrong profile).

## Ruling out the server

I checked the server side first.

```bash
# Interface, peers, last handshake per peer, transfer counters
sudo wg show wg0

# Is the service up?
systemctl is-active wg-quick@wg0

# Does the firewall allow UDP 51820?
sudo nft list ruleset | grep 51820
```

Everything looked normal. The firewall allowed UDP 51820. All 13 peers had distinct public keys and distinct addresses, so two people were not sharing one identity. The affected developer's public key and address matched what was on the server. Grafana and PostgreSQL responded on their private addresses from the server itself. Teammates in other countries had recent handshakes and live traffic.

The server also had no handshake recorded for the developer who had never connected, and an old one (late the previous evening) for the developer whose tunnel had worked and then stopped. That matched what they were telling me, and every affected developer was in the same country.

At that point I suspected filtering somewhere on that country's network path. I wanted to confirm it before picking a fix, so I needed a test point inside the country.

## Getting a test point inside the country

I am not in that country, and testing from my own connection only proves that my own connection works. Commercial VPNs that list a location in the country do not always help either: some of those locations are hosted in another country, so the traffic never crosses the country's networks.

I used two other sources instead.

**Globalping.** [Globalping](https://globalping.io/) runs volunteer probes on real ISP networks and lists some in that country. A probe on one of the country's ISPs reached the server on TCP 443, and test UDP packets reached port 51820. So the server's address was not blocked outright, and plain UDP to the VPN port was not blocked either. Globalping cannot run a WireGuard handshake, so this only ruled out a full block.

**A VPN Gate relay.** [VPN Gate](https://www.vpngate.net/) lists volunteer-run OpenVPN servers, and one of them sat on an ISP in that country (a different network from the Globalping probe). Traffic sent through it reaches the internet from an address in that country. I connected to it from a throwaway container on the server, so nothing on the host itself changed:

```bash
# Resource-limited container with its own network namespace and a TUN device
docker run --rm -d --name relay-vpn-test \
  --cpus=0.5 --memory=256m --pids-limit=128 \
  --cap-add=NET_ADMIN --device=/dev/net/tun \
  debian:bookworm-slim sleep 900

docker exec relay-vpn-test sh -c \
  'apt-get update -qq && apt-get install -y -qq openvpn iproute2 wireguard-tools curl python3'
```

Inside the container, OpenVPN connected to the relay with `route-nopull`, so the relay did not take over the container's default route. Then I added one route by hand: traffic to the VPN server's public address goes through the relay, and everything else goes direct.

```bash
openvpn --config relay.ovpn --daemon --log openvpn.log
ip route add 203.0.113.10/32 dev tun0
ip route get 203.0.113.10    # should say "dev tun0"
```

From the server's point of view, packets from the test container now arrived from an IP in that country. For the WireGuard identity I used an unused profile of my own, so no developer's key ended up in a test environment.

## Reproducing the failure

The test script ran the same WireGuard profile twice:

1. Direct, without the relay route. This only checks that the profile works, since the container runs on the server itself. The handshake completed and Grafana's health endpoint (`http://10.99.0.1:3000/api/health`) returned HTTP 200.
2. Through the relay, with the relay route added. Over five minutes there were zero successful handshakes and 23 failed health checks. TCP 443 checks to the same server, sent through the same relay during the same five minutes, all succeeded.

The key, server and port were the same in both runs, and only the network path changed. I could now reproduce the failure.

## Narrowing it down to the packet

Globalping had already shown that plain UDP reached port 51820. To find out which packets were dropped, I sent hand-crafted packets through the relay and captured what arrived on the server.

The [protocol documentation](https://www.wireguard.com/protocol/) gives the layout of a WireGuard handshake initiation. It is always 148 bytes. It starts with the message type `1` followed by three zero bytes (`01 00 00 00`), and it ends with a 16-byte field called `mac2` that is all zeros unless the server is under load. The 128 bytes in between (a random sender index, an ephemeral public key, two encrypted fields and a MAC) look random. A filter does not need to decrypt anything: a fixed four-byte header, a fixed length, and sixteen zero bytes at the end are enough to classify the packet.

On the server, a capture filter that shows only packets starting with the WireGuard initiation header looks like this (`udp[8:4]` is the first four bytes of the UDP payload):

```bash
sudo tcpdump -ni any 'udp dst port 51820 and udp[8:4] = 0x01000000'
```

I took a real initiation packet that the test client had just sent, changed one thing at a time, and sent each version from a new source port through the relay:

| Packet sent through the relay | Arrived at the server |
|---|---|
| Real handshake initiation, unchanged | No |
| Same packet, unchanged, sent again | No |
| Random bytes with the WireGuard header and an all-zero 16-byte tail | No |
| Real initiation with the first four bytes replaced | Yes |
| Real initiation with the 16-byte tail replaced by random bytes | Yes |
| Real initiation with one of the reserved header bytes set to 1 | Yes |
| 148 bytes starting with a text label, rest random | Yes |

Packets that looked like a real WireGuard initiation (the header plus the zero tail) were dropped. Any packet that broke that pattern got through, even when the rest was a byte-for-byte copy of a real handshake. The server never received the dropped packets, so they were dropped on the way in, before the server had anything to respond to.

### The first packet decides the flow

I then sent a short sequence of packets on a single UDP socket (one source port), in two different orders:

```python
import os, socket

SERVER = ("203.0.113.10", 51820)

def wg_like():
    # WireGuard initiation shape: type 1, three zero bytes, 128 random bytes, 16 zero bytes
    return b"\x01\x00\x00\x00" + os.urandom(128) + bytes(16)

def plain():
    # Same length, header changed so it no longer matches
    return b"TEST" + os.urandom(128) + bytes(16)

for name, sequence in [("wg-first", [wg_like, plain, wg_like, plain]),
                       ("plain-first", [plain, wg_like, plain, wg_like])]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("0.0.0.0", 0))  # new source port per scenario
        for make in sequence:
            s.sendto(make(), SERVER)
```

| Scenario | What arrived |
|---|---|
| Flow starts with a WireGuard-shaped packet | Nothing. The plain packets sent afterwards on the same source port were dropped too. |
| Flow starts with a plain packet | Everything, including the WireGuard-shaped packets that came later. |

The filter is stateful: it looks at the first packet of a new UDP flow (source address and port to destination address and port), decides whether that flow is WireGuard, and applies the decision to every packet in the flow after that. A flow that opens with a handshake gets blocked as a whole. A flow that opens with anything else gets marked as harmless, and later WireGuard packets in it pass.

### Confirming it with a real tunnel

If that was right, a real WireGuard tunnel should work through the relay as long as some other packet goes first from the same source port. So I sent one plain UDP packet from port 39001 to the server, then brought up WireGuard bound to that same port:

```bash
# Inside the test container's network namespace
python3 -c 'import socket,os; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("0.0.0.0", 39001)); s.sendto(b"prelude " + os.urandom(80), ("203.0.113.10", 51820))'

ip link add wgtest type wireguard
wg setconf wgtest wg-test.conf
wg set wgtest listen-port 39001
ip address add 10.99.0.11/32 dev wgtest
ip link set wgtest mtu 1280 up
ip route add 10.99.0.1/32 dev wgtest
curl http://10.99.0.1:3000/api/health
```

The handshake completed and the health check returned `"database": "ok"`. This was the same profile that had failed for five straight minutes a few minutes earlier. I left it running past WireGuard's scheduled rekey (it starts a new handshake every two minutes or so), and the health checks kept passing after it.

### Why it sometimes worked

The tests do not tell me what happened to each developer individually, and I never captured the moment the one working tunnel stopped. The behaviour above can explain both reports, though. If the filter's decision depends on the first packet of a flow, then the result can change with the network path, with how the developer's router maps ports (a new flow starts each time that mapping changes), and with which filtering box a given connection passes through. Some developers would never connect. Some would connect, and lose the tunnel later when a new flow started with a handshake.

I also do not know where the filtering device is. It could be on the relay's ISP, on a transit network, or somewhere else on the route.

## The fix: WireGuard inside TLS on port 443

Sending a plain packet first was a diagnostic. Shipping it as the fix would mean depending on one filter's current behaviour, and the filter can change at any time. I looked at four other options:

| Option | Why I did not pick it |
|---|---|
| AmneziaWG (WireGuard fork with junk packets and changed headers) | Still plain UDP on the wire, so it depends on UDP staying open from that country. The client-only mode, which sends junk packets before each handshake, works with a standard WireGuard server but depends on the filter behaving the way it did in my tests. Changing the headers needs an AmneziaWG server as well. Both need a different client app. |
| Tailscale | It does use WireGuard, and its fallback relays (DERP) carry WireGuard inside TLS on 443, which would work here. It adds a per-user subscription, and access to internal tools would depend on Tailscale's coordination servers being reachable. |
| SSH tunnels to each service | Works, but every developer has to set up a forward per service, and SSH can be filtered too. |
| WireGuard over a TLS WebSocket with [wstunnel](https://github.com/erebe/wstunnel) | Keeps every existing key, address and permission. On the wire it is HTTPS to a normal hostname on TCP 443. |

I went with wstunnel. The path looks like this:

```text
WireGuard client  --UDP-->  wstunnel client (127.0.0.1:51821, on the laptop)
                            |
                            |  TLS WebSocket over TCP 443
                            v
                 Caddy (vpn.example.com:443, existing reverse proxy)
                            |
                            v
                 wstunnel server (container)  --UDP-->  WireGuard (10.99.0.1:51820)
```

WireGuard still does all the authentication and encryption. wstunnel only changes how the WireGuard packets cross the internet: they travel as WebSocket frames inside a TLS connection. An observer on the path sees a TLS session to `vpn.example.com`, and the WireGuard header pattern never appears in a UDP packet.

### Server side

The wstunnel server runs as a container with no published ports. Caddy already terminates TLS on 443 for the other sites, so it gets one more hostname and proxies WebSocket upgrades on a fixed path to the container:

```yaml
services:
  vpn-transport:
    image: local/wstunnel:11.0.0   # FROM scratch + the release binary, runs as 65532:65532
    restart: unless-stopped
    command:
      - server
      - --restrict-config
      - /etc/wstunnel/restrictions.yaml
      - --websocket-ping-frequency
      - 20s
      - ws://0.0.0.0:8080
    volumes:
      - ./restrictions.yaml:/etc/wstunnel/restrictions.yaml:ro
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    mem_limit: 128m
    networks: [edge-vpn]
networks:
  edge-vpn:
    external: true
```

By default a wstunnel server forwards to whatever destination the client asks for, so it acts as an open proxy. The restrictions file limits it to one destination: UDP to WireGuard's own listener. Reverse tunnels are denied because none are listed.

```yaml
restrictions:
  - name: wireguard-only
    match:
      - !PathPrefix "^vpn$"
    allow:
      - !Tunnel
        protocol: [Udp]
        port: [51820]
        host: '^10\.99\.0\.1$'
        cidr: [10.99.0.1/32]
```

So anyone who reaches the endpoint without a valid WireGuard key can only send packets to a WireGuard port that discards them.

The Caddy site block for the new hostname:

```text
vpn.example.com {
	@transport {
		method GET
		path /vpn/*
		header Upgrade websocket
	}
	handle @transport {
		reverse_proxy vpn-transport:8080 {
			# Keep open VPN streams alive across config reloads for other sites
			stream_close_delay 24h
		}
	}
	handle /healthz {
		respond "ok" 200
	}
	handle {
		respond 404
	}
}
```

Without `stream_close_delay`, every Caddy reload (for example after adding a site) closes all WebSocket connections, and every developer's tunnel drops at the same moment.

### Client side

Each affected developer gets a second WireGuard profile. It is a copy of their normal profile with three changes: `Endpoint` points at the local wstunnel client, the MTU is set to 1280 (a conservative value that avoids fragmentation on paths you do not control), and `AllowedIPs` stays limited to the server's private address so normal browsing does not use the tunnel.

```ini
[Interface]
PrivateKey = <their existing key>
Address = 10.99.0.23/32
MTU = 1280

[Peer]
PublicKey = <server key>
Endpoint = 127.0.0.1:51821
AllowedIPs = 10.99.0.1/32
PersistentKeepalive = 25
```

Then they start the wstunnel client and leave it running:

```bash
wstunnel client \
  --tls-verify-certificate \
  --http-upgrade-path-prefix vpn \
  --websocket-ping-frequency 20s \
  --connection-retry-max-backoff 5s \
  -L 'udp://127.0.0.1:51821:10.99.0.1:51820?timeout_sec=0' \
  wss://vpn.example.com
```

What the flags do:

- `--tls-verify-certificate`: wstunnel skips certificate verification by default. Without this flag, anyone able to intercept the connection could present their own certificate.
- `-L 'udp://127.0.0.1:51821:10.99.0.1:51820?timeout_sec=0'`: listen for UDP locally on 51821 and ask the server to forward it to 10.99.0.1:51820. `timeout_sec=0` keeps the UDP association open while it is idle, so a quiet tunnel does not get torn down between keepalives.
- `--connection-retry-max-backoff 5s`: if the TLS connection drops, reconnect within five seconds at most instead of backing off for longer.

Then they activate the new profile in WireGuard and open Grafana.

### Testing it

The relays in that country were offline the day I finished the fix, so I tested the failure condition directly. I blocked the test client's direct UDP route to the server: plain WireGuard failed, and the TLS profile still reached Grafana and PostgreSQL. It passed 24 sustained health checks. It recovered by itself after I restarted the client helper, and again after I restarted the server container. With certificate verification on, it refused to connect to an endpoint with an untrusted certificate. I also tried to use the server as a proxy to other hosts and ports and to open reverse tunnels, and the restrictions blocked all of it.

After that, the affected developers switched to the TLS profile and tested it from their own connections. It connected and reached Grafana and the database.

## What it costs

- **TCP inside TCP.** The tunnel now runs over TCP. When a packet is lost, TCP holds back everything behind it until the retransmission arrives, so on a lossy connection the whole tunnel stalls for a moment. Small requests such as dashboard loads and short queries suffer less than large exports, which will be slower than over direct WireGuard. I have not measured by how much.
- **More parts that can break.** The tunnel now depends on DNS for the hostname, the TLS certificate, Caddy, the wstunnel container and a helper process on each laptop. A health check on `https://vpn.example.com/healthz` only proves DNS, TLS and Caddy. A full check is a handshake plus a request to `10.99.0.1`.
- **It can still be blocked.** TLS on 443 looks like ordinary HTTPS, but a network can block the hostname, the IP, or WebSocket upgrades.
- **No automatic switch.** Unaffected developers keep the direct profile, and affected developers use the TLS one. Nothing selects between them automatically.

## Tunnelling as a real fix

Tunnelling usually comes up in security writing as a way to get traffic past a firewall, with SSH port forwards or DNS tunnels. Here it solved an ordinary access problem. The filter recognised WireGuard packets by their header and zero tail, so the fix carries those same packets inside a TLS connection, which the network already allows. WireGuard still handles authentication and encryption, and the TLS layer only changes what the traffic looks like on the wire. The same approach works for other protocols that a network blocks by pattern, as long as HTTPS to your hostname gets through.
