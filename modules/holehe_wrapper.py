"""
Holehe Module Wrapper for OSINT-Fusion
Checks email registrations across 120+ websites
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

try:
    from holehe import holehe
    from holehe.core import check_email
    HOLEHE_AVAILABLE = True
except ImportError:
    HOLEHE_AVAILABLE = False
    print("⚠️  Holehe not installed. Run: pip install holehe")

class HoleheWrapper:
    """Wrapper for Holehe OSINT tool - email footprint analysis"""
    
    def __init__(self, timeout: int = 15, max_concurrent: int = 20):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.cache_dir = Path("./cache/holehe")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    async def search_email(self, email: str) -> Dict[str, Any]:
        """
        Search email across platforms
        
        Args:
            email: Target email address
            
        Returns:
            Dict with found services, status, and metadata
        """
        if not HOLEHE_AVAILABLE:
            return {
                "error": "Holehe not installed",
                "email": email,
                "status": "failed"
            }
        
        try:
            # Holehe returns list of modules, each with .exists property
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_search,
                email
            )
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "email": email,
                "status": "error"
            }
    
    def _sync_search(self, email: str) -> Dict[str, Any]:
        """Synchronous search (runs in thread pool)"""
        import holehe
        
        # Run holehe check
        modules = holehe.holehe()
        
        results = []
        found_services = []
        
        for module in modules:
            try:
                # Each module is a function that returns a dict
                result = module(email)
                
                if result.get("exists"):
                    found_services.append({
                        "name": module.__name__.replace("_", " ").title(),
                        "url": result.get("webmail", result.get("url", "")),
                        "rate_limit": result.get("rateLimit", False),
                        "recovery_email": result.get("recovery", None),
                        "phone": result.get("phone", None)
                    })
                
                results.append({
                    "module": module.__name__,
                    "exists": result.get("exists", False),
                    "rate_limit": result.get("rateLimit", False)
                })
                
            except Exception as e:
                results.append({
                    "module": module.__name__,
                    "error": str(e),
                    "exists": False
                })
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(found_services)
        
        return {
            "email": email,
            "total_services_checked": len(modules),
            "services_found": len(found_services),
            "found_services": found_services[:20],  # Top 20
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "all_results": results[:50],  # Limit for performance
            "status": "completed"
        }
    
    def _calculate_risk_score(self, found_services: List[Dict]) -> float:
        """Calculate risk score based on found services"""
        if not found_services:
            return 0.0
        
        # Weight by service importance
        high_risk_services = [
            "paypal", "bank", "bitcoin", "coinbase", "stripe",
            "amazon", "ebay", "walmart", "target", "bestbuy"
        ]
        
        medium_risk_services = [
            "facebook", "instagram", "twitter", "linkedin", "github",
            "google", "microsoft", "apple", "discord", "reddit"
        ]
        
        score = 0
        for service in found_services:
            service_lower = service["name"].lower()
            
            if any(high in service_lower for high in high_risk_services):
                score += 10
            elif any(medium in service_lower for medium in medium_risk_services):
                score += 5
            else:
                score += 2
        
        # Normalize to 0-100
        return min(100, score)
    
    def _get_risk_level(self, score: float) -> str:
        """Get risk level from score"""
        if score >= 70:
            return "Critical 🔴"
        elif score >= 40:
            return "High 🟠"
        elif score >= 20:
            return "Medium 🟡"
        elif score > 0:
            return "Low 🟢"
        else:
            return "None ⚪"
    
    async def batch_search(self, emails: List[str]) -> List[Dict[str, Any]]:
        """Search multiple emails in parallel"""
        tasks = [self.search_email(email) for email in emails]
        results = await asyncio.gather(*tasks)
        return results
    
    async def email_to_username(self, email: str) -> List[str]:
        """Extract possible usernames from email"""
        username = email.split('@')[0]
        
        # Common username patterns
        variants = [
            username,
            username.lower(),
            username.upper(),
            username.replace('.', ''),
            username.replace('_', ''),
            username.replace('-', ''),
            username + str(datetime.now().year % 100)
        ]
        
        return list(set(variants))

# Quick test function
async def test_holehe():
    wrapper = HoleheWrapper()
    result = await wrapper.search_email("test@example.com")
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(test_holehe())
