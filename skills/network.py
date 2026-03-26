import xml.etree.ElementTree as ET

from skills.base import BaseSkill


class FpingSweep(BaseSkill):
    """Ping sweep using fping to discover alive hosts on a network."""

    tool = "fping"
    tool_version_command = "fping --version 2>&1"

    def build_command(self, **kwargs) -> str:
        network = kwargs.get("network") or self.target
        if not network:
            raise ValueError("network or target is required")
        return f"fping -g {network} -a 2>/dev/null"

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        hosts = [h.strip() for h in stdout.splitlines() if h.strip()]
        filename = f"alive_hosts_{self.target.replace('/', '_').replace('.', '_')}.txt"
        self.save_artifact(filename, stdout)
        return {
            "alive_count": len(hosts),
            "hosts": hosts,
        }


class NmapScan(BaseSkill):
    """Service/version scan using nmap (TCP connect)."""

    tool = "nmap"
    tool_version_command = "nmap --version"

    def build_command(self, **kwargs) -> str:
        host = kwargs.get("host") or self.target
        if not host:
            raise ValueError("host or target is required")
        ports = kwargs.get("ports", "")
        flags = kwargs.get("flags", "-sT -sV -T4")
        safe_host = host.replace("/", "_").replace(".", "_")
        self._xml_output = f"/loot/nmap_{safe_host}.xml"
        cmd = f"nmap {flags} {host} -oX {self._xml_output}"
        if ports:
            cmd += f" -p {ports}"
        return cmd

    def parse_output(self, stdout: str, stderr: str, exit_code: int) -> dict:
        self._artifacts.append(self._xml_output)
        try:
            return {"hosts": self._parse_nmap_xml(self._xml_output)}
        except Exception as e:
            self._errors.append(f"XML parse failed: {e}")
            return {"raw_stdout": stdout}

    @staticmethod
    def _parse_nmap_xml(xml_path: str) -> list[dict]:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        hosts = []
        for host in root.findall("host"):
            addr_elem = host.find("address")
            ip = addr_elem.get("addr") if addr_elem is not None else ""

            status_elem = host.find("status")
            status = status_elem.get("state") if status_elem is not None else "unknown"
            if status != "up":
                continue

            ports = []
            ports_elem = host.find("ports")
            if ports_elem is not None:
                for port in ports_elem.findall("port"):
                    p = {
                        "id": int(port.get("portid")),
                        "protocol": port.get("protocol"),
                        "state": port.find("state").get("state"),
                        "service": "unknown",
                    }
                    service = port.find("service")
                    if service is not None:
                        p["service"] = service.get("name", "unknown")
                        p["version"] = service.get("version", "")
                        p["product"] = service.get("product", "")
                    ports.append(p)

            hosts.append({"ip": ip, "ports": ports})

        return hosts
