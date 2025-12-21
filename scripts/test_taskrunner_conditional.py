from src.framework.task_runner import TaskRunner

# Create a small inline workflow file
wf = {
    "workflow_name": "test_conditional",
    "steps": [
        {"id": "start", "module": "PassthroughTask", "inputs": {"flag": True}, "outputs": {"flag": "flag"}, "on_success": {"if": "flag", "then": "step_true", "else": "step_false"}},
        {"id": "step_true", "module": "PassthroughTask", "inputs": {}, "outputs": {}, "on_success": "end"},
        {"id": "step_false", "module": "PassthroughTask", "inputs": {}, "outputs": {}, "on_success": "end"}
    ],
    "variables": {"flag": False}
}

import json, tempfile
p = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(wf, p)
p.flush()
p.close()

runner = TaskRunner(p.name, enable_visualization=False)
ctx = runner.run(initial_inputs={})
print('Final context:', ctx)
