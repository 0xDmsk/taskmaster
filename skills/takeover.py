import socket
import dns.resolver
import requests
from skills.base import BaseSkill

class TakeoverSkill(BaseSkill):
    """
    Subdomain Takeover Skill.
    Checks CNAME records for common cloud provider takeovers.
    """
    FINGERPRINTS = {
        "github.io": "GitHub Pages",
        "herokuapp.com": "Heroku",
        "amazonaws.com": "AWS S3/CloudFront",
        "elasticbeanstalk.com": "AWS Elastic Beanstalk",
        "azurewebsites.net": "Azure App Services",
        "cloudapp.net": "Azure Cloud App",
        "trafficmanager.net": "Azure Traffic Manager",
        "wordpress.com": "WordPress",
        "shopify.com": "Shopify",
        "zendesk.com": "Zendesk",
        "readme.io": "Readme.io",
        "ghost.io": "Ghost",
        "pantheon.io": "Pantheon",
        "fly.io": "Fly.io"
    }

    def run(self, subdomains=None, **kwargs):
        if not subdomains:
            return {"error": "List of subdomains required"}

        if isinstance(subdomains, str):
            subdomains = subdomains.splitlines()

        results = {
            "scanned": len(subdomains),
            "vulnerable": [],
            "warnings": []
        }

        print(f"[*] Checking {len(subdomains)} subdomains for takeover...")

        for sub in subdomains:
            try:
                cname = self._resolve_cname(sub)
                if not cname:
                    continue
                
                # Check fingerprint
                provider = self._check_fingerprint(cname)
                if provider:
                    # Found a provider, now check if it's dead
                    is_dead = self._check_dead_dns(sub)
                    entry = {
                        "subdomain": sub,
                        "cname": cname,
                        "provider": provider,
                        "status": "VULNERABLE" if is_dead else "FLAGGED"
                    }
                    if is_dead:
                        results["vulnerable"].append(entry)
                    else:
                        results["warnings"].append(entry)
            except Exception as e:
                pass

        self.save_json("takeover_results.json", results)
        return results

    def _resolve_cname(self, domain):
        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            for rdata in answers:
                return str(rdata.target).rstrip('.')
        except:
            return None
        return None

    def _check_fingerprint(self, cname):
        for pattern, name in self.FINGERPRINTS.items():
            if pattern in cname:
                return name
        return None

    def _check_dead_dns(self, domain):
        # Simplistic check: if DNS resolves but HTTP 404/NXDOMAIN, likely takeoverable.
        # Here we rely on 'Is it resolvable to an IP?'. If yes, check HTTP.
        try:
            # Check A record
            ip = socket.gethostbyname(domain)
            # Check HTTP
            try:
                r = requests.get(f"http://{domain}", timeout=3)
                if r.status_code == 404:
                    # Many takeovers manifest as 404 (GitHub, Heroku)
                    return True
                # AWS specific
                if "NoSuchBucket" in r.text:
                    return True
            except:
                pass
            return False
        except:
            # If CNAME exists but A fails, it's dead -> Takeover!
            return True
