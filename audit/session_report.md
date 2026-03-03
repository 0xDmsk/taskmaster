# Security Assessment Report
Started: 2026-02-25 14:05:12

## Execution Summary

| ID | Phase | Target | Action | Status | Result |
|----|-------|--------|--------|--------|--------|
| a3d402ff | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| a3d402ff | reconnaissance | 10.0.0.1 | network_scan | FAILED | [Failed](#a3d402ff) |

### Detailed Result: a3d402ff

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Network timeout
```

---

| 33cfd424 | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| 33cfd424 | reconnaissance | 10.0.0.1 | network_scan | COMPLETED | [Success](#33cfd424) |

### Detailed Result: 33cfd424

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Scan successful this time
```

---

| df7df1c1 | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| df7df1c1 | reconnaissance | 10.0.0.1 | network_scan | FAILED | [Failed](#df7df1c1) |

### Detailed Result: df7df1c1

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Network timeout
```

---

| 9bfbc12b | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| 9bfbc12b | reconnaissance | 10.0.0.1 | network_scan | COMPLETED | [Success](#9bfbc12b) |

### Detailed Result: 9bfbc12b

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Scan successful this time
```

---

| e9542665 | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| e9542665 | reconnaissance | 10.0.0.1 | network_scan | FAILED | [Failed](#e9542665) |

### Detailed Result: e9542665

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Network timeout
```

---

| 49ec8ffa | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| 49ec8ffa | reconnaissance | 10.0.0.1 | network_scan | COMPLETED | [Success](#49ec8ffa) |

### Detailed Result: 49ec8ffa

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Scan successful this time
```

---

| e63c1fc4 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| e63c1fc4 | reconnaissance | nob.ro | analysis | FAILED | [Failed](#e63c1fc4) |

### Detailed Result: e63c1fc4

- **Target:** nob.ro
- **Justification:** This action is necessary to perform initial reconnaissance on the target 'nob.ro'. By using the 'SubdomainSkill' in passive mode, we can gather a list of potential subdomains from public sources like crt.sh without sending any traffic to the target's infrastructure, ensuring a low-impact and stealthy discovery phase.
- **Command:** `
from skills.subdomain import SubdomainSkill

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Run the skill in passive mode to find subdomains using crt.sh
# This is a safe, network-friendly operation.
results = skill.run(mode="passive")

# Print the results in a structured way
print("--- Subdomain Enumeration Results ---")
print(f"Target: {results.get('target')}")
print(f"Mode: {results.get('mode')}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")

# Save the findings to a file in the loot directory
# The skill already saves a basic list, but we can save the full JSON result for better data.
skill.save_json(f"subdomains_{results.get('target')}_passive.json", results)

print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
Python Execution Failed:
Traceback (most recent call last):
  File "/usr/local/bin/kali-operator", line 152, in execute_action
    exec(command, exec_globals)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'skills'

```

---

| c01962cb | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| c01962cb | reconnaissance | nob.ro | analysis | FAILED | [Failed](#c01962cb) |

### Detailed Result: c01962cb

- **Target:** nob.ro
- **Justification:** This action is necessary to perform initial reconnaissance on the target 'nob.ro'. By using the 'SubdomainSkill' in passive mode, we can gather a list of potential subdomains from public sources like crt.sh without sending any traffic to the target's infrastructure, ensuring a low-impact and stealthy discovery phase. This attempt corrects a python path issue.
- **Command:** `
import sys
sys.path.append('/app')
from skills.subdomain import SubdomainSkill

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Run the skill in passive mode to find subdomains using crt.sh
# This is a safe, network-friendly operation.
results = skill.run(mode="passive")

# Print the results in a structured way
print("--- Subdomain Enumeration Results ---")
print(f"Target: {results.get('target')}")
print(f"Mode: {results.get('mode')}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")

# Save the findings to a file in the loot directory
# The skill already saves a basic list, but we can save the full JSON result for better data.
skill.save_json(f"subdomains_{results.get('target')}_passive.json", results)

print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
Python Execution Failed:
Traceback (most recent call last):
  File "/usr/local/bin/kali-operator", line 152, in execute_action
    exec(command, exec_globals)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 4, in <module>
ModuleNotFoundError: No module named 'skills'

```

---

| 76d99a01 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 76d99a01 | reconnaissance | nob.ro | analysis | FAILED | [Failed](#76d99a01) |

### Detailed Result: 76d99a01

- **Target:** nob.ro
- **Justification:** This action is necessary to perform initial reconnaissance on the target 'nob.ro'. By using the 'SubdomainSkill' in passive mode, we can gather a list of potential subdomains from public sources like crt.sh without sending any traffic to the target's infrastructure, ensuring a low-impact and stealthy discovery phase. This attempt corrects a python path issue by explicitly setting it in the command.
- **Command:** `python3 -c "import sys; sys.path.append('/app'); from skills.subdomain import SubdomainSkill; skill = SubdomainSkill(target='nob.ro'); results = skill.run(mode='passive'); print('--- Subdomain Enumeration Results ---'); print(f'Target: {results.get('target')}'); print(f'Mode: {results.get('mode')}'); print(f'Found {results.get('passive_count', 0)} subdomains via crt.sh.'); skill.save_json(f'subdomains_{results.get('target')}_passive.json', results); print('\nFull JSON results saved to artifact.');"`

#### Raw Output

```
Python Execution Failed:
Traceback (most recent call last):
  File "/usr/local/bin/kali-operator", line 152, in execute_action
    exec(command, exec_globals)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 1
    python3 -c "import sys; sys.path.append('/app'); from skills.subdomain import SubdomainSkill; skill = SubdomainSkill(target='nob.ro'); results = skill.run(mode='passive'); print('--- Subdomain Enumeration Results ---'); print(f'Target: {results.get('target')}'); print(f'Mode: {results.get('mode')}'); print(f'Found {results.get('passive_count', 0)} subdomains via crt.sh.'); skill.save_json(f'subdomains_{results.get('target')}_passive.json', results); print('\nFull JSON results saved to artifact.');"
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: invalid syntax

```

---

| a742440a | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| a742440a | reconnaissance | nob.ro | analysis | FAILED | [Failed](#a742440a) |

### Detailed Result: a742440a

- **Target:** nob.ro
- **Justification:** This action is necessary to perform initial reconnaissance on the target 'nob.ro'. By using the 'SubdomainSkill' in passive mode, we can gather a list of potential subdomains from public sources like crt.sh without sending any traffic to the target's infrastructure, ensuring a low-impact and stealthy discovery phase. This attempt corrects the previous SyntaxError by providing pure Python code to the 'command' argument.
- **Command:** `
import sys
sys.path.append('/app')
from skills.subdomain import SubdomainSkill
import json

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Run the skill in passive mode to find subdomains using crt.sh
# This is a safe, network-friendly operation.
results = skill.run(mode="passive")

# Print the results in a structured way
print("--- Subdomain Enumeration Results ---")
print(f"Target: {results.get('target')}")
print(f"Mode: {results.get('mode')}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")

# Save the findings to a file in the loot directory
# The skill already saves a basic list, but we can save the full JSON result for better data.
skill.save_json(f"subdomains_{results.get('target')}_passive.json", results)

print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
Python Execution Failed:
Traceback (most recent call last):
  File "/usr/local/bin/kali-operator", line 152, in execute_action
    exec(command, exec_globals)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 4, in <module>
ModuleNotFoundError: No module named 'skills'

```

---

| d5849fa4 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| d5849fa4 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#d5849fa4) |

### Detailed Result: d5849fa4

- **Target:** nob.ro
- **Justification:** To diagnose why the 'skills' module is not found, this action will inspect the Python environment within the agent's container by printing sys.path and the PYTHONPATH environment variable.
- **Command:** `import sys, os; print("sys.path:", sys.path); print("PYTHONPATH:", os.environ.get("PYTHONPATH"));`

#### Raw Output

```
STDOUT:
sys.path: ['/usr/local/bin', '/app', '/work', '/usr/lib/python313.zip', '/usr/lib/python3.13', '/usr/lib/python3.13/lib-dynload', '/usr/local/lib/python3.13/dist-packages', '/usr/lib/python3/dist-packages']
PYTHONPATH: /app:

STDERR:

```

---

| 41872f9b | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 41872f9b | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#41872f9b) |

### Detailed Result: 41872f9b

- **Target:** nob.ro
- **Justification:** This action will provide detailed diagnostics on the agent's Python environment to finally resolve the 'ModuleNotFoundError'. It will print the sys.path, the PYTHONPATH, and the contents of the /app and /app/skills directories before attempting the import, which should pinpoint the exact cause of the problem.
- **Command:** `import sys, os; print("Current sys.path:", sys.path); print("PYTHONPATH env var:", os.environ.get("PYTHONPATH")); print("Contents of /app:", os.listdir("/app")); print("Contents of /app/skills:", os.listdir("/app/skills")); from skills.subdomain import SubdomainSkill;`

#### Raw Output

```
STDOUT:
Current sys.path: ['/usr/local/bin', '/app', '/work', '/usr/lib/python313.zip', '/usr/lib/python3.13', '/usr/lib/python3.13/lib-dynload', '/usr/local/lib/python3.13/dist-packages', '/usr/lib/python3/dist-packages']
PYTHONPATH env var: /app:
Contents of /app: ['skills']
Contents of /app/skills: ['TEMPLATE.md', '__init__.py', '__pycache__', 'base.py', 'cloud.py', 'network.py', 'subdomain.py', 'takeover.py', 'web.py']

STDERR:

```

---

| 2f4b5242 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 2f4b5242 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#2f4b5242) |

### Detailed Result: 2f4b5242

- **Target:** nob.ro
- **Justification:** This action will perform passive subdomain enumeration for nob.ro using the SubdomainSkill. Following successful diagnostic tests that confirmed the import path is correct, this execution will gather the required subdomain information as originally requested.
- **Command:** `
from skills.subdomain import SubdomainSkill
import json

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Run the skill in passive mode to find subdomains using crt.sh
results = skill.run(mode="passive")

# Print the results in a structured way for the report
print("--- Passive Subdomain Enumeration Results ---")
print(f"Target: {results.get('target')}")
print(f"Mode: {results.get('mode')}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")
for sub in results.get('subdomains', []):
    print(sub)

# Save the full JSON results as an artifact for later analysis
skill.save_json(f"subdomains_{results.get('target')}_passive.json", results)
print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
[*] Querying crt.sh for nob.ro...
--- Passive Subdomain Enumeration Results ---
Target: nob.ro
Mode: passive
Found 0 subdomains via crt.sh.

Full JSON results saved to artifact.

STDERR:

```

---

| 644de371 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 644de371 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#644de371) |

### Detailed Result: 644de371

- **Target:** nob.ro
- **Justification:** The initial passive scan yielded no results. This active scan is the next logical step, using brute-force with a common wordlist to discover non-public subdomains for 'nob.ro', as approved by the user.
- **Command:** `
from skills.subdomain import SubdomainSkill
import json

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Run the skill in active mode to find subdomains
results = skill.run(mode="active")

# Print the results in a structured way for the report
print("--- Active Subdomain Enumeration Results ---")
print(f"Target: {results.get('target')}")
print(f"Mode: {results.get('mode')}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")
print(f"Found an additional {results.get('active_found', 0)} subdomains via active brute-force.")

print("\n--- Found Subdomains ---")
for sub in results.get('subdomains', []):
    print(sub)

# Save the full JSON results as an artifact
skill.save_json(f"subdomains_{results.get('target')}_active.json", results)
print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
[*] Querying crt.sh for nob.ro...
[*] Running gobuster DNS for nob.ro...
--- Active Subdomain Enumeration Results ---
Target: nob.ro
Mode: active
Found 0 subdomains via crt.sh.
Found an additional 0 subdomains via active brute-force.

--- Found Subdomains ---

Full JSON results saved to artifact.

STDERR:

```

---

| 07ef5c83 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 07ef5c83 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#07ef5c83) |

### Detailed Result: 07ef5c83

- **Target:** nob.ro
- **Justification:** Per user instruction, this action retries the active subdomain scan for 'nob.ro'. It includes a preliminary check to ensure the SecLists wordlist is available at the expected path before initiating the scan, addressing potential reasons for previous failures. The agent environment is expected to have the wordlist mounted.
- **Command:** `
import os
import json
from skills.subdomain import SubdomainSkill

wordlist_path = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt"
print(f"Checking for wordlist at: {wordlist_path}")
if not os.path.exists(wordlist_path):
    print("!!! Wordlist NOT found. The scan will likely fail or return no results.")
else:
    print("Wordlist found. Proceeding with scan.")

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Run the skill in active mode to find subdomains
results = skill.run(mode="active")

# Print the results in a structured way for the report
print("--- Active Subdomain Enumeration Results ---")
print(f"Target: {results.get('target')}")
print(f"Mode: {results.get('mode')}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")
print(f"Found an additional {results.get('active_found', 0)} subdomains via active brute-force.")

print("\n--- Found Subdomains ---")
for sub in results.get('subdomains', []):
    print(sub)

# Save the full JSON results as an artifact
skill.save_json(f"subdomains_{results.get('target')}_active_seclist_check.json", results)
print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
Checking for wordlist at: /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
Wordlist found. Proceeding with scan.
[*] Querying crt.sh for nob.ro...
[*] Running gobuster DNS for nob.ro...
[!] Wildcard DNS detected (127.0.0.1). Enabling --wildcard mode.
--- Active Subdomain Enumeration Results ---
Target: nob.ro
Mode: active
Found 0 subdomains via crt.sh.
Found an additional 0 subdomains via active brute-force.

--- Found Subdomains ---

Full JSON results saved to artifact.

STDERR:

```

---

| 6af24b52 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 6af24b52 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#6af24b52) |

### Detailed Result: 6af24b52

- **Target:** nob.ro
- **Justification:** The user suspects that previous scans missed a subdomain on crt.sh. This action performs a direct, manual query using python's `requests` library within the agent to fetch and parse the data from crt.sh, independently verifying the results of the SubdomainSkill's passive run.
- **Command:** `
import requests
import json

domain = "nob.ro"
url = f"https://crt.sh/?q=%.{domain}&output=json"
print(f"[*] Querying {url}")
try:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    print("[+] crt.sh query successful.")
    print("\n--- RAW RESPONSE ---")
    print(json.dumps(data, indent=2))

    subs = set()
    for entry in data:
        name = entry.get("name_value", "")
        for sub in name.split():
            if "*" not in sub:
                subs.add(sub)
    
    print("\n--- PARSED SUBDOMAINS ---")
    if subs:
        for s in sorted(list(subs)):
            print(s)
    else:
        print("No subdomains found.")

except requests.exceptions.RequestException as e:
    print(f"[!] crt.sh query failed: {e}")

except json.JSONDecodeError:
    print("[!] Failed to decode JSON response from crt.sh.")
    print("--- RAW RESPONSE ---")
    print(r.text)
`

#### Raw Output

```
STDOUT:
[*] Querying https://crt.sh/?q=%.nob.ro&output=json
[+] crt.sh query successful.

--- RAW RESPONSE ---
[
  {
    "issuer_ca_id": 295809,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E8",
    "common_name": "n8n8n.nob.ro",
    "name_value": "n8n8n.nob.ro",
    "id": 24154736111,
    "entry_timestamp": "2026-02-03T08:07:38.674",
    "not_before": "2026-02-03T07:09:08",
    "not_after": "2026-05-04T07:09:07",
    "serial_number": "054e1bace75c9e656394eaab57d7b626391a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 295809,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E8",
    "common_name": "n8n8n.nob.ro",
    "name_value": "n8n8n.nob.ro",
    "id": 24154709265,
    "entry_timestamp": "2026-02-03T08:07:38.408",
    "not_before": "2026-02-03T07:09:08",
    "not_after": "2026-05-04T07:09:07",
    "serial_number": "054e1bace75c9e656394eaab57d7b626391a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 24031981033,
    "entry_timestamp": "2026-01-28T09:43:59.253",
    "not_before": "2026-01-28T08:43:33",
    "not_after": "2026-04-28T09:40:50",
    "serial_number": "00e31d3f51349e858711223664bd87d607",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 24031979458,
    "entry_timestamp": "2026-01-28T09:43:34.576",
    "not_before": "2026-01-28T08:43:33",
    "not_after": "2026-04-28T09:40:50",
    "serial_number": "00e31d3f51349e858711223664bd87d607",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 23742458637,
    "entry_timestamp": "2026-01-13T13:01:32.867",
    "not_before": "2026-01-13T00:00:00",
    "not_after": "2026-04-13T12:59:58",
    "serial_number": "73d707fc785df61ec4734739948875b9",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 23742459922,
    "entry_timestamp": "2026-01-13T13:01:31.454",
    "not_before": "2026-01-13T00:00:00",
    "not_after": "2026-04-13T12:59:58",
    "serial_number": "73d707fc785df61ec4734739948875b9",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 22977366358,
    "entry_timestamp": "2025-12-08T10:58:08.608",
    "not_before": "2025-11-30T04:16:52",
    "not_after": "2026-02-28T05:14:38",
    "serial_number": "673d96ba2f5c6f280eaa4087573dfaf9",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 22816751572,
    "entry_timestamp": "2025-11-30T05:16:52.407",
    "not_before": "2025-11-30T04:16:52",
    "not_after": "2026-02-28T05:14:38",
    "serial_number": "673d96ba2f5c6f280eaa4087573dfaf9",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 22487199323,
    "entry_timestamp": "2025-11-15T11:36:34.972",
    "not_before": "2025-11-15T00:00:00",
    "not_after": "2026-02-13T11:00:32",
    "serial_number": "7d107e8a4105e5d619925e5d51b44d96",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 22487198784,
    "entry_timestamp": "2025-11-15T11:36:34.095",
    "not_before": "2025-11-15T00:00:00",
    "not_after": "2026-02-13T11:00:32",
    "serial_number": "7d107e8a4105e5d619925e5d51b44d96",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 21419005255,
    "entry_timestamp": "2025-10-02T12:32:42.427",
    "not_before": "2025-10-01T23:39:45",
    "not_after": "2025-12-31T00:38:05",
    "serial_number": "00c0c47562780f94721123cdaff021a425",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 21495557670,
    "entry_timestamp": "2025-10-02T00:39:46.079",
    "not_before": "2025-10-01T23:39:45",
    "not_after": "2025-12-31T00:38:05",
    "serial_number": "00c0c47562780f94721123cdaff021a425",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 21137855160,
    "entry_timestamp": "2025-09-19T18:32:59.918",
    "not_before": "2025-09-19T00:00:00",
    "not_after": "2025-12-16T08:11:20",
    "serial_number": "50a5c3e22b1c35336fbd4ae4198ad339",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 21137854984,
    "entry_timestamp": "2025-09-19T18:32:59.399",
    "not_before": "2025-09-19T00:00:00",
    "not_after": "2025-12-16T08:11:20",
    "serial_number": "50a5c3e22b1c35336fbd4ae4198ad339",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20096989667,
    "entry_timestamp": "2025-08-03T20:04:52.26",
    "not_before": "2025-08-03T19:03:45",
    "not_after": "2025-11-01T20:01:26",
    "serial_number": "00b828d089d7f122b6111ff2240527fbc7",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20096989660,
    "entry_timestamp": "2025-08-03T20:03:46.462",
    "not_before": "2025-08-03T19:03:45",
    "not_after": "2025-11-01T20:01:26",
    "serial_number": "00b828d089d7f122b6111ff2240527fbc7",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 19668227316,
    "entry_timestamp": "2025-07-14T23:50:47.104",
    "not_before": "2025-07-14T00:00:00",
    "not_after": "2025-10-12T01:00:11",
    "serial_number": "61f6f5a37e0b10908021c974c4316081",
    "result_count": 3
  },
  {
    "issuer_ca_id": 204407,
    "issuer_name": "C=GB, O=Sectigo Limited, CN=Sectigo Public Server Authentication CA DV E36",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 19668226872,
    "entry_timestamp": "2025-07-14T23:50:46.509",
    "not_before": "2025-07-14T00:00:00",
    "not_after": "2025-10-12T01:00:11",
    "serial_number": "61f6f5a37e0b10908021c974c4316081",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 18828101149,
    "entry_timestamp": "2025-06-05T16:15:11.221",
    "not_before": "2025-06-05T14:10:17",
    "not_after": "2025-09-03T15:08:45",
    "serial_number": "481c62d6541c1d760e52467cc13d1037",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 18827625741,
    "entry_timestamp": "2025-06-05T15:10:17.533",
    "not_before": "2025-06-05T14:10:17",
    "not_after": "2025-09-03T15:08:45",
    "serial_number": "481c62d6541c1d760e52467cc13d1037",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 17718820734,
    "entry_timestamp": "2025-04-07T10:31:05.874",
    "not_before": "2025-04-07T09:31:05",
    "not_after": "2025-07-06T10:29:44",
    "serial_number": "00edf8b3ae6faadc1f1396607a0bf1e1d6",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 16593197485,
    "entry_timestamp": "2025-02-07T18:38:32.653",
    "not_before": "2025-02-07T05:00:30",
    "not_after": "2025-05-08T05:57:57",
    "serial_number": "7dd0ff534cd6768f13c6a552692b2949",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 16593178709,
    "entry_timestamp": "2025-02-07T06:00:31.06",
    "not_before": "2025-02-07T05:00:30",
    "not_after": "2025-05-08T05:57:57",
    "serial_number": "7dd0ff534cd6768f13c6a552692b2949",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 15927318849,
    "entry_timestamp": "2024-12-10T02:21:36.18",
    "not_before": "2024-12-10T01:21:35",
    "not_after": "2025-03-10T01:21:34",
    "serial_number": "009c2583e26443dd1011cf4742be891c09",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 14894252949,
    "entry_timestamp": "2024-10-11T22:30:16.086",
    "not_before": "2024-10-11T21:30:15",
    "not_after": "2025-01-09T21:30:14",
    "serial_number": "751e344d68856d6c0d571f757115da91",
    "result_count": 3
  },
  {
    "issuer_ca_id": 286236,
    "issuer_name": "C=US, O=Google Trust Services, CN=WE1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 14125692566,
    "entry_timestamp": "2024-08-13T23:16:19.507",
    "not_before": "2024-08-13T22:16:18",
    "not_after": "2024-11-11T22:16:17",
    "serial_number": "1b39f4fe499a2f050df7a27a50647dc9",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 14125115399,
    "entry_timestamp": "2024-08-13T23:13:59.566",
    "not_before": "2024-08-13T00:00:00",
    "not_after": "2025-08-13T23:59:59",
    "serial_number": "1722585cc953ff5461a9b2b14cb649b0",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 14125115277,
    "entry_timestamp": "2024-08-13T23:13:59.151",
    "not_before": "2024-08-13T00:00:00",
    "not_after": "2025-08-13T23:59:59",
    "serial_number": "1722585cc953ff5461a9b2b14cb649b0",
    "result_count": 3
  },
  {
    "issuer_ca_id": 295810,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E5",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 13403022178,
    "entry_timestamp": "2024-06-15T20:37:37.743",
    "not_before": "2024-06-15T19:37:37",
    "not_after": "2024-09-13T19:37:36",
    "serial_number": "0484dfe76dbdab90ae74fe40d8b04111372d",
    "result_count": 3
  },
  {
    "issuer_ca_id": 295810,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E5",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 13403019821,
    "entry_timestamp": "2024-06-15T20:37:37.268",
    "not_before": "2024-06-15T19:37:37",
    "not_after": "2024-09-13T19:37:36",
    "serial_number": "0484dfe76dbdab90ae74fe40d8b04111372d",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12719349671,
    "entry_timestamp": "2024-04-14T05:43:39.202",
    "not_before": "2024-04-14T04:43:38",
    "not_after": "2024-07-13T04:43:37",
    "serial_number": "0424b0cbe5ad0e6732d9140ca877e04e4523",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12719358176,
    "entry_timestamp": "2024-04-14T05:43:38.946",
    "not_before": "2024-04-14T04:43:38",
    "not_after": "2024-07-13T04:43:37",
    "serial_number": "0424b0cbe5ad0e6732d9140ca877e04e4523",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12478951219,
    "entry_timestamp": "2024-03-25T00:10:08.386",
    "not_before": "2024-03-25T00:00:00",
    "not_after": "2025-03-25T23:59:59",
    "serial_number": "38b990e9fc96a2901b6142f7f1baa7e1",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12478951360,
    "entry_timestamp": "2024-03-25T00:10:07.232",
    "not_before": "2024-03-25T00:00:00",
    "not_after": "2025-03-25T23:59:59",
    "serial_number": "38b990e9fc96a2901b6142f7f1baa7e1",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12083768673,
    "entry_timestamp": "2024-02-15T03:06:59.849",
    "not_before": "2024-02-15T02:06:58",
    "not_after": "2024-05-15T02:06:57",
    "serial_number": "045ba81beff3370154913e0d122bc4b441dc",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12083749109,
    "entry_timestamp": "2024-02-15T03:06:59.025",
    "not_before": "2024-02-15T02:06:58",
    "not_after": "2024-05-15T02:06:57",
    "serial_number": "045ba81beff3370154913e0d122bc4b441dc",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 11426765121,
    "entry_timestamp": "2023-12-17T18:30:57.766",
    "not_before": "2023-12-17T17:30:57",
    "not_after": "2024-03-16T17:30:56",
    "serial_number": "0338deb994a3ee50dd9a951c99ba85e2e7a3",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 11434255918,
    "entry_timestamp": "2023-12-17T18:30:57.582",
    "not_before": "2023-12-17T17:30:57",
    "not_after": "2024-03-16T17:30:56",
    "serial_number": "0338deb994a3ee50dd9a951c99ba85e2e7a3",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 10833445987,
    "entry_timestamp": "2023-10-19T15:38:18.794",
    "not_before": "2023-10-19T14:38:18",
    "not_after": "2024-01-17T14:38:17",
    "serial_number": "04938219508131d9ad2bd13e2b68a56fa064",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 10833441665,
    "entry_timestamp": "2023-10-19T15:38:18.479",
    "not_before": "2023-10-19T14:38:18",
    "not_after": "2024-01-17T14:38:17",
    "serial_number": "04938219508131d9ad2bd13e2b68a56fa064",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 10361964676,
    "entry_timestamp": "2023-08-21T12:41:19.172",
    "not_before": "2023-08-21T11:41:18",
    "not_after": "2023-11-19T11:41:17",
    "serial_number": "033f280ba6c3f43be9a6b5fb68a61e94206d",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 10238299809,
    "entry_timestamp": "2023-08-21T12:41:18.912",
    "not_before": "2023-08-21T11:41:18",
    "not_after": "2023-11-19T11:41:17",
    "serial_number": "033f280ba6c3f43be9a6b5fb68a61e94206d",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9746604334,
    "entry_timestamp": "2023-06-23T09:15:33.948",
    "not_before": "2023-06-23T08:15:33",
    "not_after": "2023-09-21T08:15:32",
    "serial_number": "046dbdf4d6caf73cfdf6e3a66f02f7587b7d",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9724191597,
    "entry_timestamp": "2023-06-23T09:15:33.649",
    "not_before": "2023-06-23T08:15:33",
    "not_after": "2023-09-21T08:15:32",
    "serial_number": "046dbdf4d6caf73cfdf6e3a66f02f7587b7d",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9227748636,
    "entry_timestamp": "2023-04-25T04:35:58.41",
    "not_before": "2023-04-25T00:00:00",
    "not_after": "2024-04-24T23:59:59",
    "serial_number": "00edee47983eb6b066a830b3bbd3c2db1c",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9227748423,
    "entry_timestamp": "2023-04-25T04:35:57.91",
    "not_before": "2023-04-25T00:00:00",
    "not_after": "2024-04-24T23:59:59",
    "serial_number": "00edee47983eb6b066a830b3bbd3c2db1c",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9242868555,
    "entry_timestamp": "2023-04-25T03:52:59.726",
    "not_before": "2023-04-25T02:52:59",
    "not_after": "2023-07-24T02:52:58",
    "serial_number": "034053cf144e8c796e087a5fdec2613f394c",
    "result_count": 3
  },
  {
    "issuer_ca_id": 183283,
    "issuer_name": "C=US, O=Let's Encrypt, CN=E1",
    "common_name": "nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9228086915,
    "entry_timestamp": "2023-04-25T03:52:59.567",
    "not_before": "2023-04-25T02:52:59",
    "not_after": "2023-07-24T02:52:58",
    "serial_number": "034053cf144e8c796e087a5fdec2613f394c",
    "result_count": 3
  },
  {
    "issuer_ca_id": 157938,
    "issuer_name": "C=US, O=\"Cloudflare, Inc.\", CN=Cloudflare Inc ECC CA-3",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9227533821,
    "entry_timestamp": "2023-04-25T03:51:38.933",
    "not_before": "2023-04-25T00:00:00",
    "not_after": "2024-04-24T23:59:59",
    "serial_number": "0c9cd75d2f081179eaec3b65e366a270",
    "result_count": 2
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "*.nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6797663760,
    "entry_timestamp": "2022-05-25T05:15:46.843",
    "not_before": "2022-05-25T00:00:00",
    "not_after": "2023-05-25T23:59:59",
    "serial_number": "00c40b5bbab40504827a5aa4be24a3867e",
    "result_count": 3
  },
  {
    "issuer_ca_id": 105484,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited, CN=Sectigo ECC Domain Validation Secure Server CA",
    "common_name": "*.nob.ro",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6797663572,
    "entry_timestamp": "2022-05-25T05:15:45.964",
    "not_before": "2022-05-25T00:00:00",
    "not_after": "2023-05-25T23:59:59",
    "serial_number": "00c40b5bbab40504827a5aa4be24a3867e",
    "result_count": 3
  },
  {
    "issuer_ca_id": 157938,
    "issuer_name": "C=US, O=\"Cloudflare, Inc.\", CN=Cloudflare Inc ECC CA-3",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6796558953,
    "entry_timestamp": "2022-05-25T01:25:26.94",
    "not_before": "2022-05-25T00:00:00",
    "not_after": "2023-05-25T23:59:59",
    "serial_number": "0b5af69b883a4862101ebdca57c18830",
    "result_count": 2
  },
  {
    "issuer_ca_id": 157938,
    "issuer_name": "C=US, O=\"Cloudflare, Inc.\", CN=Cloudflare Inc ECC CA-3",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 4760621684,
    "entry_timestamp": "2021-06-25T15:21:09.89",
    "not_before": "2021-06-25T00:00:00",
    "not_after": "2022-06-24T23:59:59",
    "serial_number": "022f514091f4b0e4bebcd04a12796167",
    "result_count": 2
  },
  {
    "issuer_ca_id": 157938,
    "issuer_name": "C=US, O=\"Cloudflare, Inc.\", CN=Cloudflare Inc ECC CA-3",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 3160013840,
    "entry_timestamp": "2020-07-29T09:39:19.627",
    "not_before": "2020-07-26T00:00:00",
    "not_after": "2021-07-26T12:00:00",
    "serial_number": "0bc0aed93c497532744002b379e9cf65",
    "result_count": 2
  },
  {
    "issuer_ca_id": 157938,
    "issuer_name": "C=US, O=\"Cloudflare, Inc.\", CN=Cloudflare Inc ECC CA-3",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 3142700302,
    "entry_timestamp": "2020-07-26T05:31:35.591",
    "not_before": "2020-07-26T00:00:00",
    "not_after": "2021-07-26T12:00:00",
    "serial_number": "0bc0aed93c497532744002b379e9cf65",
    "result_count": 2
  },
  {
    "issuer_ca_id": 12906,
    "issuer_name": "C=US, ST=CA, L=San Francisco, O=\"CloudFlare, Inc.\", CN=CloudFlare Inc ECC CA-2",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 2288416834,
    "entry_timestamp": "2020-01-05T01:04:40.928",
    "not_before": "2020-01-02T00:00:00",
    "not_after": "2020-10-09T12:00:00",
    "serial_number": "02afb94cd4ec84fefd5dec8f8fc3b2d4",
    "result_count": 2
  },
  {
    "issuer_ca_id": 12906,
    "issuer_name": "C=US, ST=CA, L=San Francisco, O=\"CloudFlare, Inc.\", CN=CloudFlare Inc ECC CA-2",
    "common_name": "sni.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 2279706662,
    "entry_timestamp": "2020-01-02T19:22:39.364",
    "not_before": "2020-01-02T00:00:00",
    "not_after": "2020-10-09T12:00:00",
    "serial_number": "02afb94cd4ec84fefd5dec8f8fc3b2d4",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 2271148169,
    "entry_timestamp": "2019-12-31T11:53:49.061",
    "not_before": "2019-12-31T00:00:00",
    "not_after": "2020-07-08T23:59:59",
    "serial_number": "3672ab879960d2a9bf6a33b3c15df467",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 2271147746,
    "entry_timestamp": "2019-12-31T11:53:29.289",
    "not_before": "2019-12-31T00:00:00",
    "not_after": "2020-07-08T23:59:59",
    "serial_number": "3672ab879960d2a9bf6a33b3c15df467",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 2089023592,
    "entry_timestamp": "2019-11-09T02:34:06.822",
    "not_before": "2019-11-09T00:00:00",
    "not_after": "2020-05-17T23:59:59",
    "serial_number": "49a633f63e980ab4d1d1cfb87e218096",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 2089022534,
    "entry_timestamp": "2019-11-09T02:33:51.848",
    "not_before": "2019-11-09T00:00:00",
    "not_after": "2020-05-17T23:59:59",
    "serial_number": "49a633f63e980ab4d1d1cfb87e218096",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1904210689,
    "entry_timestamp": "2019-09-19T22:25:20.185",
    "not_before": "2019-09-19T00:00:00",
    "not_after": "2020-03-27T23:59:59",
    "serial_number": "64152532dd7adbe303724894ff465029",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1904209927,
    "entry_timestamp": "2019-09-19T22:25:05.486",
    "not_before": "2019-09-19T00:00:00",
    "not_after": "2020-03-27T23:59:59",
    "serial_number": "64152532dd7adbe303724894ff465029",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1870624139,
    "entry_timestamp": "2019-09-11T04:46:21.086",
    "not_before": "2019-09-11T00:00:00",
    "not_after": "2020-03-19T23:59:59",
    "serial_number": "423dae708543dae868ffdac41f0ac27b",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1870624047,
    "entry_timestamp": "2019-09-11T04:45:58.202",
    "not_before": "2019-09-11T00:00:00",
    "not_after": "2020-03-19T23:59:59",
    "serial_number": "423dae708543dae868ffdac41f0ac27b",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1870491278,
    "entry_timestamp": "2019-09-11T03:57:51.38",
    "not_before": "2019-09-11T00:00:00",
    "not_after": "2020-03-19T23:59:59",
    "serial_number": "26f287ef348bc542b2102e2002197470",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1870489124,
    "entry_timestamp": "2019-09-11T03:57:36.083",
    "not_before": "2019-09-11T00:00:00",
    "not_after": "2020-03-19T23:59:59",
    "serial_number": "26f287ef348bc542b2102e2002197470",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1870486155,
    "entry_timestamp": "2019-09-11T03:55:32.178",
    "not_before": "2019-09-11T00:00:00",
    "not_after": "2020-03-19T23:59:59",
    "serial_number": "00f2e4048c2eb2d5ced89881c35b80857f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1870482748,
    "entry_timestamp": "2019-09-11T03:55:16.26",
    "not_before": "2019-09-11T00:00:00",
    "not_after": "2020-03-19T23:59:59",
    "serial_number": "00f2e4048c2eb2d5ced89881c35b80857f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1857047462,
    "entry_timestamp": "2019-09-07T11:26:02.185",
    "not_before": "2019-09-07T00:00:00",
    "not_after": "2020-03-15T23:59:59",
    "serial_number": "00947e346f4a85dd5665e2a6cd7c2cc507",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1857044684,
    "entry_timestamp": "2019-09-07T11:25:43.364",
    "not_before": "2019-09-07T00:00:00",
    "not_after": "2020-03-15T23:59:59",
    "serial_number": "00947e346f4a85dd5665e2a6cd7c2cc507",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1336620694,
    "entry_timestamp": "2019-04-01T03:06:49.323",
    "not_before": "2019-04-01T00:00:00",
    "not_after": "2019-10-08T23:59:59",
    "serial_number": "008b0ffff51f454ed1aa8855490a5385b6",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1336618869,
    "entry_timestamp": "2019-04-01T03:06:37.04",
    "not_before": "2019-04-01T00:00:00",
    "not_after": "2019-10-08T23:59:59",
    "serial_number": "008b0ffff51f454ed1aa8855490a5385b6",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1016230041,
    "entry_timestamp": "2018-12-10T03:27:32.622",
    "not_before": "2018-12-10T00:00:00",
    "not_after": "2019-06-18T23:59:59",
    "serial_number": "7ac4bc6eccd981814242fc216afeebbe",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 1016229551,
    "entry_timestamp": "2018-12-10T03:27:18.118",
    "not_before": "2018-12-10T00:00:00",
    "not_after": "2019-06-18T23:59:59",
    "serial_number": "7ac4bc6eccd981814242fc216afeebbe",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 995191319,
    "entry_timestamp": "2018-12-02T13:34:36.924",
    "not_before": "2018-12-02T00:00:00",
    "not_after": "2019-06-10T23:59:59",
    "serial_number": "71078cfe9f39b2c4b9e50ca7a1e462d3",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 995190652,
    "entry_timestamp": "2018-12-02T13:34:17.037",
    "not_before": "2018-12-02T00:00:00",
    "not_after": "2019-06-10T23:59:59",
    "serial_number": "71078cfe9f39b2c4b9e50ca7a1e462d3",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 945076822,
    "entry_timestamp": "2018-11-14T03:08:49.357",
    "not_before": "2018-11-14T00:00:00",
    "not_after": "2019-05-23T23:59:59",
    "serial_number": "009ba875a6a0805fafae1df1eee1b0427a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 945076119,
    "entry_timestamp": "2018-11-14T03:08:31.509",
    "not_before": "2018-11-14T00:00:00",
    "not_after": "2019-05-23T23:59:59",
    "serial_number": "009ba875a6a0805fafae1df1eee1b0427a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 896475582,
    "entry_timestamp": "2018-10-27T21:37:11.972",
    "not_before": "2018-10-27T00:00:00",
    "not_after": "2019-05-05T23:59:59",
    "serial_number": "0cf74967636cc6052f41badbbce8d5fe",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 896475476,
    "entry_timestamp": "2018-10-27T21:36:51.107",
    "not_before": "2018-10-27T00:00:00",
    "not_after": "2019-05-05T23:59:59",
    "serial_number": "0cf74967636cc6052f41badbbce8d5fe",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871266901,
    "entry_timestamp": "2018-10-17T22:52:30.643",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "1a0d93db71ed29f2a96416425fa6cbd5",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871266698,
    "entry_timestamp": "2018-10-17T22:52:16.122",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "1a0d93db71ed29f2a96416425fa6cbd5",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871265779,
    "entry_timestamp": "2018-10-17T22:51:20.076",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "008add391b3bc212b5bc530fa5c7080059",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871266002,
    "entry_timestamp": "2018-10-17T22:51:06.473",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "008add391b3bc212b5bc530fa5c7080059",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871261362,
    "entry_timestamp": "2018-10-17T22:44:39.995",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "00fe7a64afad979d23fd6e7673c1b31dde",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871261212,
    "entry_timestamp": "2018-10-17T22:44:26.663",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "00fe7a64afad979d23fd6e7673c1b31dde",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871212774,
    "entry_timestamp": "2018-10-17T22:34:19.065",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "00d5915692a2dee5c3c458be9656ede758",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 871212568,
    "entry_timestamp": "2018-10-17T22:34:05.855",
    "not_before": "2018-10-17T00:00:00",
    "not_after": "2019-04-25T23:59:59",
    "serial_number": "00d5915692a2dee5c3c458be9656ede758",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 820924219,
    "entry_timestamp": "2018-10-05T07:39:39.249",
    "not_before": "2018-10-05T00:00:00",
    "not_after": "2019-04-13T23:59:59",
    "serial_number": "00e99fd203577ed064c20ca8b0e0a83bee",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 820923747,
    "entry_timestamp": "2018-10-05T07:39:25.84",
    "not_before": "2018-10-05T00:00:00",
    "not_after": "2019-04-13T23:59:59",
    "serial_number": "00e99fd203577ed064c20ca8b0e0a83bee",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 802199983,
    "entry_timestamp": "2018-10-01T03:11:22.069",
    "not_before": "2018-10-01T00:00:00",
    "not_after": "2019-04-09T23:59:59",
    "serial_number": "61dcad0310be74d4bbf21bf5b6aa3eaf",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 802199115,
    "entry_timestamp": "2018-10-01T03:10:13.561",
    "not_before": "2018-10-01T00:00:00",
    "not_after": "2019-04-09T23:59:59",
    "serial_number": "61dcad0310be74d4bbf21bf5b6aa3eaf",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 787108477,
    "entry_timestamp": "2018-09-26T09:48:31.058",
    "not_before": "2018-09-26T00:00:00",
    "not_after": "2019-04-04T23:59:59",
    "serial_number": "462049f8e051035842a7d065900af29c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 787108644,
    "entry_timestamp": "2018-09-26T09:48:17.044",
    "not_before": "2018-09-26T00:00:00",
    "not_after": "2019-04-04T23:59:59",
    "serial_number": "462049f8e051035842a7d065900af29c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 786549404,
    "entry_timestamp": "2018-09-26T05:18:44.743",
    "not_before": "2018-09-26T00:00:00",
    "not_after": "2019-04-04T23:59:59",
    "serial_number": "763251b81101c1ed0ff2ee8f8e4063bd",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 786546635,
    "entry_timestamp": "2018-09-26T05:11:36.617",
    "not_before": "2018-09-26T00:00:00",
    "not_after": "2019-04-04T23:59:59",
    "serial_number": "763251b81101c1ed0ff2ee8f8e4063bd",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 767957238,
    "entry_timestamp": "2018-09-19T19:23:42.969",
    "not_before": "2018-09-19T00:00:00",
    "not_after": "2019-03-28T23:59:59",
    "serial_number": "66a2221f6ae1f1b155204fa34ec36554",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 767957244,
    "entry_timestamp": "2018-09-19T19:23:28.766",
    "not_before": "2018-09-19T00:00:00",
    "not_after": "2019-03-28T23:59:59",
    "serial_number": "66a2221f6ae1f1b155204fa34ec36554",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 740168310,
    "entry_timestamp": "2018-09-12T19:56:21.273",
    "not_before": "2018-09-12T00:00:00",
    "not_after": "2019-03-21T23:59:59",
    "serial_number": "00ff4a9bc7e88ffd551c811089b1e85c4f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 740167754,
    "entry_timestamp": "2018-09-12T19:56:01.027",
    "not_before": "2018-09-12T00:00:00",
    "not_after": "2019-03-21T23:59:59",
    "serial_number": "00ff4a9bc7e88ffd551c811089b1e85c4f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 738895533,
    "entry_timestamp": "2018-09-12T08:25:55.806",
    "not_before": "2018-09-12T00:00:00",
    "not_after": "2019-03-21T23:59:59",
    "serial_number": "00d7458d374e7e51d45547a39ab7758d99",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 738895464,
    "entry_timestamp": "2018-09-12T08:25:37.256",
    "not_before": "2018-09-12T00:00:00",
    "not_after": "2019-03-21T23:59:59",
    "serial_number": "00d7458d374e7e51d45547a39ab7758d99",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 737314886,
    "entry_timestamp": "2018-09-11T17:10:29.068",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00f3402d5c6d9061a18a8ac3542d035aaa",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 737313991,
    "entry_timestamp": "2018-09-11T17:10:15.021",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00f3402d5c6d9061a18a8ac3542d035aaa",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 737005726,
    "entry_timestamp": "2018-09-11T14:14:59.429",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "4c8db5c6482260aa3ecf399ce81bcfc9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 737005777,
    "entry_timestamp": "2018-09-11T14:14:39.759",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "4c8db5c6482260aa3ecf399ce81bcfc9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 736934158,
    "entry_timestamp": "2018-09-11T13:50:29.265",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "0697e57be3c00352a44aa92221eeae60",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 736933967,
    "entry_timestamp": "2018-09-11T13:50:09.473",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "0697e57be3c00352a44aa92221eeae60",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 736713813,
    "entry_timestamp": "2018-09-11T11:42:14.23",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "5cab5d55f9ecc0ec2ae3fc306d4fd838",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 736713916,
    "entry_timestamp": "2018-09-11T11:41:52.204",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "5cab5d55f9ecc0ec2ae3fc306d4fd838",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 736107593,
    "entry_timestamp": "2018-09-11T07:17:23.117",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "3483c6a5434a34c8791def24d6546d61",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 736107506,
    "entry_timestamp": "2018-09-11T07:17:04.376",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "3483c6a5434a34c8791def24d6546d61",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735967277,
    "entry_timestamp": "2018-09-11T06:29:54.679",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00d12b61692d35c27ae300b37df88b9a48",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735967193,
    "entry_timestamp": "2018-09-11T06:29:36.285",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00d12b61692d35c27ae300b37df88b9a48",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735957493,
    "entry_timestamp": "2018-09-11T06:06:14.531",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00fd47259f229fc9b7c754e69bcdca82ba",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735957349,
    "entry_timestamp": "2018-09-11T06:05:48.959",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00fd47259f229fc9b7c754e69bcdca82ba",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735955522,
    "entry_timestamp": "2018-09-11T05:59:52.609",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "0080e840ee8fdbd4ec467519f1faf19fec",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735955497,
    "entry_timestamp": "2018-09-11T05:59:39.323",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "0080e840ee8fdbd4ec467519f1faf19fec",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735953276,
    "entry_timestamp": "2018-09-11T05:55:37.682",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "7d0b6a688f7ee77f9f172238fb7f5a83",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735953413,
    "entry_timestamp": "2018-09-11T05:55:20.56",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "7d0b6a688f7ee77f9f172238fb7f5a83",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735952715,
    "entry_timestamp": "2018-09-11T05:53:11.272",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "79a8ac8c08ca3ba224717a3bd6aed68c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735952639,
    "entry_timestamp": "2018-09-11T05:52:50.356",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "79a8ac8c08ca3ba224717a3bd6aed68c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735797428,
    "entry_timestamp": "2018-09-11T05:31:51.557",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00e52057ae97b29606c0bbb081dda060ad",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 735797504,
    "entry_timestamp": "2018-09-11T05:31:43.728",
    "not_before": "2018-09-11T00:00:00",
    "not_after": "2019-03-20T23:59:59",
    "serial_number": "00e52057ae97b29606c0bbb081dda060ad",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682159100,
    "entry_timestamp": "2018-08-27T08:11:12.662",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "6e9ea7ca0dc77fde76b9bcb33a75fbf8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682159076,
    "entry_timestamp": "2018-08-27T08:10:57.639",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "6e9ea7ca0dc77fde76b9bcb33a75fbf8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682155675,
    "entry_timestamp": "2018-08-27T08:08:22.74",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "7c212597d3f31c7840b409dcdabe70c8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682155432,
    "entry_timestamp": "2018-08-27T08:08:08.367",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "7c212597d3f31c7840b409dcdabe70c8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682153912,
    "entry_timestamp": "2018-08-27T08:01:11.699",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "50a3ed52b8f2e7ded252bf8dd330ed34",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682153696,
    "entry_timestamp": "2018-08-27T08:00:57.472",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "50a3ed52b8f2e7ded252bf8dd330ed34",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682150970,
    "entry_timestamp": "2018-08-27T07:58:31.703",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "00f8622a4bed3fffdc0cbbd36567ed651f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682151177,
    "entry_timestamp": "2018-08-27T07:58:18.357",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "00f8622a4bed3fffdc0cbbd36567ed651f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682150527,
    "entry_timestamp": "2018-08-27T07:54:50.517",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "3178510473bc391e108c7c9b4ce871b9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 682150568,
    "entry_timestamp": "2018-08-27T07:54:36.39",
    "not_before": "2018-08-27T00:00:00",
    "not_after": "2019-03-05T23:59:59",
    "serial_number": "3178510473bc391e108c7c9b4ce871b9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 662210932,
    "entry_timestamp": "2018-08-21T13:52:31.114",
    "not_before": "2018-08-21T00:00:00",
    "not_after": "2019-02-27T23:59:59",
    "serial_number": "3f8b3bc7aa443bf8baf6ea26b0304eae",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 662211044,
    "entry_timestamp": "2018-08-21T13:52:09.569",
    "not_before": "2018-08-21T00:00:00",
    "not_after": "2019-02-27T23:59:59",
    "serial_number": "3f8b3bc7aa443bf8baf6ea26b0304eae",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 522948986,
    "entry_timestamp": "2018-06-13T00:40:24.282",
    "not_before": "2018-06-13T00:00:00",
    "not_after": "2018-12-20T23:59:59",
    "serial_number": "1a20dca01adc4f8c3677f21480a4e22c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 522948170,
    "entry_timestamp": "2018-06-13T00:40:07.5",
    "not_before": "2018-06-13T00:00:00",
    "not_after": "2018-12-20T23:59:59",
    "serial_number": "1a20dca01adc4f8c3677f21480a4e22c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 507680834,
    "entry_timestamp": "2018-06-05T15:05:27.461",
    "not_before": "2018-06-05T00:00:00",
    "not_after": "2018-12-12T23:59:59",
    "serial_number": "120d41b5335f8bc77e31cd2136138fc9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 507680499,
    "entry_timestamp": "2018-06-05T15:05:11.978",
    "not_before": "2018-06-05T00:00:00",
    "not_after": "2018-12-12T23:59:59",
    "serial_number": "120d41b5335f8bc77e31cd2136138fc9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 482986551,
    "entry_timestamp": "2018-05-24T15:42:55.26",
    "not_before": "2018-05-24T00:00:00",
    "not_after": "2018-11-30T23:59:59",
    "serial_number": "00c679075e3e7e5c3353913b91bb56120d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 482985756,
    "entry_timestamp": "2018-05-24T15:42:25.236",
    "not_before": "2018-05-24T00:00:00",
    "not_after": "2018-11-30T23:59:59",
    "serial_number": "00c679075e3e7e5c3353913b91bb56120d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 470093029,
    "entry_timestamp": "2018-05-18T09:50:08.336",
    "not_before": "2018-05-18T00:00:00",
    "not_after": "2018-11-24T23:59:59",
    "serial_number": "0dd8f771343e017400d6171cd60eb344",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 470092871,
    "entry_timestamp": "2018-05-18T09:49:38.191",
    "not_before": "2018-05-18T00:00:00",
    "not_after": "2018-11-24T23:59:59",
    "serial_number": "0dd8f771343e017400d6171cd60eb344",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 466089226,
    "entry_timestamp": "2018-05-16T18:20:35.447",
    "not_before": "2018-05-16T00:00:00",
    "not_after": "2018-11-22T23:59:59",
    "serial_number": "00da3e1d45b252a8edc39255e57627d20c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 466088262,
    "entry_timestamp": "2018-05-16T18:19:56.097",
    "not_before": "2018-05-16T00:00:00",
    "not_after": "2018-11-22T23:59:59",
    "serial_number": "00da3e1d45b252a8edc39255e57627d20c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 382355039,
    "entry_timestamp": "2018-04-07T18:00:17.479",
    "not_before": "2018-04-06T00:00:00",
    "not_after": "2018-10-13T23:59:59",
    "serial_number": "01b2fd4ef9dfe1b34370badb11fcda46",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 379054415,
    "entry_timestamp": "2018-04-06T01:49:34.741",
    "not_before": "2018-04-06T00:00:00",
    "not_after": "2018-10-13T23:59:59",
    "serial_number": "01b2fd4ef9dfe1b34370badb11fcda46",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 378387757,
    "entry_timestamp": "2018-04-05T17:59:38.479",
    "not_before": "2018-04-04T00:00:00",
    "not_after": "2018-10-11T23:59:59",
    "serial_number": "579463f044b4d9a50ce41f66d226ed3f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 376478219,
    "entry_timestamp": "2018-04-04T04:38:50.254",
    "not_before": "2018-04-04T00:00:00",
    "not_after": "2018-10-11T23:59:59",
    "serial_number": "579463f044b4d9a50ce41f66d226ed3f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 375687159,
    "entry_timestamp": "2018-04-03T18:08:16.347",
    "not_before": "2018-04-02T00:00:00",
    "not_after": "2018-10-09T23:59:59",
    "serial_number": "00e38e5e86d052efb217dd43375d8fd213",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 373766681,
    "entry_timestamp": "2018-04-02T05:49:10.597",
    "not_before": "2018-04-02T00:00:00",
    "not_after": "2018-10-09T23:59:59",
    "serial_number": "00e38e5e86d052efb217dd43375d8fd213",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 293694129,
    "entry_timestamp": "2018-01-02T16:48:28.417",
    "not_before": "2018-01-02T00:00:00",
    "not_after": "2018-07-11T23:59:59",
    "serial_number": "1066d514f5dd6f6bbf691b6048cc441c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 276081514,
    "entry_timestamp": "2017-12-11T21:49:30.864",
    "not_before": "2017-12-11T00:00:00",
    "not_after": "2018-06-19T23:59:59",
    "serial_number": "00b1d23a04f3e0ed9a7508931eca237964",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 245976745,
    "entry_timestamp": "2017-11-02T11:40:51.026",
    "not_before": "2017-11-02T00:00:00",
    "not_after": "2018-05-11T23:59:59",
    "serial_number": "34332b261a46a326fdd5a18e31317700",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 244021914,
    "entry_timestamp": "2017-10-30T17:48:36.169",
    "not_before": "2017-10-30T00:00:00",
    "not_after": "2018-05-08T23:59:59",
    "serial_number": "7b5823ccee339333db3b97ac0acd0c2a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 231804574,
    "entry_timestamp": "2017-10-15T13:24:05.325",
    "not_before": "2017-10-15T00:00:00",
    "not_after": "2018-04-23T23:59:59",
    "serial_number": "7ba2682a1dcb92ee0893a0355493006c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 218782669,
    "entry_timestamp": "2017-09-27T10:28:09.087",
    "not_before": "2017-09-27T00:00:00",
    "not_after": "2018-04-05T23:59:59",
    "serial_number": "008799d8f6b28b18a1cb55aec913187008",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 213876716,
    "entry_timestamp": "2017-09-20T07:34:54.796",
    "not_before": "2017-09-19T00:00:00",
    "not_after": "2018-03-28T23:59:59",
    "serial_number": "00d53cc65d87c1aeb21dd124ae710aef56",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207619050,
    "entry_timestamp": "2017-09-10T14:00:20.574",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "0834c409e4cb7a5880a66a226dd29fe4",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207598662,
    "entry_timestamp": "2017-09-10T13:56:06.614",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "008aab2457df08d89e87866b598564e27c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207598348,
    "entry_timestamp": "2017-09-10T13:42:25.743",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00d1e80875f447eb017eb8a5319388d2e6",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207598234,
    "entry_timestamp": "2017-09-10T13:37:01.564",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "6d7d00c4769ac77c3e8a3734801d3f79",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207598051,
    "entry_timestamp": "2017-09-10T13:33:08.09",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00953f0352c118b08ca0ed6c83927afb80",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207587547,
    "entry_timestamp": "2017-09-10T13:25:14.202",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00b09fc9799a8a9c38ec680cc1ee998f6d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207586632,
    "entry_timestamp": "2017-09-10T13:18:29.23",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "11f339f03d5fcb2ac7749c00abf06438",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207585849,
    "entry_timestamp": "2017-09-10T13:13:02.084",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00b432c46ae4b357aee958721c67c8739a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207584776,
    "entry_timestamp": "2017-09-10T13:05:33.222",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00a5b1b60c1bb1a34a9e6213b8c9d5c1c1",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207583782,
    "entry_timestamp": "2017-09-10T13:00:15.07",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00cba08082dcbd28225c40c642fad4c938",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207563467,
    "entry_timestamp": "2017-09-10T12:53:12.016",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00f344ed427f713cad7ded59068c3b9208",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207562835,
    "entry_timestamp": "2017-09-10T12:40:22.682",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "63a2029609247596e8a7ef7a1a74bbd2",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207560941,
    "entry_timestamp": "2017-09-10T12:12:34.408",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "104e35c23c671cc3c6aa419cd58d8bca",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207560359,
    "entry_timestamp": "2017-09-10T12:08:13.745",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "00ee113da114303d0be2e058d83e7c8509",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207559601,
    "entry_timestamp": "2017-09-10T12:04:17.83",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "54ce8956c5849774dea351ebf4edce6f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 207540352,
    "entry_timestamp": "2017-09-10T11:59:35.793",
    "not_before": "2017-09-10T00:00:00",
    "not_after": "2018-03-19T23:59:59",
    "serial_number": "64d38f00dd6325c95b4130082952d538",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 202048503,
    "entry_timestamp": "2017-08-31T14:01:08.675",
    "not_before": "2017-08-31T00:00:00",
    "not_after": "2018-03-09T23:59:59",
    "serial_number": "00bfc8cb4bffee51338791cb3a298f92ac",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 198371343,
    "entry_timestamp": "2017-08-25T15:25:13.747",
    "not_before": "2017-08-25T00:00:00",
    "not_after": "2018-03-03T23:59:59",
    "serial_number": "009fe38cb483fcfe04890bfe1b9daf0190",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 192431320,
    "entry_timestamp": "2017-08-17T11:45:46.367",
    "not_before": "2017-08-17T00:00:00",
    "not_after": "2018-02-23T23:59:59",
    "serial_number": "00959788802af5e9a12ed8560f318db3aa",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 192406422,
    "entry_timestamp": "2017-08-17T11:00:08.579",
    "not_before": "2017-08-17T00:00:00",
    "not_after": "2018-02-23T23:59:59",
    "serial_number": "00e477d084866420596e2460c2841e7084",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 192273199,
    "entry_timestamp": "2017-08-17T06:42:01.381",
    "not_before": "2017-08-17T00:00:00",
    "not_after": "2018-02-23T23:59:59",
    "serial_number": "65f1a27cd1de0cc6c6978098658f8c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 171343712,
    "entry_timestamp": "2017-07-12T10:22:27.576",
    "not_before": "2017-07-12T00:00:00",
    "not_after": "2018-01-18T23:59:59",
    "serial_number": "00f2b20a0adce27d943865051d762b5746",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 167655060,
    "entry_timestamp": "2017-07-06T07:59:06.175",
    "not_before": "2017-07-06T00:00:00",
    "not_after": "2018-01-12T23:59:59",
    "serial_number": "7bdf5eb82fcc09fa34e7561fab0f39e7",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 166871058,
    "entry_timestamp": "2017-07-04T15:42:59.494",
    "not_before": "2017-07-04T00:00:00",
    "not_after": "2018-01-10T23:59:59",
    "serial_number": "00c503ac2c3a29f69f1b850346eb9a120d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 166860967,
    "entry_timestamp": "2017-07-04T15:38:39.787",
    "not_before": "2017-07-04T00:00:00",
    "not_after": "2018-01-10T23:59:59",
    "serial_number": "00acf55e004de6e7b46e4b4212d258b76a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 166860754,
    "entry_timestamp": "2017-07-04T15:34:40.383",
    "not_before": "2017-07-04T00:00:00",
    "not_after": "2018-01-10T23:59:59",
    "serial_number": "7148d251f4fa88cd5275236e8da5ff8a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 166765324,
    "entry_timestamp": "2017-07-04T13:06:18.941",
    "not_before": "2017-07-04T00:00:00",
    "not_after": "2018-01-10T23:59:59",
    "serial_number": "00e5ee4a4b5b3f61d7982df83ed0d9d381",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 150070909,
    "entry_timestamp": "2017-06-08T10:58:19.169",
    "not_before": "2017-06-08T00:00:00",
    "not_after": "2017-12-15T23:59:59",
    "serial_number": "7843d7774c0f18c4441675e464ceb301",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 142463648,
    "entry_timestamp": "2017-05-22T19:18:49.69",
    "not_before": "2017-05-22T00:00:00",
    "not_after": "2017-11-28T23:59:59",
    "serial_number": "27f308c2812b075031f1aa547d7c23ca",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 142383497,
    "entry_timestamp": "2017-05-22T15:20:11.967",
    "not_before": "2017-05-22T00:00:00",
    "not_after": "2017-11-28T23:59:59",
    "serial_number": "00c3cdb0567169be54a221a0f6cad774a1",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 141829609,
    "entry_timestamp": "2017-05-21T14:03:06.364",
    "not_before": "2017-05-21T00:00:00",
    "not_after": "2017-11-27T23:59:59",
    "serial_number": "008fe8ae07600fdfab5270c54354a1cdb5",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 139943425,
    "entry_timestamp": "2017-05-17T21:36:31.457",
    "not_before": "2017-05-17T00:00:00",
    "not_after": "2017-11-23T23:59:59",
    "serial_number": "671c3d09fc3a0b3efd8fe91f3d99f6c4",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 107867652,
    "entry_timestamp": "2017-03-23T05:03:57.034",
    "not_before": "2017-03-23T00:00:00",
    "not_after": "2017-09-29T23:59:59",
    "serial_number": "00b899c919cec54d84dddf1a2499a9b59d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 106684644,
    "entry_timestamp": "2017-03-20T11:56:17.01",
    "not_before": "2017-03-18T00:00:00",
    "not_after": "2017-09-24T23:59:59",
    "serial_number": "00dab370941ed46b53a37cd93be51a4a17",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 104894335,
    "entry_timestamp": "2017-03-17T03:19:58.975",
    "not_before": "2017-03-16T00:00:00",
    "not_after": "2017-09-22T23:59:59",
    "serial_number": "22bd6a4b0780d462426343d458f15b34",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 101508327,
    "entry_timestamp": "2017-03-11T11:54:29.992",
    "not_before": "2017-03-09T00:00:00",
    "not_after": "2017-09-15T23:59:59",
    "serial_number": "00a7fb3028319366522902b59ea3b4ec69",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 97668728,
    "entry_timestamp": "2017-02-28T11:42:20.917",
    "not_before": "2017-02-26T00:00:00",
    "not_after": "2017-08-06T23:59:59",
    "serial_number": "377dc1c563fd9801d4bb92a9bef3d78e",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 97264590,
    "entry_timestamp": "2017-02-27T11:37:36.469",
    "not_before": "2017-02-25T00:00:00",
    "not_after": "2017-08-06T23:59:59",
    "serial_number": "70e52dae926edec2ac7c208cbdcc3d46",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 72094534,
    "entry_timestamp": "2017-01-01T11:56:17.711",
    "not_before": "2016-12-30T00:00:00",
    "not_after": "2017-07-02T23:59:59",
    "serial_number": "6a24a5045283eb28871bb89478f2ee1d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 71548396,
    "entry_timestamp": "2016-12-29T16:03:49.382",
    "not_before": "2016-12-28T00:00:00",
    "not_after": "2017-07-02T23:59:59",
    "serial_number": "00cfe745c60a7210f1b631db996a0d4db0",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 57645552,
    "entry_timestamp": "2016-12-02T15:57:53.056",
    "not_before": "2016-11-30T00:00:00",
    "not_after": "2017-06-04T23:59:59",
    "serial_number": "332c3d4674b8c6af0770c95d00aa5a39",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 30515234,
    "entry_timestamp": "2016-09-01T11:33:04.733",
    "not_before": "2016-08-30T00:00:00",
    "not_after": "2017-03-05T23:59:59",
    "serial_number": "00edf74b886e0cb3aadb453f462ac3e97b",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 26404399,
    "entry_timestamp": "2016-07-31T11:09:39.207",
    "not_before": "2016-07-29T00:00:00",
    "not_after": "2017-01-29T23:59:59",
    "serial_number": "00e71fa5b184ba0b39b3991087caa76623",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 23825085,
    "entry_timestamp": "2016-07-05T12:27:43.906",
    "not_before": "2016-07-03T00:00:00",
    "not_after": "2017-01-08T23:59:59",
    "serial_number": "69d18c449406693f485960750942f52d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 23540475,
    "entry_timestamp": "2016-07-01T11:38:53.427",
    "not_before": "2016-06-29T00:00:00",
    "not_after": "2017-01-01T23:59:59",
    "serial_number": "00aac9fd413b4ef45033bfe464598e5b84",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 21123124,
    "entry_timestamp": "2016-06-05T11:13:35.565",
    "not_before": "2016-06-03T00:00:00",
    "not_after": "2016-12-04T23:59:59",
    "serial_number": "00c6584ebcdcef29325aec624e3306546c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20935627,
    "entry_timestamp": "2016-06-03T11:42:03.705",
    "not_before": "2016-06-01T00:00:00",
    "not_after": "2016-12-04T23:59:59",
    "serial_number": "598480f14a7f06b147ab431881c9ec5a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20552152,
    "entry_timestamp": "2016-05-31T11:10:25.852",
    "not_before": "2016-05-29T00:00:00",
    "not_after": "2016-12-04T23:59:59",
    "serial_number": "009ed7076fdcf475833092523cf0567ffd",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20448887,
    "entry_timestamp": "2016-05-29T11:43:34.3",
    "not_before": "2016-05-27T00:00:00",
    "not_after": "2016-11-27T23:59:59",
    "serial_number": "00a8a3a81037b5e63ea3d94bc9b8216ddc",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20324324,
    "entry_timestamp": "2016-05-27T11:30:03.989",
    "not_before": "2016-05-25T00:00:00",
    "not_after": "2016-11-27T23:59:59",
    "serial_number": "00ee2b6e79a69f4ea732c7aa36b15fb6ca",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20288136,
    "entry_timestamp": "2016-05-26T13:36:50.043",
    "not_before": "2016-05-24T00:00:00",
    "not_after": "2016-11-27T23:59:59",
    "serial_number": "21d50b46a2c6295807339b5b17bf3677",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 20259265,
    "entry_timestamp": "2016-05-26T11:43:52.295",
    "not_before": "2016-05-24T00:00:00",
    "not_after": "2016-11-27T23:59:59",
    "serial_number": "58d110bcbf7abee5ec1e3662fedb8e12",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 19998166,
    "entry_timestamp": "2016-05-23T11:31:36.047",
    "not_before": "2016-05-21T00:00:00",
    "not_after": "2016-11-27T23:59:59",
    "serial_number": "3de106081b52daabdf74ecdce879f4c6",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 19755740,
    "entry_timestamp": "2016-05-19T13:04:54.795",
    "not_before": "2016-05-17T00:00:00",
    "not_after": "2016-11-20T23:59:59",
    "serial_number": "65c7aecbf0eae2b163ed876fea0a4b59",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 19719544,
    "entry_timestamp": "2016-05-19T11:35:52.594",
    "not_before": "2016-05-18T00:00:00",
    "not_after": "2016-11-20T23:59:59",
    "serial_number": "68ad93099f53d97b31a1829fa6770272",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 15411683,
    "entry_timestamp": "2016-03-20T12:19:04.543",
    "not_before": "2016-03-18T00:00:00",
    "not_after": "2016-09-18T23:59:59",
    "serial_number": "00c41720e524a33f555b5c88c7c29ed3bc",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 14974797,
    "entry_timestamp": "2016-03-10T11:22:12.026",
    "not_before": "2016-03-08T00:00:00",
    "not_after": "2016-09-11T23:59:59",
    "serial_number": "0081ae1247d3a5bb02e6df1bdf926cc5c8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12924705,
    "entry_timestamp": "2016-02-14T12:58:20.433",
    "not_before": "2016-02-12T00:00:00",
    "not_after": "2016-08-14T23:59:59",
    "serial_number": "0204cfef1de57c36c0d7d5a66b715a01",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12580551,
    "entry_timestamp": "2016-02-04T12:12:57.982",
    "not_before": "2016-02-02T00:00:00",
    "not_after": "2016-08-07T23:59:59",
    "serial_number": "00923c214030846824b979f0b36df43482",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 12260286,
    "entry_timestamp": "2016-01-25T12:01:14.901",
    "not_before": "2016-01-23T00:00:00",
    "not_after": "2016-07-31T23:59:59",
    "serial_number": "00d137e7ca9336dfd16a7eb9eb420760e1",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 11666752,
    "entry_timestamp": "2015-12-25T12:04:03.252",
    "not_before": "2015-12-24T00:00:00",
    "not_after": "2016-06-26T23:59:59",
    "serial_number": "0415679683c69f696378370327e636c4",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 10426991,
    "entry_timestamp": "2015-10-31T18:28:21.843",
    "not_before": "2015-10-29T00:00:00",
    "not_after": "2016-04-24T23:59:59",
    "serial_number": "01aaa47a0b787140f6860e583913d7f8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 10253762,
    "entry_timestamp": "2015-10-21T16:01:10.163",
    "not_before": "2015-10-19T00:00:00",
    "not_after": "2015-12-30T23:59:59",
    "serial_number": "0089212c15f71a6c9f6f6aa1354de40e35",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9670108,
    "entry_timestamp": "2015-10-02T19:16:26.248",
    "not_before": "2015-09-30T00:00:00",
    "not_after": "2015-12-30T23:59:59",
    "serial_number": "78c516c7d13f0a567e012df90016f55f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9363473,
    "entry_timestamp": "2015-09-17T18:20:44.144",
    "not_before": "2015-09-15T00:00:00",
    "not_after": "2015-12-23T23:59:59",
    "serial_number": "00a8ddf4bc8919efdcf364ceb90e04d664",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9340920,
    "entry_timestamp": "2015-09-16T16:23:45.18",
    "not_before": "2015-09-14T00:00:00",
    "not_after": "2015-12-23T23:59:59",
    "serial_number": "00c90e4d7ce06376c04e6a16fb1f6a4d96",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 9262543,
    "entry_timestamp": "2015-09-11T17:03:02.168",
    "not_before": "2015-09-09T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "60bdae4669f94d6d94aa8d9723c6421d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8858579,
    "entry_timestamp": "2015-08-14T12:29:32.464",
    "not_before": "2015-08-12T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "7957fd23b4c3e0347a2117c954d21bc3",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8749057,
    "entry_timestamp": "2015-08-05T18:23:18.864",
    "not_before": "2015-08-03T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "008b662d383988f9f6cb7524a085841f06",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8333861,
    "entry_timestamp": "2015-07-06T18:51:36.906",
    "not_before": "2015-07-04T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "5ca08fe31294a573e335088afdfecea7",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8268473,
    "entry_timestamp": "2015-07-02T01:31:50.956",
    "not_before": "2015-06-29T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00f3f053d4d76d6914eefefe67ebb1be7b",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8123866,
    "entry_timestamp": "2015-06-21T17:32:51.18",
    "not_before": "2015-06-19T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "008cec3938cab5e63266694d3517278047",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8119256,
    "entry_timestamp": "2015-06-21T15:00:35.038",
    "not_before": "2015-06-19T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00c60631a5cf0e1fd1447d5adf2a50a64d",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8079970,
    "entry_timestamp": "2015-06-19T12:35:53.543",
    "not_before": "2015-06-17T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "009e4d79ea5e5b0ce0c58deefd2fc2b2f7",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8069819,
    "entry_timestamp": "2015-06-18T15:55:48.447",
    "not_before": "2015-06-16T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00d64612d6c1d45dc5fad48d72f1e7af69",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8041374,
    "entry_timestamp": "2015-06-16T21:58:31.677",
    "not_before": "2015-06-14T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "008955d8b33cd0e760299b976440fdb1cc",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 8008621,
    "entry_timestamp": "2015-06-14T13:09:34.146",
    "not_before": "2015-06-12T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "009036b64eb03947732d79d75eaf614699",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7918527,
    "entry_timestamp": "2015-06-07T18:46:18.986",
    "not_before": "2015-06-05T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "4a3f64b6d2c3f108278c9278602a2298",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7789445,
    "entry_timestamp": "2015-05-29T22:22:05.995",
    "not_before": "2015-05-27T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00ffb8f2dafff9e6b48ae3c1c77a2227c3",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7755360,
    "entry_timestamp": "2015-05-27T18:34:22.169",
    "not_before": "2015-05-25T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00ccf583c2f0e6d6eea6362f4de4272fad",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7753857,
    "entry_timestamp": "2015-05-27T17:52:04.894",
    "not_before": "2015-05-25T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "5d09fd6cc9de06b038ca5105b09ac7cc",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7748633,
    "entry_timestamp": "2015-05-27T13:01:27.056",
    "not_before": "2015-05-25T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "48da0d1ed677f94267a4f0b6c6a2d059",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7641239,
    "entry_timestamp": "2015-05-20T18:24:20.035",
    "not_before": "2015-05-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00e215316ab7288b4247aaad95fd2ce528",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7639282,
    "entry_timestamp": "2015-05-20T17:18:08.4",
    "not_before": "2015-05-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "2717e13e11eac9c67bffb1d402043b75",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7617846,
    "entry_timestamp": "2015-05-20T11:34:59.03",
    "not_before": "2015-05-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "25a6b1014994bd688b39805804d4115c",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7563768,
    "entry_timestamp": "2015-05-18T17:43:14.142",
    "not_before": "2015-05-16T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00e9db7aaf056e09847e9ca31b768607b9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7541712,
    "entry_timestamp": "2015-05-16T18:19:42.305",
    "not_before": "2015-05-14T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "008528eaf9de880f41e8750b58ec92bcd5",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7493639,
    "entry_timestamp": "2015-05-14T13:28:29.87",
    "not_before": "2015-05-12T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "4ce90a7d6aede5b11443998efc4bdcd2",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7486672,
    "entry_timestamp": "2015-05-13T12:57:19.941",
    "not_before": "2015-05-10T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00e010a97f089ef3a8e82e15a5b838e6d3",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7412543,
    "entry_timestamp": "2015-05-07T13:57:33.403",
    "not_before": "2015-05-05T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "5ab1418a2cea0cceee5103374a3bf522",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7396439,
    "entry_timestamp": "2015-05-04T11:23:24.688",
    "not_before": "2015-05-02T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00db049cdda1d551ce5d7c53a3dc2ceafb",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7352839,
    "entry_timestamp": "2015-04-30T12:09:37.752",
    "not_before": "2015-04-28T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00e080de403b19cd4efba351e6f5d3b8c8",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 7142876,
    "entry_timestamp": "2015-04-11T18:26:09.026",
    "not_before": "2015-04-09T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00faf546b52252a2c06aa65c133c97ece3",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6973281,
    "entry_timestamp": "2015-03-28T16:11:11.947",
    "not_before": "2015-03-26T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00c3258abdd665ff88ba5fecbe75a31802",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6802048,
    "entry_timestamp": "2015-03-13T14:30:21.49",
    "not_before": "2015-03-11T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "0081c57019a6ae37a51e4f026deebee14b",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6765416,
    "entry_timestamp": "2015-03-10T12:28:48.431",
    "not_before": "2015-03-09T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "623f413473d5f955ad0f27e25b38591a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6603720,
    "entry_timestamp": "2015-02-22T14:58:47.922",
    "not_before": "2015-02-20T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "2aaf34f76a87d8ada1917e0e72a0c807",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6585115,
    "entry_timestamp": "2015-02-20T15:09:08.507",
    "not_before": "2015-02-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "2fbd3cd2bfddab2369a02a3758f2fd51",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6370601,
    "entry_timestamp": "2015-01-31T18:09:35.392",
    "not_before": "2015-01-29T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00f215b26d687acdd979d227e1cba2f82e",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6349098,
    "entry_timestamp": "2015-01-29T18:53:40.174",
    "not_before": "2015-01-27T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00d4e5fc2c5953eedb976e3da087423cbb",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6320622,
    "entry_timestamp": "2015-01-27T01:45:34.189",
    "not_before": "2015-01-24T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "55a7daf548fafb3836027966b026c66b",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6317719,
    "entry_timestamp": "2015-01-26T16:04:56.624",
    "not_before": "2015-01-24T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00c5901be9b736b07964bfcb01eb716c85",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6294333,
    "entry_timestamp": "2015-01-24T13:34:59.442",
    "not_before": "2015-01-22T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00f05fc88395dc9e6423cb66e5e8394de0",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6258656,
    "entry_timestamp": "2015-01-21T12:50:13.94",
    "not_before": "2015-01-19T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "53e638e254e0b3f1e2a09aa5cec5165f",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6251507,
    "entry_timestamp": "2015-01-20T15:35:56.14",
    "not_before": "2015-01-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "0595996ab37aadde350315d5f5e4bbd9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6243585,
    "entry_timestamp": "2015-01-19T14:04:11.608",
    "not_before": "2015-01-17T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "5b4d7b13ac4e515840485eb678c29d22",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6166986,
    "entry_timestamp": "2015-01-11T16:12:00.818",
    "not_before": "2015-01-07T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "008d2699f3b1b4735f1dcb926954e7e5fd",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 6043362,
    "entry_timestamp": "2014-12-26T15:54:43.09",
    "not_before": "2014-12-24T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "4f087b4f8980c6eadaa5c824dfffb87a",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5992816,
    "entry_timestamp": "2014-12-20T16:52:12.749",
    "not_before": "2014-12-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "430a2cb0ec9a5cbc9c0790bb56de3999",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5985009,
    "entry_timestamp": "2014-12-20T12:10:37.884",
    "not_before": "2014-12-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00f035af5cccdf3c25db3eeb97f44c2721",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5843711,
    "entry_timestamp": "2014-12-10T13:22:35.875",
    "not_before": "2014-12-08T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00950845c5b7cffff0bb86d9e286bfad44",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5812544,
    "entry_timestamp": "2014-12-06T15:33:09.43",
    "not_before": "2014-12-03T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "59186508538323f96cb6c18748c5bae7",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5794058,
    "entry_timestamp": "2014-12-05T00:29:07.356",
    "not_before": "2014-12-02T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "685d135ae4d0aa9338b56fd8f5669ce2",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5768647,
    "entry_timestamp": "2014-12-02T13:23:12.033",
    "not_before": "2014-11-30T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "4d37bafc5394e873338041c4c6e511dc",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5713500,
    "entry_timestamp": "2014-11-26T15:28:51.243",
    "not_before": "2014-11-24T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00b7ad1a17ebcf2a95d0a74932ca46b609",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5673550,
    "entry_timestamp": "2014-11-22T12:31:06.206",
    "not_before": "2014-11-20T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "57a41b21b0ea90c94e923f7601c5f803",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5665489,
    "entry_timestamp": "2014-11-21T16:28:53.241",
    "not_before": "2014-11-18T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00b6cb9fe4b92a9d3a977418d9fcc6b9d9",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5541382,
    "entry_timestamp": "2014-11-09T16:17:19.048",
    "not_before": "2014-11-07T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00d4afb6dfa5da6fa0fe4cddf66cd6959e",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5479672,
    "entry_timestamp": "2014-11-05T11:47:23.18",
    "not_before": "2014-11-03T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00fc0bc364af824e6a5ff4353f984d5388",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5456493,
    "entry_timestamp": "2014-11-02T13:35:01.367",
    "not_before": "2014-10-30T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00c52b4364f48314b27d65535a35668b59",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5446873,
    "entry_timestamp": "2014-11-01T15:03:46.661",
    "not_before": "2014-10-29T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00efdca32ce16aac94784c1b6011b7b1da",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5361004,
    "entry_timestamp": "2014-10-24T16:25:33.446",
    "not_before": "2014-10-20T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00d06cc30ae2790f06ff27fbe54fba3cd6",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5279571,
    "entry_timestamp": "2014-10-17T13:41:36.907",
    "not_before": "2014-10-15T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00c67a66e872f04732f2ed52d53041ff33",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5201928,
    "entry_timestamp": "2014-10-09T20:54:09.757",
    "not_before": "2014-10-07T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "7a46e8702cb4f66a9a488c467cec3432",
    "result_count": 2
  },
  {
    "issuer_ca_id": 1582,
    "issuer_name": "C=GB, ST=Greater Manchester, L=Salford, O=COMODO CA Limited, CN=COMODO ECC Domain Validation Secure Server CA 2",
    "common_name": "sni54496.cloudflaressl.com",
    "name_value": "*.nob.ro\nnob.ro",
    "id": 5182005,
    "entry_timestamp": "2014-10-08T14:58:28.547",
    "not_before": "2014-10-03T00:00:00",
    "not_after": "2015-09-30T23:59:59",
    "serial_number": "00d4319145842eb95e4f2eb3c58ca8a914",
    "result_count": 2
  }
]

--- PARSED SUBDOMAINS ---
n8n8n.nob.ro
nob.ro

STDERR:

```

---

| 57954b9d | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 57954b9d | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#57954b9d) |

### Detailed Result: 57954b9d

- **Target:** nob.ro
- **Justification:** The user requested a more comprehensive subdomain scan. This action lists the available DNS wordlists within the SecLists directory on the agent to identify a larger and more thorough wordlist to use for the next active scan.
- **Command:** `import os; print(os.listdir('/usr/share/seclists/Discovery/DNS/'))`

#### Raw Output

```
STDOUT:
['dns-Jhaddix.txt', 'deepmagic.com-prefixes-top500.txt', 'fierce-hostlist.txt', 'subdomains-top1million-5000.txt', 'namelist.txt', 'FUZZSUBS_CYFARE_1.txt', 'bug-bounty-program-subdomains-trickest-inventory.txt', 'FUZZSUBS_CYFARE_2.txt', 'italian-subdomains.txt', 'bitquark-subdomains-top100000.txt', 'shubs-stackoverflow.txt', 'n0kovo_subdomains.txt', 'README.md', 'subdomains-top1million-20000.txt', 'combined_subdomains.txt', 'tlds.txt', 'shubs-subdomains.txt', 'sortedcombined-knock-dnsrecon-fierce-reconng.txt', 'services-names.txt', 'subdomains-top1million-110000.txt', 'subdomains-spanish.txt', 'deepmagic.com-prefixes-top50000.txt']

STDERR:

```

---

| 3778a9e1 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 3778a9e1 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#3778a9e1) |

### Detailed Result: 3778a9e1

- **Target:** nob.ro
- **Justification:** Based on user feedback, this action performs a more thorough active subdomain scan using a larger wordlist (`subdomains-top1million-110000.txt`). It will also re-run the passive scan to ensure the previously missed subdomain from crt.sh is included in the final results.
- **Command:** `
from skills.subdomain import SubdomainSkill
import json

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Define the comprehensive wordlist to use
comprehensive_wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"

# Run the skill in active mode with the specified wordlist
results = skill.run(mode="active", wordlist=comprehensive_wordlist)

# Print the results in a structured way for the report
print("--- Comprehensive Active Subdomain Enumeration ---")
print(f"Target: {results.get('target')}")
print(f"Wordlist: {comprehensive_wordlist}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")
print(f"Found an additional {results.get('active_found', 0)} subdomains via active brute-force.")

print("\n--- Found Subdomains ---")
for sub in results.get('subdomains', []):
    print(sub)

# Save the full JSON results as an artifact
skill.save_json(f"subdomains_{results.get('target')}_active_comprehensive.json", results)
print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
[*] Querying crt.sh for nob.ro...
[*] Running gobuster DNS for nob.ro...
[!] Wildcard DNS detected (127.0.0.1). Enabling --wildcard mode.
--- Comprehensive Active Subdomain Enumeration ---
Target: nob.ro
Wordlist: /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt
Found 2 subdomains via crt.sh.
Found an additional 0 subdomains via active brute-force.

--- Found Subdomains ---
n8n8n.nob.ro
nob.ro

Full JSON results saved to artifact.

STDERR:

```

---

| cadd8f5a | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| cadd8f5a | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#cadd8f5a) |

### Detailed Result: cadd8f5a

- **Target:** nob.ro
- **Justification:** Per user request, this action reruns the comprehensive active subdomain scan for 'nob.ro' using the 'subdomains-top1million-110000.txt' wordlist. This explicitly addresses the user's concern about wildcard subdomains by leveraging the built-in filtering logic of the SubdomainSkill.
- **Command:** `
from skills.subdomain import SubdomainSkill
import json

# Initialize the skill with the target domain
skill = SubdomainSkill(target="nob.ro")

# Define the comprehensive wordlist to use
comprehensive_wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"

# Run the skill in active mode with the specified wordlist
results = skill.run(mode="active", wordlist=comprehensive_wordlist)

# Print the results in a structured way for the report
print("--- Comprehensive Active Subdomain Enumeration (Re-run) ---")
print(f"Target: {results.get('target')}")
print(f"Wordlist: {comprehensive_wordlist}")
print(f"Found {results.get('passive_count', 0)} subdomains via crt.sh.")
print(f"Found an additional {results.get('active_found', 0)} subdomains via active brute-force.")

print("\n--- Found Subdomains ---")
for sub in results.get('subdomains', []):
    print(sub)

# Save the full JSON results as an artifact
skill.save_json(f"subdomains_{results.get('target')}_active_comprehensive_rerun.json", results)
print("\nFull JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
[*] Querying crt.sh for nob.ro...
[*] Running gobuster DNS for nob.ro...
[!] Wildcard DNS detected (127.0.0.1). Enabling --wildcard mode.
--- Comprehensive Active Subdomain Enumeration (Re-run) ---
Target: nob.ro
Wordlist: /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt
Found 2 subdomains via crt.sh.
Found an additional 0 subdomains via active brute-force.

--- Found Subdomains ---
nob.ro
n8n8n.nob.ro

Full JSON results saved to artifact.

STDERR:

```

---

| e7fec59a | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| e7fec59a | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#e7fec59a) |

### Detailed Result: e7fec59a

- **Target:** nob.ro
- **Justification:** Per user request, this action attempts subdomain enumeration using `ffuf` with a comprehensive wordlist. It also includes a preliminary step to determine the wildcard response size to accurately filter out false positives from `ffuf`'s output, addressing the user's specific concern about wildcard subdomains. The passive crt.sh scan is also included to provide a complete picture.
- **Command:** `
import os
import json
import subprocess
import requests
import uuid
import re

domain = "nob.ro"
comprehensive_wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"
found_subdomains = set()

print(f"--- FFUF Subdomain Enumeration for {domain} ---")

# 1. Passive Recon (crt.sh)
print("[*] Performing passive reconnaissance with crt.sh...")
url = f"https://crt.sh/?q=%.{domain}&output=json"
try:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    for entry in data:
        name = entry.get("name_value", "")
        for sub in name.split():
            if "*" not in sub:
                found_subdomains.add(sub.strip())
except requests.exceptions.RequestException as e:
    print(f"[!] crt.sh query failed: {e}")
except json.JSONDecodeError:
    print("[!] Failed to decode JSON response from crt.sh.")

print(f"Found {len(found_subdomains)} subdomains from crt.sh.")

# 2. Determine wildcard response size for ffuf filtering
print("[*] Determining wildcard response size for FFUF...")
random_sub = f"{uuid.uuid4().hex[:10]}.{domain}"
test_url = f"http://{random_sub}" # Using http as ffuf will check both http and https by default
# We need to get the actual response size from the server for a non-existent domain.
# FFUF can report different sizes. Let's run ffuf once on a random subdomain.
ffuf_test_cmd = [
    "ffuf",
    "-u", f"http://{random_sub}",
    "-H", f"Host: {random_sub}.{domain}",
    "-mc", "all",
    "-s" # Silent mode, only print results (we will parse JSON)
]
try:
    test_result = subprocess.run(ffuf_test_cmd, capture_output=True, text=True, timeout=60, check=True)
    # The output from ffuf -s is usually empty if no valid response.
    # We need to get the size for a non-existent subdomain.
    # A trick is to use -o and -of json to get the details
    ffuf_test_cmd_json = [
        "ffuf",
        "-u", f"http://{random_sub}",
        "-H", f"Host: {random_sub}.{domain}",
        "-mc", "all",
        "-o", "/tmp/ffuf_test_output.json",
        "-of", "json"
    ]
    subprocess.run(ffuf_test_cmd_json, capture_output=True, text=True, timeout=60, check=True)
    with open("/tmp/ffuf_test_output.json", "r") as f:
        ffuf_test_data = json.load(f)
    
    wildcard_size = None
    if ffuf_test_data and "results" in ffuf_test_data and len(ffuf_test_data["results"]) > 0:
        wildcard_size = ffuf_test_data["results"][0].get("length")
        print(f"Wildcard response size determined: {wildcard_size}")
    else:
        print("Could not determine wildcard response size. Proceeding without -fs filter (may be noisy).")

except subprocess.CalledProcessError as e:
    print(f"[!] FFUF wildcard test failed: {e.stderr}")
    wildcard_size = None
except Exception as e:
    print(f"[!] Error during FFUF wildcard test: {e}")
    wildcard_size = None

# 3. Active FFUF scan for subdomains
print(f"[*] Starting FFUF active scan with wordlist: {comprehensive_wordlist}")
ffuf_cmd = [
    "ffuf",
    "-w", comprehensive_wordlist,
    "-u", f"http://FUZZ.{domain}",
    "-H", f"Host: FUZZ.{domain}",
    "-mc", "all", # Match all status codes, filtering by size
    "-o", "/loot/ffuf_subdomains.json",
    "-of", "json",
    "-t", "50" # Threads
]
if wildcard_size is not None:
    ffuf_cmd.extend(["-fs", str(wildcard_size)])
else:
    print("WARNING: No wildcard size to filter. FFUF results may contain many false positives.")

try:
    subprocess.run(ffuf_cmd, capture_output=True, text=True, timeout=600, check=True)
    
    ffuf_results = []
    with open("/loot/ffuf_subdomains.json", "r") as f:
        ffuf_data = json.load(f)
        if "results" in ffuf_data:
            for result in ffuf_data["results"]:
                subdomain = result.get("input", {}).get("FUZZ")
                if subdomain:
                    full_sub = f"{subdomain}.{domain}"
                    if full_sub not in found_subdomains:
                        ffuf_results.append(full_sub)
                        found_subdomains.add(full_sub)

    print(f"Found {len(ffuf_results)} additional subdomains via FFUF.")

except subprocess.CalledProcessError as e:
    print(f"[!] FFUF scan failed: {e.stderr}")
except Exception as e:
    print(f"[!] Error during FFUF scan: {e}")

# 4. Report findings
print("\n--- Consolidated Subdomain Results ---")
print(f"Target: {domain}")
print(f"Total Unique Subdomains Found: {len(found_subdomains)}")
for sub in sorted(list(found_subdomains)):
    print(sub)

# Save all results
final_results_dict = {
    "target": domain,
    "passive_sources": ["crt.sh"],
    "active_tool": "ffuf",
    "wordlist": comprehensive_wordlist,
    "subdomains": sorted(list(found_subdomains))
}
with open(f"/loot/consolidated_subdomains_{domain}.json", "w") as f:
    json.dump(final_results_dict, f, indent=2)
print("\nConsolidated JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
--- FFUF Subdomain Enumeration for nob.ro ---
[*] Performing passive reconnaissance with crt.sh...
Found 2 subdomains from crt.sh.
[*] Determining wildcard response size for FFUF...
[!] FFUF wildcard test failed: Encountered error(s): 1 errors occurred.
	* Either -w or --input-cmd flag is required

Encountered error(s): 1 errors occurred.
	* Either -w or --input-cmd flag is required


[*] Starting FFUF active scan with wordlist: /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt
WARNING: No wildcard size to filter. FFUF results may contain many false positives.
[!] Error during FFUF scan: Command '['ffuf', '-w', '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt', '-u', 'http://FUZZ.nob.ro', '-H', 'Host: FUZZ.nob.ro', '-mc', 'all', '-o', '/loot/ffuf_subdomains.json', '-of', 'json', '-t', '50']' timed out after 600 seconds

--- Consolidated Subdomain Results ---
Target: nob.ro
Total Unique Subdomains Found: 2
n8n8n.nob.ro
nob.ro

Consolidated JSON results saved to artifact.

STDERR:

```

---

| 174bcf50 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 174bcf50 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#174bcf50) |

### Detailed Result: 174bcf50

- **Target:** nob.ro
- **Justification:** This action re-attempts subdomain enumeration for 'nob.ro' using `ffuf` with a comprehensive wordlist, addressing the previous wildcard filtering failure. The Python script has been corrected to properly determine the wildcard response size using `ffuf`'s stdin wordlist option, ensuring accurate filtering and avoiding timeouts from excessive false positives.
- **Command:** `
import os
import json
import subprocess
import requests
import uuid
import re

domain = "nob.ro"
comprehensive_wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"
found_subdomains = set()

print(f"--- FFUF Subdomain Enumeration for {domain} ---")

# 1. Passive Recon (crt.sh)
print("[*] Performing passive reconnaissance with crt.sh...")
url = f"https://crt.sh/?q=%.{domain}&output=json"
try:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    for entry in data:
        name = entry.get("name_value", "")
        for sub in name.split():
            if "*" not in sub:
                found_subdomains.add(sub.strip())
except requests.exceptions.RequestException as e:
    print(f"[!] crt.sh query failed: {e}")
except json.JSONDecodeError:
    print("[!] Failed to decode JSON response from crt.sh.")

print(f"Found {len(found_subdomains)} subdomains from crt.sh.")

# 2. Determine wildcard response size for ffuf filtering
print("[*] Determining wildcard response size for FFUF...")
random_sub_fuzz_part = f"{uuid.uuid4().hex[:10]}" # Just the fuzzed part
test_host = f"{random_sub_fuzz_part}.{domain}"
ffuf_test_cmd_json = [
    "ffuf",
    "-w", "-", # Read wordlist from stdin
    "-u", f"http://{test_host}",
    "-H", f"Host: {test_host}",
    "-mc", "all",
    "-o", "/tmp/ffuf_test_output.json",
    "-of", "json"
]
wildcard_size = None
try:
    process = subprocess.Popen(ffuf_test_cmd_json, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Provide one "FUZZ" word via stdin to satisfy -w -
    stdout, stderr = process.communicate(input="FUZZ\n", timeout=60) 
    
    if process.returncode != 0:
        print(f"[!] FFUF wildcard test failed: {stderr}")
    else:
        with open("/tmp/ffuf_test_output.json", "r") as f:
            ffuf_test_data = json.load(f)
        
        if ffuf_test_data and "results" in ffuf_test_data and len(ffuf_test_data["results"]) > 0:
            wildcard_size = ffuf_test_data["results"][0].get("length")
            print(f"Wildcard response size determined: {wildcard_size}")
        else:
            print("Could not determine wildcard response size. Proceeding without -fs filter (may be noisy).")

except subprocess.TimeoutExpired:
    process.kill()
    print("[!] FFUF wildcard test timed out.")
except Exception as e:
    print(f"[!] Error during FFUF wildcard test: {e}")

# 3. Active FFUF scan for subdomains
print(f"[*] Starting FFUF active scan with wordlist: {comprehensive_wordlist}")
ffuf_cmd = [
    "ffuf",
    "-w", comprehensive_wordlist,
    "-u", f"http://FUZZ.{domain}",
    "-H", f"Host: FUZZ.{domain}",
    "-mc", "all", # Match all status codes, filtering by size
    "-o", "/loot/ffuf_subdomains.json",
    "-of", "json",
    "-t", "50" # Threads
]
if wildcard_size is not None:
    ffuf_cmd.extend(["-fs", str(wildcard_size)])
else:
    print("WARNING: No wildcard size to filter. FFUF results may contain many false positives.")

try:
    subprocess.run(ffuf_cmd, capture_output=True, text=True, timeout=1200, check=True) # Increased timeout
    
    ffuf_results_from_file = []
    with open("/loot/ffuf_subdomains.json", "r") as f:
        ffuf_data = json.load(f)
        if "results" in ffuf_data:
            for result in ffuf_data["results"]:
                subdomain = result.get("input", {}).get("FUZZ")
                if subdomain:
                    full_sub = f"{subdomain}.{domain}"
                    if full_sub not in found_subdomains:
                        ffuf_results_from_file.append(full_sub)
                        found_subdomains.add(full_sub)

    print(f"Found {len(ffuf_results_from_file)} additional subdomains via FFUF.")

except subprocess.CalledProcessError as e:
    print(f"[!] FFUF scan failed: {e.stderr}")
except Exception as e:
    print(f"[!] Error during FFUF scan: {e}")

# 4. Report findings
print("\n--- Consolidated Subdomain Results ---")
print(f"Target: {domain}")
print(f"Total Unique Subdomains Found: {len(found_subdomains)}")
for sub in sorted(list(found_subdomains)):
    print(sub)

# Save all results
final_results_dict = {
    "target": domain,
    "passive_sources": ["crt.sh"],
    "active_tool": "ffuf",
    "wordlist": comprehensive_wordlist,
    "subdomains": sorted(list(found_subdomains))
}
with open(f"/loot/consolidated_subdomains_{domain}.json", "w") as f:
    json.dump(final_results_dict, f, indent=2)
print("\nConsolidated JSON results saved to artifact.")
`

#### Raw Output

```
STDOUT:
--- FFUF Subdomain Enumeration for nob.ro ---
[*] Performing passive reconnaissance with crt.sh...
Found 2 subdomains from crt.sh.
[*] Determining wildcard response size for FFUF...
Wildcard response size determined: 372
[*] Starting FFUF active scan with wordlist: /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt
[!] Error during FFUF scan: Command '['ffuf', '-w', '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt', '-u', 'http://FUZZ.nob.ro', '-H', 'Host: FUZZ.nob.ro', '-mc', 'all', '-o', '/loot/ffuf_subdomains.json', '-of', 'json', '-t', '50', '-fs', '372']' timed out after 1200 seconds

--- Consolidated Subdomain Results ---
Target: nob.ro
Total Unique Subdomains Found: 2
n8n8n.nob.ro
nob.ro

Consolidated JSON results saved to artifact.

STDERR:

```

---

| 8252f1cd | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 8252f1cd | reconnaissance | nob.ro | analysis | FAILED | [Failed](#8252f1cd) |

### Detailed Result: 8252f1cd

- **Target:** nob.ro
- **Justification:** The user explicitly stated that 'testing.nob.ro' is an existing subdomain. This action will perform a direct DNS lookup to confirm its existence and retrieve its IP address, bypassing previous enumeration failures.
- **Command:** `host testing.nob.ro`

#### Raw Output

```
Python Execution Failed:
Traceback (most recent call last):
  File "/usr/local/bin/kali-operator", line 152, in execute_action
    exec(command, exec_globals)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 1
    host testing.nob.ro
         ^^^^^^^
SyntaxError: invalid syntax

```

---

| 9d854a24 | reconnaissance | nob.ro | analysis | QUEUED | Pending |
| 9d854a24 | reconnaissance | nob.ro | analysis | COMPLETED | [Success](#9d854a24) |

### Detailed Result: 9d854a24

- **Target:** nob.ro
- **Justification:** Correcting the previous error where a shell command was directly provided to an `analysis` action. This action now properly wraps the `host` command within a Python subprocess call to confirm the existence of 'testing.nob.ro' as stated by the user.
- **Command:** `
import subprocess

target_subdomain = "testing.nob.ro"
print(f"[*] Performing DNS lookup for: {target_subdomain}")
try:
    result = subprocess.run(
        ["host", target_subdomain],
        capture_output=True,
        text=True,
        timeout=10,
        check=True
    )
    print("\n--- HOST COMMAND OUTPUT ---")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(f"[!] Host command failed: {e.stderr}")
except subprocess.TimeoutExpired:
    print(f"[!] Host command timed out for {target_subdomain}.")
except Exception as e:
    print(f"[!] An error occurred: {e}")
`

#### Raw Output

```
STDOUT:
[*] Performing DNS lookup for: testing.nob.ro

--- HOST COMMAND OUTPUT ---
testing.nob.ro has address 172.67.134.103
testing.nob.ro has address 104.21.25.169
testing.nob.ro has IPv6 address 2606:4700:3033::ac43:8667
testing.nob.ro has IPv6 address 2606:4700:3034::6815:19a9
testing.nob.ro has HTTP service bindings 1 . alpn="h3,h2" ipv4hint=104.21.25.169,172.67.134.103 ech=AEX+DQBBZQAgACBq79PCrwZNPaOeldIulFIpPIKDzC22z2TXGmI4UleMRgAEAAEAAQASY2xvdWRmbGFyZS1lY2guY29tAAA= ipv6hint=2606:4700:3033::ac43:8667,2606:4700:3034::6815:19a9


STDERR:

```

---

| 12973783 | reconnaissance | testing.nob.ro | network_scan | QUEUED | Pending |
| 12973783 | reconnaissance | testing.nob.ro | network_scan | COMPLETED | [Success](#12973783) |

### Detailed Result: 12973783

- **Target:** testing.nob.ro
- **Justification:** Following the user's directive to perform reconnaissance on the newly confirmed 'testing.nob.ro' subdomain, this action uses nmap to conduct a TCP connect scan, service version detection, and default script scanning to identify open ports and running services. The output is saved as an XML artifact for structured analysis.
- **Command:** `nmap -sT -sV -sC -oX /loot/testing_nob_ro_scan.xml testing.nob.ro`

#### Findings

```json
:
{
  "testing_nob_ro_scan.xml": [
    {
      "ip": "172.67.134.103",
      "ports": [
        {
          "id": 80,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "version": "",
          "product": "Cloudflare http proxy"
        },
        {
          "id": 443,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "version": "",
          "product": "Cloudflare http proxy"
        },
        {
          "id": 8080,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "version": "",
          "product": "Cloudflare http proxy"
        },
        {
          "id": 8443,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "version": "",
          "product": "Cloudflare http proxy"
        }
      ]
    }
  ]
}

[ARTIFACTS]:
/loot/testing_nob_ro_scan.xml
```

#### Raw Output

<details><summary>Click to expand</summary>

```
Exit Code: 0

STDOUT:
Starting Nmap 7.98 ( https://nmap.org ) at 2026-02-26 12:21 +0000
Nmap scan report for testing.nob.ro (172.67.134.103)
Host is up (0.0082s latency).
Other addresses for testing.nob.ro (not scanned): 104.21.25.169 2606:4700:3033::ac43:8667 2606:4700:3034::6815:19a9
Not shown: 996 filtered tcp ports (no-response)
PORT     STATE SERVICE  VERSION
80/tcp   open  http     Cloudflare http proxy
|_http-title: Attention Required! | Cloudflare
|_http-server-header: cloudflare
443/tcp  open  ssl/http Cloudflare http proxy
|_http-server-header: cloudflare
|_http-title: Attention Required! | Cloudflare
| ssl-cert: Subject: commonName=nob.ro
| Subject Alternative Name: DNS:nob.ro, DNS:*.nob.ro
| Not valid before: 2026-01-28T08:43:33
|_Not valid after:  2026-04-28T09:40:50
8080/tcp open  http     Cloudflare http proxy
|_http-server-header: cloudflare
|_http-title: Attention Required! | Cloudflare
8443/tcp open  ssl/http Cloudflare http proxy
|_http-title: Attention Required! | Cloudflare
|_http-server-header: cloudflare
| ssl-cert: Subject: commonName=nob.ro
| Subject Alternative Name: DNS:nob.ro, DNS:*.nob.ro
| Not valid before: 2026-01-28T08:43:33
|_Not valid after:  2026-04-28T09:40:50

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 22.91 seconds


STDERR:
```

</details>

---

| d8286a39 | enumeration | testing.nob.ro | analysis | QUEUED | Pending |
| d8286a39 | enumeration | testing.nob.ro | analysis | FAILED | [Failed](#d8286a39) |

### Detailed Result: d8286a39

- **Target:** testing.nob.ro
- **Justification:** To perform a web probe using ffuf, an appropriate wordlist is required for content discovery. This action lists the available wordlists in the designated SecLists directory to allow for selection of the most suitable list.
- **Command:** `ls -F /usr/share/seclists/Discovery/Web-Content/`

#### Raw Output

```
Python Execution Failed:
Traceback (most recent call last):
  File "/usr/local/bin/kali-operator", line 152, in execute_action
    exec(command, exec_globals)
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 1
    ls -F /usr/share/seclists/Discovery/Web-Content/
                                                    ^
SyntaxError: invalid syntax

```

---

| 7ed4a452 | enumeration | testing.nob.ro | analysis | QUEUED | Pending |
| 7ed4a452 | enumeration | testing.nob.ro | analysis | COMPLETED | [Success](#7ed4a452) |

### Detailed Result: 7ed4a452

- **Target:** testing.nob.ro
- **Justification:** Correcting the previous error, this action now properly wraps the `ls -F` command within a Python subprocess call to list available web content discovery wordlists in SecLists, enabling selection of an appropriate list for ffuf.
- **Command:** `
import subprocess

target_path = "/usr/share/seclists/Discovery/Web-Content/"
print(f"[*] Listing contents of: {target_path}")
try:
    result = subprocess.run(
        ["ls", "-F", target_path],
        capture_output=True,
        text=True,
        timeout=10,
        check=True
    )
    print("\n--- LS COMMAND OUTPUT ---")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(f"[!] LS command failed: {e.stderr}")
except subprocess.TimeoutExpired:
    print(f"[!] LS command timed out for {target_path}.")
except Exception as e:
    print(f"[!] An error occurred: {e}")
`

#### Raw Output

```
STDOUT:
[*] Listing contents of: /usr/share/seclists/Discovery/Web-Content/

--- LS COMMAND OUTPUT ---
ActiveDirectory-small.txt
AdobeXML.fuzz.txt
BurpSuite-ParamMiner/
CMS/
Common-DB-Backups.txt
DirBuster-2007_directory-list-2.3-big.txt
DirBuster-2007_directory-list-2.3-medium.txt
DirBuster-2007_directory-list-2.3-small.txt
DirBuster-2007_directory-list-lowercase-2.3-big.txt
DirBuster-2007_directory-list-lowercase-2.3-medium.txt
DirBuster-2007_directory-list-lowercase-2.3-small.txt
Domino-Hunter/
File-Extensions-Universal-SVNDigger-Project/
JavaScript-Miners.txt
JavaServlets-Common.fuzz.txt
LEGACY-SERVICES/
LinuxFileList.txt
Logins.fuzz.txt
Microsoft-Frontpage.txt
Oracle9i.fuzz.txt
OracleAppServer.fuzz.txt
Passwords.fuzz.txt
Programming-Language-Specific/
Proxy-Auto-Configuration-Files.txt
Public-Source-Repo-Issues.json
README.md
Roundcube-123.txt
SAP-NetWeaver.txt
SOAP-functions.txt
Service-Specific/
URLs/
UnixDotfiles.fuzz.txt
Web-Servers/
api/
big.txt
burp-parameter-names.txt
coldfusion.txt
combined_directories.txt
combined_words.txt
common-api-endpoints-mazen160.txt
common.txt
common_directories.txt
default-web-root-directory-linux.txt
default-web-root-directory-windows.txt
domino-dirs-coldfusion39.txt
domino-endpoints-coldfusion39.txt
dsstorewordlist.txt
dutch/
graphql.txt
hashicorp-consul-api.txt
hashicorp-vault.txt
mcp-server.txt
netware.txt
ntlm-directories.txt
oauth-oidc-scopes.txt
quickhits.txt
raft-large-directories-lowercase.txt
raft-large-directories.txt
raft-large-extensions-lowercase.txt
raft-large-extensions.txt
raft-large-files-lowercase.txt
raft-large-files.txt
raft-large-words-lowercase.txt
raft-large-words.txt
raft-medium-directories-lowercase.txt
raft-medium-directories.txt
raft-medium-extensions-lowercase.txt
raft-medium-extensions.txt
raft-medium-files-lowercase.txt
raft-medium-files.txt
raft-medium-words-lowercase.txt
raft-medium-words.txt
raft-small-directories-lowercase.txt
raft-small-directories.txt
raft-small-extensions-lowercase.txt
raft-small-extensions.txt
raft-small-files-lowercase.txt
raft-small-files.txt
raft-small-words-lowercase.txt
raft-small-words.txt
reverse-proxy-inconsistencies.txt
rssfeed-files.txt
sap-analytics-cloud.txt
tftp.fuzz.txt
trickest-robots-disallowed-wordlists/
uri-from-top-55-most-popular-apps.txt
url-params_from-top-55-most-popular-apps.txt
versioning_metafiles.txt
vulnerability-scan_j2ee-websites_WEB-INF.txt
web-all-content-types.txt
web-extensions-big.txt
web-extensions.txt
web-mutations.txt
wso2-enterprise-integrator.txt


STDERR:

```

---

| d320c0f0 | enumeration | testing.nob.ro | web_probe | QUEUED | Pending |
| d320c0f0 | enumeration | testing.nob.ro | web_probe | FAILED | [Failed](#d320c0f0) |

### Detailed Result: d320c0f0

- **Target:** testing.nob.ro
- **Justification:** Per user request, this action performs a web content discovery scan on 'testing.nob.ro' using `ffuf`. The script is designed to combine multiple wordlists for thoroughness, and critically, to first determine and then filter out the response size of Cloudflare's "Attention Required!" page, ensuring that only actual web content is reported. It scans both HTTP and HTTPS ports.
- **Command:** `
import os
import json
import subprocess
import requests
import uuid

target_host = "testing.nob.ro"
wordlist_big = "/usr/share/seclists/Discovery/Web-Content/big.txt"
wordlist_raft_medium_dirs = "/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt"

# Combine wordlists for a more thorough scan
combined_wordlist_path = "/tmp/combined_web_wordlist.txt"
try:
    with open(combined_wordlist_path, "w") as outfile:
        with open(wordlist_big, "r") as infile1:
            outfile.write(infile1.read())
        with open(wordlist_raft_medium_dirs, "r") as infile2:
            outfile.write(infile2.read())
except Exception as e:
    print(f"[!] Error combining wordlists: {e}")
    # Fallback to just big.txt if combination fails
    combined_wordlist_path = wordlist_big

found_web_paths = set()

print(f"--- FFUF Web Content Discovery for {target_host} ---")

# 1. Determine size of a non-existent page for filtering
print("[*] Determining response size for non-existent page to filter Cloudflare challenges...")
non_existent_path = f"/{uuid.uuid4().hex}"
test_url = f"http://{target_host}{non_existent_path}"
filter_size = None
try:
    response = requests.get(test_url, timeout=10)
    filter_size = len(response.content)
    print(f"Filter size for non-existent page: {filter_size}")
except requests.exceptions.RequestException as e:
    print(f"[!] Error getting filter size: {e}")
    print("Proceeding without size filter (might be noisy).")

# 2. Run FFUF for content discovery
print(f"[*] Starting FFUF scan on {target_host} (HTTP and HTTPS)...")

ffuf_base_cmd = [
    "ffuf",
    "-w", combined_wordlist_path,
    "-mc", "all", # Match all status codes, then filter by size
    "-o", "/loot/ffuf_web_content.json",
    "-of", "json",
    "-t", "50" # Threads
]
if filter_size is not None:
    ffuf_base_cmd.extend(["-fs", str(filter_size)])
else:
    print("WARNING: No filter size set. FFUF results may contain many false positives.")

# Scan HTTP (port 80)
print(f"[*] FFUF on HTTP (port 80)...")
ffuf_http_cmd = ffuf_base_cmd + ["-u", f"http://{target_host}/FUZZ", "-H", f"Host: {target_host}"]
try:
    subprocess.run(ffuf_http_cmd, capture_output=True, text=True, timeout=1800, check=True) # Increased timeout
except subprocess.CalledProcessError as e:
    print(f"[!] FFUF HTTP scan failed: {e.stderr}")
except Exception as e:
    print(f"[!] Error during FFUF HTTP scan: {e}")

# Scan HTTPS (port 443)
print(f"[*] FFUF on HTTPS (port 443)...")
ffuf_https_cmd = ffuf_base_cmd + ["-u", f"https://{target_host}/FUZZ", "-H", f"Host: {target_host}"]
try:
    subprocess.run(ffuf_https_cmd, capture_output=True, text=True, timeout=1800, check=True) # Increased timeout
except subprocess.CalledProcessError as e:
    print(f"[!] FFUF HTTPS scan failed: {e.stderr}")
except Exception as e:
    print(f"[!] Error during FFUF HTTPS scan: {e}")

# Process FFUF results
ffuf_results_path = "/loot/ffuf_web_content.json"
if os.path.exists(ffuf_results_path):
    try:
        with open(ffuf_results_path, "r") as f:
            ffuf_data = json.load(f)
            if "results" in ffuf_data:
                for result in ffuf_data["results"]:
                    path = result.get("input", {}).get("FUZZ")
                    if path:
                        # Exclude paths that result in the Cloudflare challenge page
                        if filter_size is not None and result.get("length") == filter_size:
                            continue # Skip filtered size
                        found_web_paths.add(path.strip())
    except Exception as e:
        print(f"[!] Error processing FFUF results: {e}")
else:
    print("[!] FFUF output file not found.")

# 3. Report findings
print("\n--- Web Content Discovery Results ---")
print(f"Target: {target_host}")
print(f"Total Unique Paths Found (after filtering): {len(found_web_paths)}")
for path in sorted(list(found_web_paths)):
    print(f"/{path}")

# Save all results
final_results_dict = {
    "target": target_host,
    "tool": "ffuf",
    "wordlists_used": [wordlist_big, wordlist_raft_medium_dirs],
    "filter_size": filter_size,
    "found_paths": sorted(list(found_web_paths))
}
with open(f"/loot/web_content_discovery_{target_host}.json", "w") as f:
    json.dump(final_results_dict, f, indent=2)
print("\nConsolidated JSON results saved to artifact.")
`

#### Raw Output

```
Exit Code: 2

STDOUT:


STDERR:
/bin/sh: 2: import: not found
/bin/sh: 3: import: not found
/bin/sh: 4: import: not found
/bin/sh: 5: import: not found
/bin/sh: 6: import: not found
/bin/sh: 8: target_host: not found
/bin/sh: 9: wordlist_big: not found
/bin/sh: 10: wordlist_raft_medium_dirs: not found
/bin/sh: 13: combined_wordlist_path: not found
/bin/sh: 14: try:: not found
/bin/sh: 15: Syntax error: "(" unexpected

```

---

| e22ca640 | enumeration | testing.nob.ro | analysis | QUEUED | Pending |
| e22ca640 | enumeration | testing.nob.ro | analysis | COMPLETED | [Success](#e22ca640) |

### Detailed Result: e22ca640

- **Target:** testing.nob.ro
- **Justification:** To accurately diagnose the execution environment and resolve persistent `SyntaxError` issues, this action will print key Python environment variables and execute simple shell and Python commands via subprocess, clarifying how the `command` argument is interpreted and executed within the agent's container.
- **Command:** `
import sys, os, subprocess

print(f"sys.executable: {sys.executable}")
print(f"os.getenv('SHELL'): {os.getenv('SHELL')}")
print(f"os.getenv('0'): {os.getenv('0')}")
print(f"os.getenv('_'): {os.getenv('_')}")

try:
    print("\n--- Trying to run a simple shell command via subprocess ---")
    result = subprocess.run(
        ["/bin/sh", "-c", "echo 'hello from shell via subprocess'"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True
    )
    print(f"Subprocess stdout: {result.stdout}")
    print(f"Subprocess stderr: {result.stderr}")
except Exception as e:
    print(f"Error running subprocess shell command: {e}")

try:
    print("\n--- Trying to run a simple python command via subprocess ---")
    result = subprocess.run(
        [sys.executable, "-c", "print('hello from python via subprocess')"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True
    )
    print(f"Subprocess stdout: {result.stdout}")
    print(f"Subprocess stderr: {result.stderr}")
except Exception as e:
    print(f"Error running subprocess python command: {e}")
`

#### Raw Output

```
STDOUT:
sys.executable: /usr/bin/python3
os.getenv('SHELL'): None
os.getenv('0'): None
os.getenv('_'): None

--- Trying to run a simple shell command via subprocess ---
Subprocess stdout: hello from shell via subprocess

Subprocess stderr: 

--- Trying to run a simple python command via subprocess ---
Subprocess stdout: hello from python via subprocess

Subprocess stderr: 

STDERR:

```

---

| f2557c61 | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| f2557c61 | reconnaissance | 10.0.0.1 | network_scan | FAILED | [Failed](#f2557c61) |

### Detailed Result: f2557c61

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Network timeout
```

---

| 764fe3ff | reconnaissance | 10.0.0.1 | network_scan | QUEUED | Pending |
| 764fe3ff | reconnaissance | 10.0.0.1 | network_scan | COMPLETED | [Success](#764fe3ff) |

### Detailed Result: 764fe3ff

- **Target:** 10.0.0.1
- **Justification:** Initial recon to identify open ports and services for security assessment...................
- **Command:** `nmap -sV 10.0.0.1`

#### Raw Output

```
Scan successful this time
```

---

