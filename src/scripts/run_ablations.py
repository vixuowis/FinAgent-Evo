import subprocess
import os
import sys
import time

def run_shard(variant_name, shard_idx):
    shard_file = f"src/benchmarks/shard_{shard_idx}.json"
    run_id = f"shard_{shard_idx}_{variant_name}"
    print(f"🚀 Starting ablation variant: {variant_name} | Shard: {shard_idx} | RunID: {run_id}")
    
    log_dir = "src/benchmarks/results/ablation_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = f"{log_dir}/log_{variant_name}_shard_{shard_idx}.txt"
    log_file = open(log_file_path, "a") # Use append to keep logs across resumes
    
    cmd = [
        ".venv/bin/python", "src/evaluation/complex_runner.py",
        "--benchmark", shard_file,
        "--variants", variant_name,
        "--output-dir", "src/benchmarks/results/ablation_run_300",
        "--repeat", "1",
        "--resume-run-id", run_id
    ]
    
    env = os.environ.copy()
    env["FINAGENT_TASK_TIMEOUT_SECONDS"] = "1800"
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
    os.makedirs("src/benchmarks/results/ablation_run_300", exist_ok=True)
    
    # Define ablation variants based on complex_runner.py build_variants logic
    # Prioritizing wo_evolution and wo_orchestration as requested by user
    variants = ["wo_evolution", "wo_orchestration", "wo_memory"]
    shards = [1, 2, 3, 4]
    max_workers = 4
    
    all_tasks = []
    for v in variants:
        for s in shards:
            all_tasks.append((v, s))
            
    print(f"\n🚀 Launching ablation experiments with concurrency limit: {max_workers}")
    print("Using Model: GLM-5.1 (via MAAS)")
    print("Logs are in src/benchmarks/results/ablation_logs/")
    
    active_processes = []
    
    try:
        task_idx = 0
        while task_idx < len(all_tasks) or active_processes:
            # Fill up workers
            while len(active_processes) < max_workers and task_idx < len(all_tasks):
                v, s = all_tasks[task_idx]
                p, log = run_shard(v, s)
                active_processes.append((v, s, p, log))
                task_idx += 1
                time.sleep(10) # Stagger to avoid API spikes
            
            # Check for finished processes
            still_active = []
            for v, s, p, log in active_processes:
                if p.poll() is None:
                    still_active.append((v, s, p, log))
                else:
                    exit_code = p.poll()
                    status = "✅ Success" if exit_code == 0 else f"❌ Failed (exit code: {exit_code})"
                    print(f"{status}: {v} | Shard {s}")
                    log.close()
            
            active_processes = still_active
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n⚠️ Terminating all workers...")
        for _, _, p, _ in active_processes:
            p.terminate()
    finally:
        for _, _, _, log in active_processes:
            if not log.closed:
                log.close()

if __name__ == "__main__":
    main()
