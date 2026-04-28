#!/usr/bin/env python3
"""
Advanced CLI with Parallel Execution
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parallel_executor import Orchestrator, ModuleTask
from modules.maigret_wrapper import MaigretWrapper

async def async_main():
    parser = argparse.ArgumentParser(
        description="OSINT-Fusion Advanced CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  osint-fusion --username johndoe --parallel
  osint-fusion --email test@example.com --output report.json
  osint-fusion --username johndoe --email test@example.com --parallel --workers 15
        """
    )
    
    parser.add_argument("--username", help="Target username")
    parser.add_argument("--email", help="Target email")
    parser.add_argument("--domain", help="Target domain")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel execution")
    parser.add_argument("--workers", type=int, default=10, help="Max parallel workers")
    parser.add_argument("--output", help="Output JSON file (default: report_TIMESTAMP.json)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not any([args.username, args.email, args.domain]):
        parser.print_help()
        print("\n❌ Error: Specify at least one target")
        sys.exit(1)
    
    print("🔍 OSINT-Fusion Starting...")
    print(f"📊 Parallel mode: {'ON' if args.parallel else 'OFF'}")
    print(f"⚙️  Workers: {args.workers}")
    print("-" * 50)
    
    target = {
        "username": args.username,
        "email": args.email,
        "domain": args.domain
    }
    
    # Initialize modules
    maigret = MaigretWrapper()
    orchestrator = Orchestrator()
    
    # Register modules
    async def maigret_task(username):
        return await maigret.search_username(username)
    
    orchestrator.modules["maigret"] = {"func": maigret_task, "dependencies": []}
    
    # Build task list
    tasks = []
    
    if args.username:
        tasks.append(ModuleTask(
            name="maigret",
            func=maigret_task,
            args=(args.username,),
            kwargs={},
            priority=1
        ))
    
    # Execute
    if args.parallel:
        executor = ParallelExecutor(max_workers=args.workers)
        results = await executor.execute_parallel(tasks)
    else:
        # Sequential execution
        results = {"results": {}, "execution_time": 0}
        for task in tasks:
            result = await task.func(*task.args)
            results["results"][task.name] = result
    
    # Output
    output_file = args.output or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "target": target,
            "parallel_mode": args.parallel,
            "execution_stats": {
                "time": results.get("execution_time", 0),
                "modules_executed": len(tasks)
            },
            "results": results.get("results", {})
        }, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    if args.verbose:
        print("\n📊 Summary:")
        for name, result in results.get("results", {}).items():
            if "error" in result:
                print(f"  ❌ {name}: {result['error']}")
            elif name == "maigret" and "sites_found" in result:
                print(f"  ✅ {name}: {result['sites_found']} sites found")

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
