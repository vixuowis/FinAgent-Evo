import asyncio
import argparse

from src.evaluation.complex_runner import Variant, run_benchmark


async def main():
    parser = argparse.ArgumentParser(description="Complex orchestration evaluation (unified NeurIPS runner).")
    parser.add_argument("--benchmark", type=str, default="src/benchmarks/tasks/complex_tasks.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="src/benchmarks/results")
    args = parser.parse_args()

    await run_benchmark(
        benchmark_path=args.benchmark,
        variants=[Variant(name="full")],
        limit=args.limit,
        output_dir=args.output_dir,
        judge=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
