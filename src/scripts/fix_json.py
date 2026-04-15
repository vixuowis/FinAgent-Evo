import json

def read_broken_json(path):
    with open(path, "r") as f:
        content = f.read()
    
    # We will just parse each line and try to manually reconstruct the JSON array
    # Since it's just a flat list of objects appended together with `json.dump({"results": results}, f, indent=2)`
    
    results = []
    
    # Let's just find the blocks between {"task_id": ... and "error": ...}
    import re
    blocks = re.findall(r'\{\s*"task_id":.*?"error":.*?(?:null|"[^"]*")\n\s*\}', content, re.DOTALL)
    for b in blocks:
        try:
            results.append(json.loads(b))
        except Exception as e:
            # try to fix common trailing commas or unescaped quotes
            try:
                # sometimes LLM outputs unescaped quotes in reasoning
                b2 = re.sub(r'\\"', r'\\\\"', b)
                results.append(json.loads(b2))
            except:
                print("Skipping broken block")
                
    print(f"Recovered {len(results)} tasks.")
    with open("benchmarks/finagent_real_api_results_merged.json", "w") as f:
        json.dump({"results": results}, f, indent=2, ensure_ascii=False)

read_broken_json("benchmarks/finagent_real_api_results.json")
