# Generic Agent Mission Template

When spawning a new agent using `spawn_agent`, Gemini should use the following structured template for the `mission` argument. This ensures consistency across the fleet and allows Taskmaster to effectively track the purpose of each container.

## Mission Structure

```yaml
ROLE: "[recon | enumeration | exploitation | post_exploitation]"
TARGET: "[Target IP/Domain]"
OBJECTIVE: "[Specific goal, e.g., Identify all hidden web directories]"
PHASE_RESTRICTION: "[The specific security phase this agent is locked to]"
STRATEGY: "[e.g., Minimal footprint | Intensive | Automated | Custom Python Analysis]"
SUCCESS_CRITERIA: "[What defines the completion of this agent's mission]"
PLATFORM_CONSTRAINTS: "macOS VM — use nmap -sT only, no raw-socket scans (-sS/-sU/-O), no arp-scan/hping/scapy. HTTP-based tools work fine."
```

## Usage Example

```json
{
  "target": "10.0.0.15",
  "mission": "ROLE: enumeration
TARGET: 10.0.0.15
OBJECTIVE: Find subdomains and vhosts
PHASE_RESTRICTION: enumeration
STRATEGY: Intensive ffuf and gobuster scans
PLATFORM_CONSTRAINTS: macOS VM — nmap -sT only, no raw-socket scans, HTTP tools OK
SUCCESS_CRITERIA: List of verified subdomains"
}
```

## Benefits
1. **Traceability**: The mission is printed in the agent's startup logs, making it easy to audit what `kali-agent-7a1b2` was intended to do.
2. **Specialization**: Gemini can use this template to "brain-wash" the universal agent into a specialized role.
3. **Task Alignment**: Ensures that the `request_security_action` calls made later align with the agent's initialized mission.
