import json
import tempfile
from src.framework.task_runner import TaskRunner


def test_on_success_conditional_object_resolves():
    # Workflow where the first step's on_success is a conditional object
    wf = {
        "workflow_name": "test_conditional_on_success",
        "steps": [
            {
                "id": "start",
                "module": "PassthroughTask",
                "inputs": {"flag": True},
                "outputs": {"flag": "flag"},
                "on_success": {"if": "flag", "then": "step_true", "else": "step_false"}
            },
            {"id": "step_true", "module": "PassthroughTask", "inputs": {}, "outputs": {}, "on_success": "end"},
            {"id": "step_false", "module": "PassthroughTask", "inputs": {}, "outputs": {}, "on_success": "end"}
        ],
        "variables": {"flag": False}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as p:
        json.dump(wf, p)
        p.flush()
        runner = TaskRunner(p.name, enable_visualization=False)
        ctx = runner.run(initial_inputs={})

    assert ctx.get('flag') is True
*** End Patch