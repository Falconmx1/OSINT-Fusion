"""
Parallel Module Executor for OSINT-Fusion
Runs multiple OSINT modules concurrently with resource management
"""

import asyncio
import concurrent.futures
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModuleTask:
    """Represents an OSINT module task"""
    name: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 5  # 1-10, lower = higher priority

class ParallelExecutor:
    """Manages parallel execution of OSINT modules"""
    
    def __init__(self, max_workers: int = 10, use_asyncio: bool = True):
        self.max_workers = max_workers
        self.use_asyncio = use_asyncio
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
        
    async def execute_parallel(self, tasks: List[ModuleTask]) -> Dict[str, Any]:
        """
        Execute multiple modules in parallel
        
        Args:
            tasks: List of ModuleTask objects
            
        Returns:
            Dictionary with module results
        """
        start_time = time.time()
        
        if self.use_asyncio:
            results = await self._execute_async(tasks)
        else:
            results = await self._execute_threadpool(tasks)
        
        execution_time = time.time() - start_time
        
        return {
            "execution_time": round(execution_time, 2),
            "total_modules": len(tasks),
            "successful": len([r for r in results.values() if "error" not in r]),
            "failed": len([r for r in results.values() if "error" in r]),
            "results": results
        }
    
    async def _execute_async(self, tasks: List[ModuleTask]) -> Dict[str, Any]:
        """Execute using asyncio gather"""
        async_tasks = []
        task_names = []
        
        for task in sorted(tasks, key=lambda x: x.priority):
            if asyncio.iscoroutinefunction(task.func):
                async_tasks.append(task.func(*task.args, **task.kwargs))
            else:
                # Wrap sync function in async
                async_tasks.append(
                    asyncio.get_event_loop().run_in_executor(
                        None, task.func, *task.args
                    )
                )
            task_names.append(task.name)
        
        # Execute with semaphore for rate limiting
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def run_with_limit(task_coro, name):
            async with semaphore:
                try:
                    result = await task_coro
                    return name, result
                except Exception as e:
                    logger.error(f"Module {name} failed: {e}")
                    return name, {"error": str(e)}
        
        # Run all tasks
        results = {}
        for task_coro, name in zip(async_tasks, task_names):
            name, result = await run_with_limit(task_coro, name)
            results[name] = result
        
        return results
    
    async def _execute_threadpool(self, tasks: List[ModuleTask]) -> Dict[str, Any]:
        """Execute using ThreadPoolExecutor (fallback)"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {}
            
            for task in tasks:
                future = executor.submit(task.func, *task.args, **task.kwargs)
                future_to_task[future] = task.name
            
            for future in concurrent.futures.as_completed(future_to_task):
                name = future_to_task[future]
                try:
                    result = future.result(timeout=30)
                    results[name] = result
                except Exception as e:
                    logger.error(f"Module {name} failed: {e}")
                    results[name] = {"error": str(e)}
        
        return results

class Orchestrator:
    """Orchestrates multiple OSINT modules with dependencies"""
    
    def __init__(self):
        self.executor = ParallelExecutor()
        self.modules = {}
        
    def register_module(self, name: str, func: Callable, dependencies: Optional[List[str]] = None):
        """Register a module with optional dependencies"""
        self.modules[name] = {
            "func": func,
            "dependencies": dependencies or []
        }
    
    async def run_pipeline(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run modules based on target type (username, email, domain)
        """
        tasks = []
        
        # Discover modules based on target
        if target.get("username"):
            tasks.append(ModuleTask(
                name="maigret",
                func=self.modules.get("maigret", {}).get("func", self._dummy_module),
                args=(target["username"],),
                kwargs={},
                priority=1
            ))
        
        if target.get("email"):
            tasks.append(ModuleTask(
                name="holehe",
                func=self.modules.get("holehe", {}).get("func", self._dummy_module),
                args=(target["email"],),
                kwargs={},
                priority=2
            ))
        
        if target.get("domain"):
            tasks.append(ModuleTask(
                name="theharvester",
                func=self.modules.get("theharvester", {}).get("func", self._dummy_module),
                args=(target["domain"],),
                kwargs={},
                priority=3
            ))
        
        # Execute parallel tasks
        results = await self.executor.execute_parallel(tasks)
        return results
    
    async def _dummy_module(self, target):
        """Placeholder for missing modules"""
        return {"status": "pending", "message": "Module not yet integrated"}

# Example usage
async def demo_parallel_execution():
    """Demo showing parallel execution"""
    
    # Create dummy modules for demo
    async def fast_module(data):
        await asyncio.sleep(1)
        return {"result": "fast", "data": data}
    
    async def slow_module(data):
        await asyncio.sleep(3)
        return {"result": "slow", "data": data}
    
    async def error_module(data):
        await asyncio.sleep(0.5)
        raise ValueError("Demo error")
    
    executor = ParallelExecutor(max_workers=5)
    
    tasks = [
        ModuleTask("fast", fast_module, ("test",), {}),
        ModuleTask("slow", slow_module, ("test",), {}),
        ModuleTask("error", error_module, ("test",), {}),
    ]
    
    results = await executor.execute_parallel(tasks)
    print("Parallel execution results:")
    print(f"  Time: {results['execution_time']}s")
    print(f"  Success: {results['successful']}/{results['total_modules']}")
    for name, result in results['results'].items():
        print(f"  {name}: {'✅' if 'error' not in result else '❌'}")

if __name__ == "__main__":
    asyncio.run(demo_parallel_execution())
