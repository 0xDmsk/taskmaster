# Platform Constraints: macOS Container Environment

Taskmaster runs Kali Linux containers inside a Linux VM on macOS (Lima/Colima/Docker Desktop). This VM boundary imposes hard limitations on what security tools can and cannot do. **You MUST consult this before planning any scan.**

## The Core Problem

On macOS, containers run inside a lightweight Linux VM — not on the host directly. This means:
- `--network=host` shares the **VM's** virtual NIC, not the Mac's physical interface
- `CAP_NET_RAW` / `--privileged` only grant raw socket access to the VM's virtual network
- The container can reach external targets via NAT, but cannot see or interact with the real Layer 2/3 network

## What WILL NOT Work (or produces unreliable results)

| Technique | Why it fails | Example |
|---|---|---|
| **SYN scan** (`nmap -sS`) | Requires raw sockets; falls back to connect scan silently or errors out | `nmap -sS target` |
| **UDP scan** (`nmap -sU`) | Unreliable through double NAT (container → VM → host → network) | `nmap -sU target` |
| **OS fingerprinting** (`nmap -O`) | Requires raw sockets for TCP/IP stack analysis | `nmap -O target` |
| **ACK scan** (`nmap -sA`) | Raw socket dependent | `nmap -sA target` |
| **SCTP scans** (`nmap -sY`, `-sZ`) | Raw socket dependent | `nmap -sY target` |
| **Idle/zombie scan** (`nmap -sI`) | Requires IP ID probing via raw sockets | `nmap -sI zombie target` |
| **ARP scanning** | Can only see the VM's virtual bridge, not the real LAN | `arp-scan -l`, `nmap -PR` |
| **ICMP-only host discovery** | Unreliable; ICMP is NATted through the VM | `nmap -sn -PE target` |
| **Raw packet crafting** | Packets go to the VM's virtual NIC | `scapy`, `hping3` |
| **Network sniffing** | Captures VM internal traffic, not real network traffic | `tcpdump`, `tshark` |
| **MAC spoofing** | Affects the VM's virtual MAC, not the physical adapter | `macchanger` |
| **Traceroute** (`nmap --traceroute`) | Shows hops inside the VM, not real network path | `nmap --traceroute target` |

## What WORKS Reliably

| Technique | Why it works | Example |
|---|---|---|
| **TCP connect scan** (`nmap -sT`) | Uses standard TCP sockets, NATted correctly | `nmap -sT -p- target` |
| **Service detection** (`nmap -sV`) | Uses connect-based banner grabbing | `nmap -sT -sV target` |
| **NSE scripts** (`nmap -sC`, `--script`) | Most scripts use TCP connections | `nmap -sT -sC target` |
| **Web scanning** | All HTTP-based, works through NAT | `ffuf`, `gobuster`, `nikto`, `sqlmap` |
| **DNS tools** | Standard UDP/TCP DNS queries work fine | `dig`, `nslookup`, `host`, `dnsrecon` |
| **Subdomain enumeration** | DNS/HTTP based | `subfinder`, skills/subdomain.py |
| **SSL/TLS scanning** | TCP-based | `sslscan`, `testssl.sh`, `nmap --script ssl-*` |
| **HTTP requests** | Standard TCP | `curl`, `wget`, `python3 requests` |
| **Cloud tool APIs** | HTTPS API calls | `aws`, `gcloud`, `kubectl`, `helm` |
| **Credential testing** | TCP-based protocols | `hydra` (against TCP services), `impacket` |
| **SQL injection** | HTTP-based | `sqlmap` |
| **Directory brute-forcing** | HTTP-based | `ffuf`, `gobuster`, `dirb` |
| **SMB/LDAP enumeration** | TCP-based | `impacket` tools, `enum4linux` |

## Mandatory Nmap Usage Rules

**ALWAYS** use `-sT` (TCP connect scan) instead of `-sS` (SYN scan). Example:
```bash
# WRONG — will fail or produce unreliable results
nmap -sS -sV -p 1-1000 target

# CORRECT — reliable through the VM
nmap -sT -sV -p 1-1000 target
```

**NEVER** combine `-O` (OS detection) with scans. If OS identification is needed, infer from service banners (`-sV`) and NSE scripts instead:
```bash
# WRONG
nmap -O target

# CORRECT alternative
nmap -sT -sV --script=smb-os-discovery,http-server-header target
```

**AVOID** `-sU` for UDP scanning. If UDP service discovery is critical, use service-specific tools:
```bash
# WRONG — unreliable
nmap -sU target

# CORRECT alternatives
dig @target version.bind chaos txt    # DNS
snmpwalk -v2c -c public target        # SNMP
```

## When Planning an Assessment

1. **Reconnaissance**: Use DNS, HTTP, and connect-based scanning only
2. **Enumeration**: Rely on `-sT -sV -sC` for port/service enumeration
3. **Exploitation**: HTTP-based exploits (SQLi, XSS, RCE) work fine; raw-socket exploits do not
4. **Post-exploitation**: If you have a shell, the target's own network stack has no VM limitation
