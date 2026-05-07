
import subprocess
import os
import time

def run_recovery_shard(shard_idx):
    shard_file = f"src/benchmarks/recovery_shard_{shard_idx}.json"
    run_id = f"recovery_shard_{shard_idx}_full"
    print(f"🚀 Starting Full Recovery | Shard: {shard_idx}")
    
    log_dir = "src/benchmarks/results/recovery_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = f"{log_dir}/log_full_recovery_shard_{shard_idx}.txt"
    log_file = open(log_file_path, "a")
    
    cmd = [
        ".venv/bin/python", "src/evaluation/complex_runner.py",
        "--benchmark", shard_file,
        "--variants", "full",
        "--output-dir", "src/benchmarks/results/full_recovery_run",
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
    os.makedirs("src/benchmarks/results/full_recovery_run", exist_ok=True)
    shards = [1, 2, 3, 4]
    max_workers = 2
    active_processes = []
    
    print(f"\n🚀 Launching recovery benchmark with concurrency limit: {max_workers}")
    
    try:
        shard_idx = 0
        while shard_idx < len(shards) or active_processes:
            # Fill up workers
            while len(active_processes) < max_workers and shard_idx < len(shards):
                s = shards[shard_idx]
                p, log = run_recovery_shard(s)
                active_processes.append((s, p, log))
                shard_idx += 1
                time.sleep(10) # Stagger
            
            # Check for finished processes
            still_active = []
            for s, p, log in active_processes:
                if p.poll() is None:
                    still_active.append((s, p, log))
                else:
                    print(f"✅ Recovery worker finished: Shard {s}")
                    log.close()
            
            active_processes = still_active
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n⚠️ Terminating all workers...")
        for _, p, _ in active_processes:
            p.terminate()
    finally:
        for _, _, log in active_processes:
            log.close()

if __name__ == "__main__":
    main()
