import json
import re

def extract_vars(expr):
    # ${var} または ${var.subkey} の "var" 部分を抽出
    return set(re.findall(r"\$\{([a-zA-Z0-9_\.]+)", json.dumps(expr)))

def check_workflow(filepath):
    with open(filepath, encoding="utf-8") as f:
        wf = json.load(f)
    steps = wf["steps"]
    step_ids = {s["id"] for s in steps if "id" in s}
    produced_vars = set()
    errors = []

    for step in steps:
        # outputsで生成される変数
        if "outputs" in step:
            for k, v in step["outputs"].items():
                produced_vars.add(v)
        # inputsで参照される変数
        if "inputs" in step:
            used_vars = extract_vars(step["inputs"])
            for var in used_vars:
                # ドット区切りの先頭だけ見る
                base_var = var.split(".")[0]
                if base_var not in produced_vars and base_var not in ("initial_input",):
                    errors.append(f"Step '{step['id']}' uses undefined variable: '{base_var}'")
        # on_success/on_failureのIDチェック
        for key in ("on_success", "on_failure"):
            if key in step and step[key] not in step_ids and step[key] not in ("end",):
                errors.append(f"Step '{step['id']}' has unknown {key}: '{step[key]}'")

    if errors:
        print("❌ ワークフローチェックNG:")
        for e in errors:
            print("  -", e)
    else:
        print("✅ ワークフロー変数・フロー整合性チェックOK")

if __name__ == "__main__":
    check_workflow("src/workflows/article_generation.json")