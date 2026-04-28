import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parallel_executor import ParallelExecutor, ModuleTask

async def test_parallel_execution():
    """Test that parallel execution is faster than sequential"""
    
    async def delay_function(seconds, name):
        await asyncio.sleep(seconds)
        return f"{name} done"
    
    tasks = [
        ModuleTask("task1", delay_function, (0.5, "1"), {}),
        ModuleTask("task2", delay_function, (0.5, "2"), {}),
        ModuleTask("task3", delay_function, (0.5, "3"), {}),
        ModuleTask("task4", delay_function, (0.5, "4"), {}),
    ]
    
    executor = ParallelExecutor(max_workers=4)
    results = await executor.execute_parallel(tasks)
    
    # Parallel with 4 workers should take ~0.5s, not 2s
    assert results["execution_time"] < 1.0
    assert results["successful"] == 4
    assert results["failed"] == 0

async def test_error_handling():
    """Test that errors don't crash other tasks"""
    
    async def good_task():
        await asyncio.sleep(0.1)
        return "success"
    
    async def bad_task():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")
    
    tasks = [
        ModuleTask("good", good_task, (), {}),
        ModuleTask("bad", bad_task, (), {}),
    ]
    
    executor = ParallelExecutor(max_workers=2)
    results = await executor.execute_parallel(tasks)
    
    assert results["successful"] == 1
    assert results["failed"] == 1
    assert "error" in results["results"]["bad"]

if __name__ == "__main__":
    asyncio.run(test_parallel_execution())
    asyncio.run(test_error_handling())
    print("✅ All tests passed!")
