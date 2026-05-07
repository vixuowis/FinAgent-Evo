import subprocess
import os
import time

def run_shard(shard_idx):
    shard_file = f"src/benchmarks/shard_{shard_idx}.json"
    run_id = f"shard_{shard_idx}_stepfix_full"
    log_dir = "src/benchmarks/results/ablation_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = f"{log_dir}/log_full_stepfix_shard_{shard_idx}.txt"
    log_file = open(log_file_path, "a")

    cmd = [
        ".venv/bin/python", "src/evaluation/complex_runner.py",
        "--benchmark", shard_file,
        "--variants", "full",
        "--output-dir", "src/benchmarks/results/ablation_run_300",
        "--repeat", "1",
        "--resume-run-id", run_id
    ]

    env = os.environ.copy()
    env["FINAGENT_TASK_TIMEOUT_SECONDS"] = "1800"
    env["PYTHONPATH"] = "."

    process = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT, text=True)
    print(f"Started shard {shard_idx} (PID {process.pid}) -> {log_file_path}")
    return process, log_file

def main():
    os.makedirs("src/benchmarks/results/ablation_run_300", exist_ok=True)
    shards = [1, 2, 3, 4]
    active = []

    for s in shards:
        p, log = run_shard(s)
        active.append((s, p, log))
        time.sleep(5)

    try:
        while active:
            still = []
            for s, p, log in active:
                if p.poll() is None:
                    still.append((s, p, log))
                else:
                    status = "OK" if p.returncode == 0 else f"FAILED({p.returncode})"
                    print(f"Shard {s}: {status}")
                    log.close()
            active = still
            time.sleep(30)
    except KeyboardInterrupt:
        for _, p, _ in active:
            p.terminate()
    finally:
        for _, _, log in active:
            if not log.closed:
                log.close()

if __name__ == "__main__":
    main()
