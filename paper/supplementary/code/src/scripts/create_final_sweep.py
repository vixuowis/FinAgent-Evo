import json
import os

low_tids = ['T014','T016','T038','T040','T041','T043','T047','T048','T051','T052','T053','T057','T062','T064','T068','T076','T083','T107','T109','T110','T111','T112','T113','T121','T123','T124','T125','T128','T129','T132','T136','T140','T142','T143','T146','T147','T150','T151','T161','T162','T163','T170','T171','T183','T184','T188','T191','T192','T198','T201','T204','T207','T208','T209','T213','T215','T216','T217','T220','T226','T233','T234','T239','T252','T255','T263','T264','T265','T266','T268','T269','T282','T295']

all_tasks = []
for i in range(1, 5):
    path = f'src/benchmarks/shard_{i}.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            tasks = json.load(f)
            if isinstance(tasks, list):
                all_tasks.extend(tasks)
            elif isinstance(tasks, dict):
                # Handle case where it might be a dict with a key
                for k, v in tasks.items():
                    if isinstance(v, list):
                        all_tasks.extend(v)

final_sweep = [t for t in all_tasks if t.get('task_id') in low_tids]

with open('src/benchmarks/tasks/evofinagent_final_sweep.json', 'w') as f:
    json.dump(final_sweep, f, indent=2)

print(f"Created final sweep with {len(final_sweep)} tasks.")
