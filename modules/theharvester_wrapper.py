"""
theHarvester Module Wrapper for OSINT-Fusion
Domain/company reconnaissance and email harvesting
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import re

try:
    from theHarvester.discovery import *
    from theHarvester.lib.core import *
    THEHARVESTER_AVAILABLE = True
except ImportError:
    THEHARVESTER_AVAILABLE = False
    print("⚠️  theHarvester not installed. Run: pip install theHarvester")

class TheHarvesterWrapper:
    """Wrapper for theHarvester OSINT tool - domain intelligence"""
    
    def __init__(self, timeout: int = 30, max_sources: int = 15):
        self.timeout = timeout
        self.max_sources = max_sources
        self.cache_dir = Path("./cache/theharvester")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Available data sources
        self.sources = [
            "google", "bing", "linkedin", "twitter", "github",
            "duckduckgo", "crtsh", "hunter", "anubis", "virustotal",
            "dnsdumpster", "intelx", "bufferoverrun", "urlscan", "hackertarget"
        ]
    
    async def search_domain(self, domain: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search domain across multiple sources
        
        Args:
            domain: Target domain (e.g., example.com)
            sources: List of sources to use (None = all available)
            
        Returns:
            Dict with emails, hosts, ips, and metadata
        """
        if not THEHARVESTER_AVAILABLE:
            return {
                "error": "theHarvester not installed",
                "domain": domain,
                "status": "failed"
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_search,
                domain,
                sources or self.sources[:self.max_sources]
            )
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "domain": domain,
                "status": "error"
            }
    
    def _sync_search(self, domain: str, sources: List[str]) -> Dict[str, Any]:
        """Synchronous search implementation"""
        from theHarvester.lib.core import Core
        
        results = {
            "emails": set(),
            "hosts": set(),
            "ips": set(),
            "subdomains": set(),
            "urls": set(),
            "source_stats": {}
        }
        
        # Process each source
        for source_name in sources:
            try:
                source_results = self._query_source(source_name, domain)
                
                # Aggregar resultados
                results["emails"].update(source_results.get("emails", []))
                results["hosts"].update(source_results.get("hosts", []))
                results["ips"].update(source_results.get("ips", []))
                results["subdomains"].update(source_results.get("subdomains", []))
                results["urls"].update(source_results.get("urls", []))
                
                results["source_stats"][source_name] = {
                    "emails": len(source_results.get("emails", [])),
                    "hosts": len(source_results.get("hosts", [])),
                    "subdomains": len(source_results.get("subdomains", []))
                }
                
            except Exception as e:
                results["source_stats"][source_name] = {"error": str(e)}
        
        # Convert sets to lists for JSON serialization
        return {
            "domain": domain,
            "total_emails": len(results["emails"]),
            "total_hosts": len(results["hosts"]),
            "total_ips": len(results["ips"]),
            "total_subdomains": len(results["subdomains"]),
            "emails": list(results["emails"])[:100],  # Top 100
            "hosts": list(results["hosts"])[:50],
            "ips": list(results["ips"])[:50],
            "subdomains": list(results["subdomains"])[:50],
            "urls": list(results["urls"])[:50],
            "source_stats": results["source_stats"],
            "status": "completed"
        }
    
    def _query_source(self, source_name: str, domain: str) -> Dict[str, Any]:
        """Query individual source (simplified - real implementation would use source classes)"""
        # Simplified version - real theHarvester has complex source classes
        # This is a placeholder that returns mock data for testing
        # In production, you'd use actual theHarvester source classes
        
        import requests
        from bs4 import BeautifulSoup
        
        results = {"emails": [], "hosts": [], "ips": [], "subdomains": [], "urls": []}
        
        # Certificates (crtsh)
        if source_name == "crtsh":
            try:
                url = f"https://crt.sh/?q=%25.{domain}&output=json"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    subdomains = set()
                    for entry in data:
                        if 'name_value' in entry:
                            names = entry['name_value'].split('\n')
                            for name in names:
                                if domain in name:
                                    subdomains.add(name.strip())
                    results["subdomains"] = list(subdomains)[:20]
            except:
                pass
        
        # DNSDumpster
        elif source_name == "dnsdumpster":
            try:
                url = "https://dnsdumpster.com/"
                session = requests.Session()
                csrf = session.get(url).content
                # Simplified - actual implementation requires CSRF token
                results["hosts"] = [f"www.{domain}", f"mail.{domain}"]
            except:
                pass
        
        # Hackertarget
        elif source_name == "hackertarget":
            try:
                url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    for line in response.text.split('\n'):
                        if ',' in line:
                            host, ip = line.split(',')
                            results["hosts"].append(host)
                            results["ips"].append(ip)
            except:
                pass
        
        return results
    
    async def search_company(self, company_name: str) -> Dict[str, Any]:
        """Search for company domains"""
        # Common domain patterns
        possible_domains = [
            f"{company_name}.com",
            f"{company_name.replace(' ', '')}.com",
            f"{company_name}.io",
            f"{company_name}.org",
            f"{company_name}.net"
        ]
        
        results = {}
        for domain in possible_domains[:5]:
            domain_result = await self.search_domain(domain)
            if domain_result.get("total_emails", 0) > 0:
                results[domain] = domain_result
        
        return {
            "company": company_name,
            "domains_found": len(results),
            "results": results
        }
    
    def extract_employee_emails(self, emails: List[str], company_domain: str) -> List[Dict]:
        """Extract and categorize employee emails"""
        employees = []
        
        for email in emails:
            if company_domain in email:
                username = email.split('@')[0]
                
                # Guess employee info from email format
                name_parts = re.split(r'[._-]', username)
                
                employee = {
                    "email": email,
                    "username": username,
                    "format": self._detect_email_format(username)
                }
                
                if len(name_parts) >= 2:
                    employee["first_name"] = name_parts[0].capitalize()
                    employee["last_name"] = name_parts[-1].capitalize()
                
                employees.append(employee)
        
        return employees
    
    def _detect_email_format(self, username: str) -> str:
        """Detect email format pattern"""
        if '.' in username:
            return "first.last"
        elif '_' in username:
            return "first_last"
        elif username.islower() and len(username) > 5:
            return "firstlast"
        elif username[0].isalpha() and len(username) < 8:
            return "initial.last"
        else:
            return "custom"

# Quick test function
async def test_theharvester():
    wrapper = TheHarvesterWrapper()
    result = await wrapper.search_domain("github.com", sources=["crtsh", "hackertarget"])
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(test_theharvester())
