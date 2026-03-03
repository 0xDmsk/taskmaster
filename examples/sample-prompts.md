# Sample Prompts for Taskmaster

Example prompts to use with Gemini CLI or other MCP clients when working with Taskmaster.

## 🎯 Initial Context Setup

Before starting an assessment, provide this context to your AI agent:

```
I'm using Taskmaster, an agentic security orchestration platform.
Please read the GEMINI.md file for operational guidelines.

Key points:
- Use request_security_action to queue tasks
- Use spawn_agent to create execution containers
- Follow phase progression: reconnaissance -> enumeration -> exploitation
- Always provide detailed justification for audit trails
- Use structured action_type: "skill" when possible for better data
```

## 🔍 Reconnaissance Phase

### Basic Network Scan

```
Perform reconnaissance on target 192.168.1.100 using nmap to identify
open ports and running services. This is an authorized penetration test
of our internal infrastructure.
```

### Subdomain Enumeration

```
Execute subdomain enumeration on target example.com using the subdomain
skill. This is for an authorized security assessment with documented scope.
```

### Web Technology Detection

```
Analyze target https://app.example.com using the web reconnaissance skill
to identify technologies, frameworks, and potential attack surface.
```

## 🔬 Enumeration Phase

### Web Directory Bruteforcing

```
After completing reconnaissance on https://app.example.com, enumerate
web directories and endpoints using ffuf with common wordlists.
Target shows a web application on port 443.
```

### Service Version Detection

```
Following the initial port scan of 192.168.1.100, perform detailed service
version detection on ports 22, 80, and 443 to identify potential vulnerabilities.
```

### Cloud Asset Discovery

```
Execute cloud audit skill for target organization "example-corp" to enumerate
AWS resources and identify misconfigurations. Using provided read-only credentials.
```

## 🎯 Exploitation Phase

### Vulnerability Testing

```
Based on enumeration results showing outdated Apache version, test for known
vulnerabilities using appropriate tools. This is an authorized test with proper
scope and emergency contacts defined.
```

### Credential Testing

```
Test discovered credentials against SSH service on 192.168.1.100:22.
Credentials were found in publicly exposed GitHub repository and have been
reported to the client.
```

## 📊 Reporting Phase

### Generate Report

```
Review all completed executions and generate a comprehensive assessment report.
Include findings, evidence, and recommendations for each discovered vulnerability.
```

### Analyze Results

```
Analyze the structured data from all completed skill executions and identify
the most critical findings. Prioritize by severity and exploitability.
```

## 🔄 Workflow Examples

### Complete Assessment Workflow

```
I need to perform a complete security assessment of target 192.168.1.0/24:

1. Start with passive reconnaissance (DNS, whois, public data)
2. Perform active network scanning (nmap)
3. Enumerate discovered services
4. Test for common vulnerabilities
5. Generate a detailed report

This is an authorized penetration test. Client: Acme Corp, Authorization: PT-2026-001
```

### Focused Web Application Test

```
Conduct a focused web application security assessment of https://staging.example.com:

1. Technology fingerprinting
2. Directory enumeration
3. Parameter fuzzing
4. Authentication testing
5. Session management review

Authorization: Written consent from CTO, Scope: Staging environment only
```

### Cloud Security Audit

```
Perform a cloud security audit for AWS account 123456789012:

1. IAM policy review
2. S3 bucket configuration audit
3. EC2 instance security group analysis
4. CloudTrail log review
5. Compliance check against CIS benchmarks

Authorization: Internal security audit, Read-only access granted
```

## 🛠️ Skill-Specific Prompts

### Using Subdomain Skill

```
Use the subdomain.SubdomainSkill to find all subdomains for target.com.
Run both passive (crt.sh) and active (gobuster) enumeration methods.
Save results to loot for further analysis.
```

### Using Cloud Audit Skill

```
Execute cloud.CloudAuditSkill for AWS with the following parameters:
- Region: us-east-1
- Services: IAM, S3, EC2
- Check for: Public buckets, overly permissive IAM policies, security group issues
```

### Using Web Recon Skill

```
Run web.WebReconSkill on https://app.example.com to:
- Identify web technologies (Wappalyzer)
- Detect web server and frameworks
- Check for common vulnerabilities
- Enumerate interesting endpoints
```

### Using Takeover Skill

```
Use takeover.TakeoverSkill to check all discovered subdomains for
potential subdomain takeover vulnerabilities. Check against major
cloud providers (AWS, Azure, GCP, GitHub Pages, etc.)
```

## 🎓 Training Scenarios

### CTF Challenge

```
I'm working on a Capture The Flag challenge at ctf.example.com:8080.
Help me enumerate the application, find vulnerabilities, and capture flags.
This is a sanctioned CTF competition.
```

### Vulnerable VM Practice

```
I'm practicing on a deliberately vulnerable VM (Metasploitable3) at 192.168.56.101.
Walk me through a complete penetration test from reconnaissance to exploitation.
```

## ⚠️ Important Reminders

When using these prompts, always:

1. **Verify Authorization**: Ensure you have written permission to test
2. **Define Scope**: Clearly specify what's in and out of scope
3. **Emergency Contacts**: Have contact info for system owners
4. **Justification**: Provide detailed reasoning for audit trails
5. **Data Handling**: Specify how to handle discovered credentials/data

## 🔄 Multi-Agent Workflows

### Parallel Reconnaissance

```
Spawn multiple agents to perform parallel reconnaissance on different targets:
- Agent 1: Network scan of 192.168.1.0/24
- Agent 2: Subdomain enumeration of example.com
- Agent 3: Cloud asset discovery for AWS account

Coordinate results and identify relationships between findings.
```

### Progressive Enumeration

```
Based on the initial nmap scan showing ports 22, 80, 443, 3306:
1. Spawn agent for web enumeration (ports 80, 443)
2. Spawn agent for SSH analysis (port 22)
3. Spawn agent for MySQL enumeration (port 3306)

Each agent should work independently and report findings.
```

## 📝 Custom Skill Examples

### Creating a New Skill

```
I need a custom skill for testing API endpoints. Create a new skill that:
- Takes a list of API endpoints
- Tests authentication mechanisms
- Checks for rate limiting
- Validates input sanitization
- Outputs structured JSON results

Save it to skills/api_test.py following the TEMPLATE.md pattern.
```

### Extending Existing Skill

```
Extend the web.WebReconSkill to include additional checks:
- Check for security headers (CSP, HSTS, etc.)
- Test for clickjacking protection
- Validate SSL/TLS configuration
- Check for information disclosure in error messages
```

## 🎯 Real-World Scenarios

### Bug Bounty Preparation

```
I'm starting a bug bounty on target.com. Help me:
1. Gather all public information (ASN, domains, subdomains)
2. Map the attack surface
3. Identify interesting targets (admin panels, APIs, old versions)
4. Prioritize based on potential impact
```

### Incident Response

```
We detected suspicious activity on server 10.0.0.50. Help me:
1. Check for signs of compromise
2. Enumerate running processes and connections
3. Identify any backdoors or persistence mechanisms
4. Gather evidence for forensic analysis
```

### Compliance Audit

```
Perform a PCI DSS compliance check on our payment processing infrastructure:
1. Verify network segmentation
2. Check for default credentials
3. Validate encryption in transit
4. Review access controls
5. Generate compliance report
```

## 💡 Tips for Effective Prompts

1. **Be Specific**: Include target details, scope, and authorization
2. **Structured Requests**: Break complex tasks into phases
3. **Use Skills**: Reference specific skills when available
4. **Provide Context**: Mention previous findings that inform next steps
5. **Set Expectations**: Specify desired output format and level of detail

## 📚 Learning Resources

After trying these prompts:
- Review `audit/session_report.md` for structured findings
- Check `audit/audit_log.jsonl` for detailed execution logs
- Examine `audit/loot/` for raw tool outputs
- Study successful workflows to create custom prompts
