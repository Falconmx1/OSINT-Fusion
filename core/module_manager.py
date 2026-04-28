"""
Central Module Manager for OSINT-Fusion
Orchestrates all modules with dependency resolution and parallel execution
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from modules.maigret_wrapper import MaigretWrapper
from modules.holehe_wrapper import HoleheWrapper
from modules.theharvester_wrapper import TheHarvesterWrapper
from core.parallel_executor import ParallelExecutor, ModuleTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InvestigationTarget:
    """Complete investigation target"""
    username: Optional[str] = None
    email: Optional[str] = None
    domain: Optional[str] = None
    
class ModuleManager:
    """Manages all OSINT modules and their coordination"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ParallelExecutor(max_workers=max_workers)
        
        # Initialize modules
        self.maigret = MaigretWrapper()
        self.holehe = HoleheWrapper()
        self.theharvester = TheHarvesterWrapper()
        
        # Module registry
        self.modules = {
            "maigret": {
                "func": self.maigret.search_username,
                "dependencies": [],
                "target_field": "username"
            },
            "holehe": {
                "func": self.holehe.search_email,
                "dependencies": [],
                "target_field": "email"
            },
            "theharvester": {
                "func": self.theharvester.search_domain,
                "dependencies": [],
                "target_field": "domain"
            }
        }
    
    async def run_full_investigation(self, target: InvestigationTarget) -> Dict[str, Any]:
        """
        Run complete investigation with all available modules
        """
        logger.info(f"Starting full investigation for: {target}")
        start_time = datetime.now()
        
        tasks = []
        
        # Create tasks based on available targets
        if target.username:
            tasks.append(ModuleTask(
                name="maigret",
                func=self.maigret.search_username,
                args=(target.username,),
                kwargs={},
                priority=1
            ))
        
        if target.email:
            tasks.append(ModuleTask(
                name="holehe",
                func=self.holehe.search_email,
                args=(target.email,),
                kwargs={},
                priority=1
            ))
            
            # Also try to extract username from email
            if not target.username:
                usernames = await self.holehe.email_to_username(target.email)
                if usernames:
                    tasks.append(ModuleTask(
                        name="maigret_email_extracted",
                        func=self.maigret.search_username,
                        args=(usernames[0],),
                        kwargs={},
                        priority=2
                    ))
        
        if target.domain:
            tasks.append(ModuleTask(
                name="theharvester",
                func=self.theharvester.search_domain,
                args=(target.domain,),
                kwargs={},
                priority=1
            ))
        
        if not tasks:
            return {"error": "No valid targets provided"}
        
        # Execute all tasks in parallel
        results = await self.executor.execute_parallel(tasks)
        
        # Correlate results between modules
        correlated = await self._correlate_results(results, target)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "execution_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "execution_time_seconds": round(execution_time, 2),
            "target": {
                "username": target.username,
                "email": target.email,
                "domain": target.domain
            },
            "modules_executed": len(tasks),
            "module_results": results,
            "correlated_data": correlated
        }
    
    async def _correlate_results(self, results: Dict, target: InvestigationTarget) -> Dict:
        """
        Correlate findings across modules
        """
        correlated = {
            "common_platforms": [],
            "email_username_match": False,
            "domain_emails": [],
            "linked_accounts": {},
            "risk_indicators": []
        }
        
        # Correlation 1: Check if email username matches searched username
        if target.email and target.username:
            email_username = target.email.split('@')[0]
            if email_username.lower() == target.username.lower():
                correlated["email_username_match"] = True
                correlated["risk_indicators"].append("Email username matches OSINT username")
        
        # Correlation 2: Extract emails from theHarvester and check with holehe
        if "theharvester" in results.get("results", {}):
            harvester_result = results["results"]["theharvester"]
            emails_found = harvester_result.get("emails", [])
            
            if emails_found and target.email:
                if target.email in emails_found:
                    correlated["risk_indicators"].append("Target email found in domain search")
            
            correlated["domain_emails"] = emails_found[:10]
            
            # Check each found email with holehe if we had time
            # (This would be async but we're already in correlation)
        
        # Correlation 3: Find platforms where username appears (from maigret)
        if "maigret" in results.get("results", {}):
            maigret_result = results["results"]["maigret"]
            found_sites = maigret_result.get("found_sites", [])
            
            # Check if any found platforms have email verification
            high_value_platforms = ["github", "twitter", "linkedin", "facebook", "instagram"]
            for site in found_sites:
                site_name = site.get("name", "").lower()
                if any(platform in site_name for platform in high_value_platforms):
                    correlated["linked_accounts"][site_name] = site.get("url")
        
        return correlated
    
    async def smart_investigation(self, target: InvestigationTarget) -> Dict[str, Any]:
        """
        Smart investigation that adapts based on findings
        """
        # First pass: quick checks
        quick_tasks = []
        
        if target.email:
            quick_tasks.append(ModuleTask(
                name="holehe_quick",
                func=self.holehe.search_email,
                args=(target.email,),
                kwargs={},
                priority=1
            ))
        
        initial_results = await self.executor.execute_parallel(quick_tasks)
        
        # Second pass: based on findings
        follow_up_tasks = []
        
        # If email has many registrations, search username
        if "holehe_quick" in initial_results.get("results", {}):
            holehe_result = initial_results["results"]["holehe_quick"]
            if holehe_result.get("services_found", 0) > 5:
                email_username = target.email.split('@')[0]
                follow_up_tasks.append(ModuleTask(
                    name="maigret_followup",
                    func=self.maigret.search_username,
                    args=(email_username,),
                    kwargs={},
                    priority=2
                ))
        
        # Execute follow-up
        if follow_up_tasks:
            follow_up_results = await self.executor.execute_parallel(follow_up_tasks)
            initial_results["results"].update(follow_up_results.get("results", {}))
        
        return initial_results

# CLI integration
async def main():
    manager = ModuleManager(max_workers=8)
    
    # Example: Full investigation
    target = InvestigationTarget(
        username="johndoe",
        email="johndoe@example.com",
        domain="example.com"
    )
    
    print("🔍 Running full investigation...")
    result = await manager.run_full_investigation(target)
    
    print(f"\n✅ Investigation completed in {result['execution_time_seconds']}s")
    print(f"📊 Modules executed: {result['modules_executed']}")
    
    # Show key findings
    if "maigret" in result["module_results"]["results"]:
        maigret_data = result["module_results"]["results"]["maigret"]
        print(f"🌐 Username found on {maigret_data.get('sites_found', 0)} platforms")
    
    if "holehe" in result["module_results"]["results"]:
        holehe_data = result["module_results"]["results"]["holehe"]
        print(f"📧 Email registered on {holehe_data.get('services_found', 0)} services")
        print(f"⚠️  Risk score: {holehe_data.get('risk_score', 0)} ({holehe_data.get('risk_level', 'Unknown')})")
    
    if "theharvester" in result["module_results"]["results"]:
        harvester_data = result["module_results"]["results"]["theharvester"]
        print(f"🌍 Domain found {harvester_data.get('total_emails', 0)} emails")
        print(f"🏠 {harvester_data.get('total_subdomains', 0)} subdomains")

if __name__ == "__main__":
    asyncio.run(main())
