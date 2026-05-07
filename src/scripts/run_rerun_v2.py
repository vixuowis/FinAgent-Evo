
import subprocess
import os
import sys
import time
import json

def shard_benchmark(benchmark_file, num_shards):
    with open(benchmark_file, 'r') as f:
        tasks = json.load(f)
    
    shard_size = (len(tasks) + num_shards - 1) // num_shards
    shards = []
    for i in range(num_shards):
        shard_tasks = tasks[i*shard_size : (i+1)*shard_size]
        if not shard_tasks: continue
        
        shard_file = benchmark_file.replace(".json", f"_shard_{i+1}.json")
        with open(shard_file, 'w') as f:
            json.dump(shard_tasks, f, indent=2, ensure_ascii=False)
        shards.append(shard_file)
    return shards

def run_rerun_shard(variant_name, benchmark_file, shard_idx):
    # CRITICAL: run_id must end with _[variant_name]
    run_id = f"rerun_s{shard_idx}_{variant_name}"
    print(f"🚀 Starting RERUN: {variant_name} | Shard: {shard_idx} | File: {benchmark_file} | RunID: {run_id}")
    
    log_dir = "src/benchmarks/results/rerun_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = f"{log_dir}/log_{run_id}.txt"
    log_file = open(log_file_path, "w")
    
    cmd = [
        ".venv/bin/python", "src/evaluation/complex_runner.py",
        "--benchmark", benchmark_file,
        "--variants", variant_name,
        "--output-dir", "src/benchmarks/results/reruns",
        "--repeat", "1",
        "--resume-run-id", run_id
    ]
    
    env = os.environ.copy()
    env["FINAGENT_TASK_TIMEOUT_SECONDS"] = "1800"
    env["LLM_TIMEOUT_SECONDS"] = "180"
    env["PYTHONPATH"] = "."
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True
    )
    return process, log_file

if __name__ == "__main__":
    os.makedirs("src/benchmarks/results/reruns", exist_ok=True)
    os.makedirs("src/benchmarks/results/rerun_logs", exist_ok=True)
    
    # Rerun 'full' with 2 shards
    num_shards = 2
    full_shards = shard_benchmark("src/benchmarks/tasks/rerun_full.json", num_shards)
    
    active_processes = []
    for idx, sfile in enumerate(full_shards):
        p, log = run_rerun_shard("full", sfile, idx+1)
        active_processes.append(("full", p, log))
            
    print(f"\n🚀 Monitoring {len(active_processes)} rerun shards...")
    try:
        while active_processes:
            still_active = []
            for v, p, log in active_processes:
                if p.poll() is None:
                    still_active.append((v, p, log))
                else:
                    print(f"✅ Rerun finished for: {v}")
                    log.close()
            active_processes = still_active
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n⚠️ Terminating reruns...")
        for _, p, _ in active_processes:
            p.terminate()
