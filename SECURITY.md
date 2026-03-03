# Security Policy

## 🛡️ Purpose

Taskmaster is designed as a **security assessment orchestration platform**. It is intended for:

- Authorized penetration testing
- Security research in controlled environments
- CTF competitions and training
- Defensive security operations
- Compliance auditing with proper authorization

## ⚠️ Important Disclaimers

### Legal Use Only

Taskmaster must only be used for **authorized security testing** where you have:

1. **Explicit written permission** from the target system owner
2. A defined **scope of testing**
3. Clear **rules of engagement**
4. Appropriate **insurance and legal protections** (for professional engagements)

### Prohibited Uses

**DO NOT use Taskmaster for:**

- Unauthorized access to systems or networks
- Malicious attacks or data theft
- Denial of service attacks
- Privacy violations
- Any illegal activities

**Unauthorized use may result in:**
- Criminal prosecution
- Civil liability
- Loss of professional certifications
- Damage to reputation

## 🔐 Ethical Guidelines

### Target Authorization

Before using Taskmaster:

1. **Document Authorization**: Maintain written evidence of permission to test
2. **Define Scope**: Clearly document which systems/networks are in scope
3. **Set Boundaries**: Establish what techniques are prohibited
4. **Emergency Contacts**: Have contact information for target system owners
5. **Data Handling**: Understand requirements for handling discovered data

### Responsible Disclosure

If Taskmaster discovers vulnerabilities:

1. **Do Not Exploit**: Stop testing once a vulnerability is confirmed
2. **Document Findings**: Record evidence professionally
3. **Notify Stakeholders**: Inform the target organization promptly
4. **Allow Remediation Time**: Give reasonable time to fix issues before public disclosure
5. **Protect Sensitive Data**: Handle discovered credentials/data with extreme care

## 🔒 Security Features

### Audit Trail

Taskmaster maintains comprehensive audit logs:

- `audit/session_report.md` - Human-readable assessment report
- `audit/audit_log.jsonl` - Machine-readable event log
- `audit/loot/` - Artifacts and evidence

**These logs should be:**
- Protected with appropriate file permissions
- Stored securely
- Retained according to engagement requirements
- Provided to clients as deliverables

### Target Locking

Taskmaster prevents concurrent operations on the same target to:
- Avoid service disruption
- Prevent race conditions
- Maintain audit trail integrity

### Phase-Based Controls

The phase system enforces proper assessment methodology:
1. Reconnaissance (passive information gathering)
2. Enumeration (active scanning)
3. Exploitation (vulnerability testing)
4. Post-exploitation (controlled access)

## 🚨 Reporting Security Vulnerabilities

### Scope

If you discover a security vulnerability **in Taskmaster itself** (not in targets you're testing):

**In Scope:**
- Authentication/authorization bypasses
- Code injection vulnerabilities
- Container escape scenarios
- Privilege escalation
- Data leakage between assessments

**Out of Scope:**
- Issues in third-party tools (nmap, ffuf, etc.)
- Vulnerabilities in targets being assessed
- Social engineering attacks
- Physical security issues

### Reporting Process

1. **Do Not** create a public GitHub issue
2. **Email** security details to [your-security-email@example.com]
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested remediation (if any)
4. **Wait** for acknowledgment (we aim for 48 hours)
5. **Coordinate** disclosure timeline (typically 90 days)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Status Updates**: Every 2 weeks
- **Remediation**: Depends on severity (critical: days, high: weeks, medium/low: months)
- **Credit**: Public acknowledgment in release notes (if desired)

## 🔧 Security Best Practices for Users

### Container Security

1. **Keep Base Image Updated**: Regularly rebuild with latest Kali packages
2. **Network Isolation**: Use appropriate Docker network configurations
3. **Volume Permissions**: Ensure loot/skills directories have proper permissions
4. **Secrets Management**: Never commit credentials or API keys

### Operational Security

1. **VPN/Tunneling**: Use appropriate network isolation
2. **Proxy Configuration**: Route traffic through approved proxies when required
3. **Data Encryption**: Encrypt sensitive findings at rest and in transit
4. **Access Controls**: Limit who can spawn agents and access audit data
5. **Log Retention**: Follow organizational policies for log retention and destruction

### Credential Handling

When Taskmaster discovers credentials:

1. **Immediate Documentation**: Record in secure location
2. **Notification**: Inform stakeholders immediately
3. **No Unauthorized Use**: Do not use credentials beyond authorized testing scope
4. **Secure Storage**: Encrypt and protect from unauthorized access
5. **Proper Disposal**: Securely delete after engagement completion

## 📋 Compliance Considerations

### Data Protection

Consider regulations that may apply:
- GDPR (if testing EU systems)
- CCPA (if testing California-based systems)
- HIPAA (if testing healthcare systems)
- PCI DSS (if testing payment systems)

### Evidence Requirements

Maintain audit trails for:
- Compliance audits
- Legal proceedings
- Client deliverables
- Professional certifications (OSCP, GPEN, etc.)

## 🔄 Updates

This security policy may be updated periodically. Check the git history for changes.

**Last Updated**: 2026-02-10
