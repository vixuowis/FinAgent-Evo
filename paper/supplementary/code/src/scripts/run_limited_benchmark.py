
import subprocess
import os
import time

def run_task(variant_name, shard_idx, is_recovery=False):
    if is_recovery and variant_name == "full":
        shard_file = f"src/benchmarks/recovery_shard_{shard_idx}.json"
        run_id = f"recovery_shard_{shard_idx}_full"
        output_dir = "src/benchmarks/results/full_recovery_run"
    else:
        shard_file = f"src/benchmarks/shard_{shard_idx}.json"
        run_id = f"shard_{shard_idx}_{variant_name}"
        output_dir = "src/benchmarks/results/full_run_300_sharded"
        
    print(f"🚀 Launching: {variant_name} | Shard: {shard_idx} | Recovery: {is_recovery}")
    
    log_dir = "src/benchmarks/results/sharded_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = f"{log_dir}/log_{variant_name}_shard_{shard_idx}{'_rec' if is_recovery else ''}.txt"
    log_file = open(log_file_path, "a")
    
    cmd = [
        ".venv/bin/python", "src/evaluation/complex_runner.py",
        "--benchmark", shard_file,
        "--variants", variant_name,
        "--output-dir", output_dir,
        "--repeat", "1",
        "--resume-run-id", run_id
    ]
    
    env = os.environ.copy()
    env["FINAGENT_TASK_TIMEOUT_SECONDS"] = "1200"
    env["PYTHONPATH"] = "."
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True
    )
    return process, log_file

def main():
    max_workers = 3
    all_tasks = []
    
    # 1. Recovery tasks for Full
    for s in [1, 2, 3, 4]:
        all_tasks.append(("full", s, True))
    
    # 2. Regular tasks for others
    for v in ["finagent_dvampire", "finmem"]:
        for s in [1, 2, 3, 4]:
            all_tasks.append((v, s, False))
            
    print(f"\n🚀 Unified Benchmark Runner | Concurrency Limit: {max_workers}")
    active_processes = []
    
    try:
        task_idx = 0
        while task_idx < len(all_tasks) or active_processes:
            # Fill workers
            while len(active_processes) < max_workers and task_idx < len(all_tasks):
                v, s, is_rec = all_tasks[task_idx]
                p, log = run_task(v, s, is_rec)
                active_processes.append((v, s, p, log))
                task_idx += 1
                time.sleep(10)
            
            # Check status
            still_active = []
            for v, s, p, log in active_processes:
                if p.poll() is None:
                    still_active.append((v, s, p, log))
                else:
                    print(f"✅ Finished: {v} | Shard {s}")
                    log.close()
            active_processes = still_active
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n⚠️ Stopping all...")
        for _, _, p, _ in active_processes:
            p.terminate()
    finally:
        for _, _, _, log in active_processes:
            log.close()

if __name__ == "__main__":
    main()
