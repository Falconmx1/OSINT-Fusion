import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.maigret_wrapper import MaigretWrapper
from modules.holehe_wrapper import HoleheWrapper
from modules.theharvester_wrapper import TheHarvesterWrapper
from core.module_manager import ModuleManager, InvestigationTarget

async def test_all_modules():
    """Test all modules independently"""
    
    print("🧪 Testing OSINT-Fusion Modules\n" + "="*50)
    
    # Test Maigret
    print("\n1. Testing Maigret (Username)...")
    maigret = MaigretWrapper()
    result = await maigret.search_username("github")
    print(f"   ✅ Found {result.get('sites_found', 0)} sites")
    
    # Test Holehe
    print("\n2. Testing Holehe (Email)...")
    holehe = HoleheWrapper()
    result = await holehe.search_email("test@gmail.com")
    print(f"   ✅ Found {result.get('services_found', 0)} services")
    print(f"   📊 Risk score: {result.get('risk_score', 0)}")
    
    # Test theHarvester
    print("\n3. Testing theHarvester (Domain)...")
    harvester = TheHarvesterWrapper()
    result = await harvester.search_domain("github.com", sources=["crtsh"])
    print(f"   ✅ Found {result.get('total_subdomains', 0)} subdomains")
    print(f"   📧 Found {result.get('total_emails', 0)} emails")
    
    print("\n" + "="*50)
    print("✅ All modules passed basic tests!")

async def test_integration():
    """Test full integration"""
    
    print("\n🧪 Testing Module Integration\n" + "="*50)
    
    manager = ModuleManager(max_workers=5)
    
    target = InvestigationTarget(
        username="python",
        email="python@example.com",
        domain="python.org"
    )
    
    print(f"\n🔍 Running investigation on: {target}")
    results = await manager.run_full_investigation(target)
    
    print(f"\n📊 Results:")
    print(f"   ⏱️  Time: {results['execution_time_seconds']}s")
    print(f"   🔧 Modules: {results['modules_executed']}")
    
    module_results = results.get("module_results", {}).get("results", {})
    
    if "maigret" in module_results:
        print(f"   🌐 Username sites: {module_results['maigret'].get('sites_found', 0)}")
    
    if "holehe" in module_results:
        print(f"   📧 Email services: {module_results['holehe'].get('services_found', 0)}")
    
    if "theharvester" in module_results:
        print(f"   🌍 Domain subdomains: {module_results['theharvester'].get('total_subdomains', 0)}")
    
    print("\n✅ Integration test passed!")

async def main():
    await test_all_modules()
    await test_integration()

if __name__ == "__main__":
    asyncio.run(main())
