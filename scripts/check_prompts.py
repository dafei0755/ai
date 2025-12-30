import yaml, json, glob, os, sys
p = os.path.join(os.path.dirname(__file__), '..', 'intelligent_project_analyzer', 'config', 'prompts')
# normalize path
p = os.path.abspath(p)
yaml_files = sorted(glob.glob(os.path.join(p, "*.yaml")) + glob.glob(os.path.join(p, "*.yml")))
required = ["requirements_analyst", "review_agents", "result_aggregator", "dynamic_project_director"]

print("Prompts dir:", p)
if not yaml_files:
    print("ERROR: no yaml files found in prompts dir")
    sys.exit(2)

loaded = {}
errors = {}

for fpath in yaml_files:
    name = os.path.basename(fpath)
    stem = os.path.splitext(name)[0]
    try:
        with open(fpath, "r", encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        loaded[stem] = data
        print(f"[OK] Parsed {name} -> top keys: {list(data.keys())}")
    except Exception as e:
        errors[stem] = str(e)
        print(f"[ERROR] Failed to parse {name}: {e}")

print("\n--- Integrity checks ---")
missing = []
bad = []
for r in required:
    if r not in loaded:
        missing.append(r)
        print(f"[MISSING] {r}.yaml not loaded")
    else:
        cfg = loaded[r]
        if r == "review_agents":
            if not isinstance(cfg, dict) or "reviewers" not in cfg or not cfg.get("reviewers"):
                bad.append(r)
                print(f"[INVALID] review_agents.yaml missing 'reviewers' or empty reviewers")
        else:
            if not isinstance(cfg, dict) or not (cfg.get("prompt") or cfg.get("system_prompt")):
                bad.append(r)
                print(f"[INVALID] {r}.yaml missing top-level 'prompt' or 'system_prompt'")

if errors:
    print("\nParse errors found:")
    for k,v in errors.items():
        print(f" - {k}.yaml : {v}")

if not missing and not bad and not errors:
    print("\nAll core prompts present and look valid.")
    sys.exit(0)
else:
    print("\nPlease inspect the above issues.")
    sys.exit(1)
