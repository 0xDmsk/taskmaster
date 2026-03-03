"""
Runtime command validator for macOS container platform constraints.

Detects commands that will fail or produce unreliable results due to
the Linux VM boundary on macOS, and suggests working alternatives.
"""

import re

# Each rule: (pattern, severity, message, suggestion)
# severity: "block" = reject the command, "warn" = allow but return warning
CONSTRAINT_RULES = [
    # --- Nmap raw-socket scans ---
    (
        r"\bnmap\b.*\s-sS\b",
        "block",
        "SYN scan (-sS) requires raw sockets and will fail or produce unreliable results in the macOS container VM.",
        "Replace -sS with -sT (TCP connect scan). Example: nmap -sT -sV target",
    ),
    (
        r"\bnmap\b.*\s-sU\b",
        "block",
        "UDP scan (-sU) is unreliable through the macOS VM's double NAT layer.",
        "Use service-specific tools instead: dig (DNS), snmpwalk (SNMP), or skip UDP scanning.",
    ),
    (
        r"\bnmap\b.*\s-sA\b",
        "block",
        "ACK scan (-sA) requires raw sockets and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) for port discovery.",
    ),
    (
        r"\bnmap\b.*\s-sY\b",
        "block",
        "SCTP INIT scan (-sY) requires raw sockets and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) instead.",
    ),
    (
        r"\bnmap\b.*\s-sZ\b",
        "block",
        "SCTP COOKIE-ECHO scan (-sZ) requires raw sockets and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) instead.",
    ),
    (
        r"\bnmap\b.*\s-sI\b",
        "block",
        "Idle/zombie scan (-sI) requires raw sockets for IP ID probing and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) instead.",
    ),
    (
        r"\bnmap\b.*\s-sF\b",
        "block",
        "FIN scan (-sF) requires raw sockets and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) instead.",
    ),
    (
        r"\bnmap\b.*\s-sX\b",
        "block",
        "Xmas scan (-sX) requires raw sockets and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) instead.",
    ),
    (
        r"\bnmap\b.*\s-sN\b",
        "block",
        "NULL scan (-sN) requires raw sockets and will not work in the macOS container VM.",
        "Use -sT (TCP connect scan) instead.",
    ),
    # --- Nmap OS detection ---
    (
        r"\bnmap\b.*\s-O\b",
        "block",
        "OS fingerprinting (-O) requires raw sockets for TCP/IP stack analysis and will not work in the macOS container VM.",
        "Infer OS from service banners instead: nmap -sT -sV --script=smb-os-discovery,http-server-header target",
    ),
    # --- Nmap traceroute ---
    (
        r"\bnmap\b.*\s--traceroute\b",
        "warn",
        "Traceroute (--traceroute) shows hops inside the VM, not the real network path. Results will be misleading.",
        "Use standard traceroute/tracepath from outside the container if real network hops are needed.",
    ),
    # --- ARP scanning ---
    (
        r"\barp-scan\b",
        "block",
        "ARP scanning can only see the VM's virtual bridge network, not the real LAN.",
        "Use nmap -sT -sn for host discovery, or use DNS-based discovery.",
    ),
    (
        r"\bnmap\b.*\s-PR\b",
        "block",
        "ARP ping (-PR) can only see the VM's virtual bridge network, not the real LAN.",
        "Use nmap -sT -sn for host discovery.",
    ),
    # --- Raw packet tools ---
    (
        r"\bscapy\b",
        "warn",
        "Scapy sends raw packets to the VM's virtual NIC, not the real network interface.",
        "Use TCP-based tools (requests, impacket) for reliable results.",
    ),
    (
        r"\bhping3?\b",
        "block",
        "hping requires raw sockets and will not produce reliable results in the macOS container VM.",
        "Use nmap -sT or curl for connectivity testing.",
    ),
    # --- Sniffing ---
    (
        r"\btcpdump\b",
        "warn",
        "tcpdump will capture traffic on the VM's virtual interface, not real network traffic.",
        "This is only useful for debugging container-to-target connections, not for network sniffing.",
    ),
    (
        r"\btshark\b",
        "warn",
        "tshark will capture traffic on the VM's virtual interface, not real network traffic.",
        "This is only useful for debugging container-to-target connections, not for network sniffing.",
    ),
    # --- Nmap without -sT (implicit SYN scan) ---
    (
        r"\bnmap\b(?!.*\s-s[TVCn])",
        "warn",
        "Nmap without an explicit scan type defaults to -sS (SYN scan) when run as root, which requires raw sockets.",
        "Always specify -sT explicitly. Example: nmap -sT -sV target",
    ),
]


def validate_command(command):
    """
    Validate a command against platform constraint rules.

    Returns:
        dict with keys:
        - "allowed": bool
        - "violations": list of dicts with "severity", "message", "suggestion"
    """
    violations = []

    for pattern, severity, message, suggestion in CONSTRAINT_RULES:
        if re.search(pattern, command):
            violations.append({
                "severity": severity,
                "message": message,
                "suggestion": suggestion,
            })

    has_block = any(v["severity"] == "block" for v in violations)

    return {
        "allowed": not has_block,
        "violations": violations,
    }
