"""
Maigret Module Wrapper for OSINT-Fusion
Searches username across 3000+ social networks
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

# Dynamic import with fallback
try:
    from maigret import Maigret, detect_usernames
    from maigret.report import save_report
    MAIGRET_AVAILABLE = True
except ImportError:
    MAIGRET_AVAILABLE = False
    print("⚠️  Maigret not installed. Run: pip install maigret")

class MaigretWrapper:
    """Wrapper for Maigret OSINT tool"""
    
    def __init__(self, timeout: int = 30, max_connections: int = 50):
        self.timeout = timeout
        self.max_connections = max_connections
        self.cache_dir = Path("./cache/maigret")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    async def search_username(self, username: str) -> Dict[str, Any]:
        """
        Search username across platforms
        
        Args:
            username: Target username
            
        Returns:
            Dict with found sites, status, and metadata
        """
        if not MAIGRET_AVAILABLE:
            return {
                "error": "Maigret not installed",
                "username": username,
                "status": "failed"
            }
        
        try:
            # Run maigret in thread pool (blocks async)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._sync_search, 
                username
            )
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "username": username,
                "status": "error"
            }
    
    def _sync_search(self, username: str) -> Dict[str, Any]:
        """Synchronous search (runs in thread pool)"""
        from maigret import Maigret
        
        # Configure maigret
        maigret = Maigret(
            timeout=self.timeout,
            max_connections=self.max_connections,
            cache_path=str(self.cache_dir)
        )
        
        # Run detection
        results = detect_usernames(
            usernames=[username],
            maigret=maigret,
            report_path=None  # We'll handle reporting ourselves
        )
        
        # Parse results
        found_sites = []
        if username in results:
            for site_name, site_data in results[username].items():
                if site_data.get("status", {}).get("exists", False):
                    found_sites.append({
                        "name": site_name,
                        "url": site_data.get("url", ""),
                        "status": site_data.get("status", {}).get("http_status", 200),
                        "confidence": site_data.get("status", {}).get("confidence", "low")
                    })
        
        return {
            "username": username,
            "total_sites_checked": len(results.get(username, {})),
            "sites_found": len(found_sites),
            "found_sites": found_sites,
            "status": "completed",
            "cache_used": self.cache_dir.exists()
        }
    
    async def batch_search(self, usernames: List[str]) -> List[Dict[str, Any]]:
        """Search multiple usernames in parallel"""
        tasks = [self.search_username(u) for u in usernames]
        results = await asyncio.gather(*tasks)
        return results

# Quick test function
async def test_maigret():
    wrapper = MaigretWrapper(timeout=20)
    result = await wrapper.search_username("john")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_maigret())
