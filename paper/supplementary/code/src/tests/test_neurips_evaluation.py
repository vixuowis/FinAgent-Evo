import asyncio
import json
import os
import shutil
import unittest


class TestNeuripsEvaluation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ["DASHSCOPE_API_KEY"] = "dummy"
        os.environ["JUDGE_API_KEY"] = "dummy"
        os.environ["QVERIS_API_KEY"] = "dummy"
        self.tmp_dir = "src/benchmarks/results_test_tmp"
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.benchmark_path = os.path.join(self.tmp_dir, "benchmark.json")
        with open(self.benchmark_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "tasks": [
                        {
                            "task_id": "T00",
                            "query": "测试任务：获取AAPL股价并计算 2+2。",
                            "difficulty": "easy",
                            "evaluation_criteria": {
                                "final_answer_metrics": ["AAPL价格", "2+2结果"],
                                "min_tool_calls": 2,
                                "must_call_sequence": [["get_stock_price", "calculator"]],
                            },
                        }
                    ]
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    async def asyncTearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    async def test_runner_dry_run_schema(self):
        from src.evaluation.complex_runner import Variant, run_benchmark

        run_ids = await run_benchmark(
            benchmark_path=self.benchmark_path,
            variants=[Variant(name="full")],
            limit=1,
            output_dir=self.tmp_dir,
            judge=True,
        )
        self.assertEqual(len(run_ids), 1)
        run_id = run_ids[0]
        run_path = os.path.join(self.tmp_dir, run_id, "run.json")
        self.assertTrue(os.path.exists(run_path))

        with open(run_path, "r", encoding="utf-8") as f:
            obj = json.load(f)

        self.assertIn("schema_version", obj)
        self.assertIn("variant", obj)
        self.assertIn("judge", obj)
        self.assertIn("summary", obj)
        self.assertIn("results", obj)
        self.assertEqual(obj["benchmark"]["task_count"], 1)
        self.assertEqual(len(obj["results"]), 1)
        self.assertIn("run", obj["results"][0])
        self.assertIn("agent", obj["results"][0])

    def test_qveris_cache_roundtrip(self):
        os.environ["QVERIS_CACHE_ENABLED"] = "1"
        os.environ["QVERIS_CACHE_TTL_SECONDS"] = "60"
        os.environ["QVERIS_CACHE_DIR"] = os.path.join(self.tmp_dir, "qveris_cache")

        import src.core.qveris_cache as qc

        qc._DEFAULT_CACHE = None
        cache = qc.get_qveris_cache()

        tool_id = "t"
        params = {"a": 1}
        cache.set(tool_id, params, "ok")
        val, hit = cache.get(tool_id, params)
        self.assertTrue(hit)
        self.assertEqual(val, "ok")


if __name__ == "__main__":
    unittest.main()
