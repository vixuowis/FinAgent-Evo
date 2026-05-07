import json
import os

# Task 1
spec_file = ".trae/specs/neurips-review-revisions-2026/spec.md"
doc_file = "docs/neurips_2026_simulated_review.md"

with open(spec_file, "r") as f:
    content = f.read()

# Extract Appendix
appendix_start = content.find("## Appendix: Simulated NeurIPS Review Content")
if appendix_start != -1:
    appendix_content = content[appendix_start:]
    
    os.makedirs("docs", exist_ok=True)
    with open(doc_file, "w") as f:
        f.write(appendix_content)

# Task 4
json_file = "src/benchmarks/tasks/complex_tasks_real_api.json"
new_json_file = "src/benchmarks/tasks/complex_tasks_real_api_expanded.json"

with open(json_file, "r") as f:
    data = json.load(f)

tasks = data.get("tasks", [])
new_tasks = []

for i in range(100):
    task_copy = tasks[i % len(tasks)].copy()
    task_copy["task_id"] = f"T{i+1:02d}"
    new_tasks.append(task_copy)

data["tasks"] = new_tasks

with open(new_json_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
