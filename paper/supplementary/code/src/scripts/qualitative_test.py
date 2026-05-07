import asyncio
import os
import json
from src.evaluation.complex_runner import build_variants, run_benchmark

async def main():
    # Run 10 sampled tasks across 3 methods
    benchmark_path = "src/benchmarks/tasks/sample_10_tasks.json"
    
    # 变体：同步测试三个主要方法
    variants = build_variants(["full", "finagent_dvampire", "finmem"])
    
    # 设置超时时间环境变量 (10 题较多，稍微放宽一点总时间，但单题 1200s 足够)
    os.environ["FINAGENT_TASK_TIMEOUT_SECONDS"] = "1200"
    
    print(f"🚀 Starting Sampled Benchmark (10 tasks) for variants: {[v.name for v in variants]}...")
    
    if not os.path.exists(benchmark_path):
        print(f"Error: {benchmark_path} not found!")
        return
    
    run_ids = await run_benchmark(
        benchmark_path=benchmark_path,
        variants=variants,
        output_dir="src/benchmarks/qualitative_tests",
        judge=True,
        repeat=1
    )
    
    print(f"\n✅ Qualitative Test Finished. Run IDs: {run_ids}")
    print("Please check src/benchmarks/qualitative_tests for detailed logs and scores.")

if __name__ == "__main__":
    asyncio.run(main())
