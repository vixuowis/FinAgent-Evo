import subprocess
import os
import sys
import time

def run_variant(variant_name):
    print(f"🚀 Starting background process for variant: {variant_name}")
    log_file = open(f"src/benchmarks/results/log_{variant_name}.txt", "w")
    
    # Use the existing complex_runner.py via command line
    cmd = [
        ".venv/bin/python", "src/evaluation/complex_runner.py",
        "--benchmark", "src/benchmarks/tasks/complex_tasks_300_unique.json",
        "--variants", variant_name,
        "--output-dir", "src/benchmarks/results/full_run_300",
        "--repeat", "1"
    ]
    
    # Set environment variables for the subprocess
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
    os.makedirs("src/benchmarks/results/full_run_300", exist_ok=True)
    
    variants = ["full", "finagent_dvampire", "finmem"]
    processes = []
    
    for v in variants:
        p, log = run_variant(v)
        processes.append((v, p, log))
        time.sleep(5) # Slight stagger to avoid rate limits on startup
    
    print("\n✅ All 3 variants are running in background.")
    print("Run IDs will be generated inside src/benchmarks/results/full_run_300/")
    print("Check individual logs in src/benchmarks/results/log_<variant>.txt for progress.")
    
    # Monitor processes
    try:
        while any(p.poll() is None for _, p, _ in processes):
            for v, p, _ in processes:
                if p.poll() is not None:
                    print(f"🔔 Variant {v} has finished with exit code {p.returncode}")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n⚠️ Received interrupt, terminating all benchmarks...")
        for _, p, _ in processes:
            p.terminate()
    finally:
        for _, _, log in processes:
            log.close()

if __name__ == "__main__":
    main()
