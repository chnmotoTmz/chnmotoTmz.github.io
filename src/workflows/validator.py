"""
Workflow Validator: Ensures workflow definitions are well-formed and executable.
"""
import logging
from typing import List, Dict, Any, Tuple, Set

# To check for module existence, we need a way to know where task modules are.
# This is a placeholder for how we might locate the task modules.
# A more robust solution would use importlib or a predefined mapping.
# For now, we assume a function `task_module_exists` is available.
# We will need to implement this based on the project structure.

# Let's assume task modules are in a specific directory, e.g., `src.workflows.tasks`
# This is a mock implementation for now.
# TODO: Replace with actual module discovery logic.
def _placeholder_task_module_exists(module_name: str) -> bool:
    """Placeholder check for task module existence."""
    # In a real implementation, this would check if `src.workflows.tasks.{module_name}`
    # can be imported.
    # For this design, we'll have to find where the 14 tasks are located.
    return True # Assume all modules exist for now

from src.workflows.registry import WorkflowRegistry
from src.workflows.exceptions import WorkflowNotFoundError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowValidator:
    """
    Validates workflow definitions and their inputs.
    """
    def __init__(self, registry: WorkflowRegistry):
        """
        Initializes the validator with a workflow registry.

        Args:
            registry: An instance of WorkflowRegistry.
        """
        self.registry = registry

    def validate(self, workflow_name: str) -> Tuple[bool, List[str]]:
        """
        Validates a workflow definition against a set of rules.

        Args:
            workflow_name: The name of the workflow to validate.

        Returns:
            A tuple containing a boolean (is_valid) and a list of error messages.
        """
        errors: List[str] = []
        try:
            definition = self.registry.get_workflow_definition(workflow_name)
        except WorkflowNotFoundError as e:
            return False, [str(e)]

        if 'workflow_name' not in definition or 'steps' not in definition:
            errors.append("Workflow must have 'workflow_name' and 'steps' keys.")
            return False, errors

        if not isinstance(definition['steps'], list) or not definition['steps']:
            errors.append("'steps' must be a non-empty list.")
            return False, errors

        step_ids: Set[str] = set()
        declared_vars: Set[str] = set(self.registry.get_workflow_info(workflow_name).get('required_inputs', []))
        declared_vars.update(self.registry.get_workflow_info(workflow_name).get('optional_inputs', []))
        declared_vars.add('last_error_message') # Special variable for error handling

        for i, step in enumerate(definition['steps']):
            step_id = step.get('id')
            if not step_id:
                errors.append(f"Step {i} is missing an 'id'.")
                continue
            
            step_ids.add(step_id)

            required_keys = ['id', 'module', 'on_success', 'on_failure']
            for key in required_keys:
                if key not in step:
                    errors.append(f"Step '{step_id}' is missing required key: '{key}'.")

            module_name = step.get('module')
            if module_name and not _placeholder_task_module_exists(module_name):
                errors.append(f"Step '{step_id}' refers to a non-existent module: '{module_name}'.")

            # Validate variable references in inputs
            if 'inputs' in step and isinstance(step['inputs'], dict):
                for key, value in step['inputs'].items():
                    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                        var_name = value[2:-1].split('.')[0]
                        if var_name != 'initial_input' and var_name not in declared_vars:
                            errors.append(f"Step '{step_id}' uses an undeclared variable: '{var_name}'.")
            
            # Add outputs of this step to declared variables for subsequent steps
            if 'outputs' in step and isinstance(step['outputs'], dict):
                for var in step['outputs'].values():
                    declared_vars.add(var)

        # Validate on_success and on_failure transitions
        for step in definition['steps']:
            step_id = step.get('id')
            for transition in ['on_success', 'on_failure']:
                target = step.get(transition)
                if target and target != 'end' and target not in step_ids:
                    errors.append(f"Step '{step_id}' has an invalid transition target '{target}' for '{transition}'.")

        return not errors, errors

    def validate_inputs(self, workflow_name: str, inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates the provided inputs against the workflow's requirements.

        Args:
            workflow_name: The name of the workflow.
            inputs: The dictionary of inputs provided at execution time.

        Returns:
            A tuple containing a boolean (is_valid) and a list of error messages.
        """
        errors: List[str] = []
        try:
            info = self.registry.get_workflow_info(workflow_name)
            required_inputs = info.get('required_inputs', [])
        except WorkflowNotFoundError as e:
            return False, [str(e)]

        missing_inputs = [req for req in required_inputs if req not in inputs]
        if missing_inputs:
            errors.append(f"Missing required inputs: {', '.join(missing_inputs)}.")

        return not errors, errors
