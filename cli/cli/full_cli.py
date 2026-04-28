#!/usr/bin/env python3
"""
OSINT-Fusion Full CLI
Complete interface with all modules and parallel execution
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.module_manager import ModuleManager, InvestigationTarget
from core.parallel_executor import ParallelExecutor

class OSINTFusionCLI:
    def __init__(self):
        self.manager = ModuleManager()
        
    async def run(self):
        parser = argparse.ArgumentParser(
            description="OSINT-Fusion - Complete OSINT Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Username investigation
  python full_cli.py --username johndoe
  
  # Email investigation
  python full_cli.py --email user@example.com
  
  # Domain investigation
  python full_cli.py --domain example.com
  
  # Full investigation (all three)
  python full_cli.py --username johndoe --email john@doe.com --domain doce.com
  
  # Smart investigation (adapts based on findings)
  python full_cli.py --email user@example.com --smart
  
  # Output to JSON
  python full_cli.py --username johndoe --output report.json
  
  # Parallel execution with custom workers
  python full_cli.py --email test@example.com --workers 15
            """
        )
        
        parser.add_argument("--username", help="Target username")
        parser.add_argument("--email", help="Target email")
        parser.add_argument("--domain", help="Target domain")
        parser.add_argument("--smart", action="store_true", help="Smart investigation mode")
        parser.add_argument("--workers", type=int, default=10, help="Max parallel workers")
        parser.add_argument("--output", help="Output JSON file")
        parser.add_argument("--verbose", action="store_true", help="Verbose output")
        
        args = parser.parse_args()
        
        if not any([args.username, args.email, args.domain]):
            parser.print_help()
            print("\n❌ Error: Specify at least one target")
            sys.exit(1)
        
        # Update workers
        self.manager.max_workers = args.workers
        self.manager.executor.max_workers = args.workers
        
        print("🔍 OSINT-Fusion Starting...")
        print("═" * 50)
        print(f"📊 Mode: {'Smart' if args.smart else 'Full'}")
        print(f"⚙️  Workers: {args.workers}")
        print(f"🎯 Targets: {', '.join([f for f in [args.username and f'user:{args.username}', args.email and f'email:{args.email}', args.domain and f'domain:{args.domain}'] if f])}")
        print("═" * 50)
        
        target = InvestigationTarget(
            username=args.username,
            email=args.email,
            domain=args.domain
        )
        
        try:
            if args.smart:
                results = await self.manager.smart_investigation(target)
            else:
                results = await self.manager.run_full_investigation(target)
            
            # Display results
            self._display_results(results, args.verbose)
            
            # Save to file
            output_file = args.output or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"\n💾 Report saved to: {output_file}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    def _display_results(self, results: Dict, verbose: bool):
        """Display formatted results"""
        print("\n📊 INVESTIGATION RESULTS")
        print("═" * 50)
        
        # Execution stats
        print(f"\n⏱️  Execution time: {results.get('execution_time_seconds', 0)}s")
        print(f"🔧 Modules executed: {results.get('modules_executed', 0)}")
        
        # Module results
        module_results = results.get("module_results", {}).get("results", {})
        
        # Maigret results
        if "maigret" in module_results:
            m = module_results["maigret"]
            print(f"\n🌐 USERNAME OSINT (Maigret)")
            print(f"   └─ Sites found: {m.get('sites_found', 0)} / {m.get('total_sites_checked', 0)}")
            if verbose and m.get('found_sites'):
                print("   └─ Top sites:")
                for site in m.get('found_sites', [])[:5]:
                    print(f"       • {site.get('name')}: {site.get('url')}")
        
        # Holehe results
        if "holehe" in module_results:
            h = module_results["holehe"]
            print(f"\n📧 EMAIL OSINT (Holehe)")
            print(f"   └─ Services found: {h.get('services_found', 0)} / {h.get('total_services_checked', 0)}")
            print(f"   └─ Risk score: {h.get('risk_score', 0)}/100 {h.get('risk_level', '')}")
            if verbose and h.get('found_services'):
                print("   └─ Top services:")
                for service in h.get('found_services', [])[:5]:
                    print(f"       • {service.get('name')}")
        
        # TheHarvester results
        if "theharvester" in module_results:
            th = module_results["theharvester"]
            print(f"\n🌍 DOMAIN OSINT (theHarvester)")
            print(f"   └─ Emails: {th.get('total_emails', 0)}")
            print(f"   └─ Subdomains: {th.get('total_subdomains', 0)}")
            print(f"   └─ Hosts: {th.get('total_hosts', 0)}")
            if verbose and th.get('emails'):
                print("   └─ Sample emails:")
                for email in th.get('emails', [])[:3]:
                    print(f"       • {email}")
        
        # Correlated data
        correlated = results.get("correlated_data", {})
        if correlated.get("risk_indicators"):
            print(f"\n⚠️  RISK INDICATORS")
            for indicator in correlated["risk_indicators"]:
                print(f"   └─ {indicator}")
        
        if correlated.get("linked_accounts"):
            print(f"\n🔗 LINKED ACCOUNTS")
            for platform, url in correlated["linked_accounts"].items():
                print(f"   └─ {platform.title()}: {url}")
        
        print("\n" + "═" * 50)

def main():
    cli = OSINTFusionCLI()
    asyncio.run(cli.run())

if __name__ == "__main__":
    main()
