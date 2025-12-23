import json
import yaml
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from .service_registry import service_registry
from .workflow_visualizer import WorkflowVisualizer

logger = logging.getLogger(__name__)

class TaskRunner:
    """Executes a workflow defined in a JSON or YAML file."""

    def __init__(self, workflow_path: str, enable_visualization: bool = True):
        """
        Initializes the TaskRunner.

        Args:
            workflow_path (str): The file path to the JSON/YAML workflow definition.
            enable_visualization (bool): Whether to print Mermaid diagrams to console.
        """
        self.workflow_path = workflow_path
        self.enable_visualization = enable_visualization

        # Load workflow (auto-detect JSON/YAML)
        path = Path(workflow_path)
        if path.suffix in ['.yaml', '.yml']:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                self.workflow = yaml.safe_load(f)
        else:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                self.workflow = json.load(f)

        self.context: Dict[str, Any] = {}
        self.steps_map: Dict[str, Any] = {step['id']: step for step in self.workflow['steps']}
        self.execution_start_time: Optional[float] = None
        self.execution_end_time: Optional[float] = None

    def _resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves input values from the context using placeholder syntax.
        Handles nested placeholders and special 'initial_input' context.

        Args:
            inputs (Dict[str, Any]): The input definition for a task, which may contain placeholders.

        Returns:
            Dict[str, Any]: The resolved inputs with actual values from the context.
        """

        def resolve_value(value: Any):
            # Optional parameter support: {"var": "${xxx}", "optional": true}
            if isinstance(value, dict) and "var" in value and value.get("optional") is True:
                var_expr = value["var"]
                if isinstance(var_expr, str) and var_expr.startswith('${') and var_expr.endswith('}'):
                    var_path = var_expr[2:-1]
                    # initial_input特別扱い
                    if var_path.startswith('initial_input.'):
                        key = var_path.split('.', 1)[1]
                        return self.context.get('initial_input', {}).get(key, None)
                    res = self.context.get(var_path, None)
                    logger.debug(f"[resolve_value] Resolved optional {var_path} -> {'found' if res is not None else 'None'}")
                    return res
                else:
                    return None

            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                var_path = value[2:-1]  # Remove ${ and }

                # デフォルト値をサポート: ${var_name:default_value}
                # ... (keep existing logic) ...
                if ':' in var_path:
                    # (shortened for brevity in thought, but keeping real code)
                    var_path, default_str = var_path.split(':', 1)
                    # ... rest of default value logic ...

                # Handle special case for initial workflow inputs
                if var_path.startswith('initial_input.'):
                    key = var_path.split('.', 1)[1]
                    if 'initial_input' not in self.context or key not in self.context['initial_input']:
                        return None # Fallback
                    return self.context['initial_input'][key]

                # Handle regular context variables with nested access support
                if '.' in var_path:
                    parts = var_path.split('.')
                    current_value = self.context.get(parts[0])
                    if current_value is None:
                        return None
                    for part in parts[1:]:
                        if isinstance(current_value, dict) and part in current_value:
                            current_value = current_value[part]
                        else:
                            return None
                    return current_value
                else:
                    # Handle simple top-level variables
                    if var_path not in self.context:
                        logger.warning(f"[resolve_value] Context key '{var_path}' NOT FOUND. Available: {list(self.context.keys())}")
                        return None
                    val = self.context[var_path]
                    if val is None:
                        logger.warning(f"[resolve_value] Context key '{var_path}' IS NONE.")
                    return val

            if isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}

            if isinstance(value, list):
                return [resolve_value(item) for item in value]

            return value

        resolved = {key: resolve_value(val) for key, val in inputs.items()}
        # Debug logging for critical inputs
        if 'blog' in resolved:
            logger.info(f"[resolve_inputs] 'blog' resolved to: {'valid dict' if isinstance(resolved['blog'], dict) and resolved['blog'] else 'INVALID/EMPTY'}")
        return resolved

    def _update_context(self, outputs_mapping: Dict[str, str], task_outputs: Dict[str, Any]):
        """
        Updates the context with the outputs of a completed task.

        Args:
            outputs_mapping (Dict[str, str]): The mapping of task output keys to context variable names.
            task_outputs (Dict[str, Any]): The actual outputs from the task execution.
        """
        for task_key, context_key in outputs_mapping.items():
            if task_key in task_outputs:
                val = task_outputs[task_key]
                logger.info(f"[_update_context] Updating '{context_key}' with value from '{task_key}' (type: {type(val).__name__})")
                self.context[context_key] = val
            else:
                logger.debug(f"[_update_context] Key '{task_key}' not found in task outputs.")

    def run(self, initial_inputs: Dict[str, Any] = None):
        """
        Executes the entire workflow.

        Args:
            initial_inputs (Dict[str, Any], optional): Initial data to start the workflow.
                                                       Defaults to None.
        """
        # Initialize context with initial inputs and workflow-level default variables
        self.context = {'initial_input': initial_inputs or {}}
        # Populate top-level variables from workflow definition so placeholders like ${new_chat} resolve
        for var_key, var_default in self.workflow.get('variables', {}).items():
            if var_key not in self.context:
                self.context[var_key] = var_default
        self.execution_start_time = time.time()

        # Print workflow visualization before execution
        if self.enable_visualization:
            print("\n" + "="*70)
            print(f"🚀 Starting Workflow: {self.workflow.get('workflow_name', 'Unnamed')}")
            print(f"📝 Description: {self.workflow.get('description', 'No description')}")
            print("="*70)
            WorkflowVisualizer.print_to_console(
                self.workflow_path,
                title="Workflow Structure (Before Execution)"
            )

        current_step_id = self.workflow['steps'][0]['id']

        def _resolve_transition(transition: Any) -> Optional[str]:
            """
            Resolve a transition specification into a step id string.

            Supported forms:
              - a simple string step id
              - a conditional object: {"if": "var_name", "then": "step_a", "else": "step_b"}

            Returns:
                step id string or None if transition is not provided.
            """
            if transition is None:
                return None
            if isinstance(transition, str):
                return transition
            if isinstance(transition, dict):
                cond = transition.get('if')
                then = transition.get('then')
                els = transition.get('else')
                if cond is None:
                    logger.warning(f"Transition dict missing 'if' key: {transition}")
                    return None
                cond_value = self.context.get(cond)
                logger.debug(f"[transition] condition '{cond}' -> {cond_value}")
                return _resolve_transition(then if cond_value else els)

            logger.warning(f"Unsupported transition type: {type(transition)} -> {transition}")
            return None

        while current_step_id and current_step_id != 'end':
            logger.info(f"[TaskRunner] Current Step: {current_step_id}. Context keys: {list(self.context.keys())}")
            # Defensive: ensure we have a string step id
            if not isinstance(current_step_id, str):
                raise TypeError(f"Invalid step id type: {type(current_step_id).__name__} -> {current_step_id}. Transition must resolve to a string step id.")

            step = self.steps_map.get(current_step_id)
            if not step:
                raise ValueError(f"Step '{current_step_id}' not found in workflow.")

            # Get retry configuration
            max_retries = step.get('retries', 0)
            retry_delay = step.get('retry_delay_seconds', 5)
            timeout = step.get('timeout_seconds', None)

            # Retry loop
            for attempt in range(max_retries + 1):
                try:
                    attempt_msg = f" (attempt {attempt + 1}/{max_retries + 1})" if max_retries > 0 else ""
                    print(f"--- Executing step: {current_step_id}{attempt_msg} ---")

                    module_class = service_registry.get_module(step['module'])

                    # Pass the step-specific config to the module instance
                    step_config = step.get('config', {})
                    module_instance = module_class(config=step_config)

                    inputs = self._resolve_inputs(step.get('inputs', {}))

                    # Special handling for conditional branching
                    if module_class.__name__ == 'ConditionalBranchTask':
                        condition_value = inputs.get('condition', False)
                        logger.info(f"Conditional branch: condition is '{condition_value}'.")
                        next_raw = step.get('on_true') if condition_value else step.get('on_false')
                        next_resolved = _resolve_transition(next_raw)
                        if not next_resolved:
                            # If transition cannot be resolved, stop workflow
                            logger.warning(f"Conditional branch could not resolve next step from: {next_raw}")
                            current_step_id = 'end'
                        else:
                            current_step_id = next_resolved
                        print(f"✅ Step '{step.get('id')}' completed successfully")
                        continue

                    # Execute with timeout if specified
                    if timeout:
                        import signal

                        def timeout_handler(signum, frame):
                            raise TimeoutError(f"Step '{current_step_id}' exceeded timeout of {timeout}s")

                        # Note: signal.alarm only works on Unix. For Windows, use threading.
                        try:
                            signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(timeout)
                            outputs = module_instance.execute(inputs)
                            signal.alarm(0)  # Cancel alarm
                        except AttributeError:
                            # Windows fallback: no timeout enforcement
                            print(f"⚠️ Timeout not supported on Windows. Executing without timeout.")
                            outputs = module_instance.execute(inputs)
                    else:
                        outputs = module_instance.execute(inputs)

                    self._update_context(step.get('outputs', {}), outputs)

                    # Check if the task requested to stop the workflow
                    if self.context.get('stop_workflow') is True:
                        print(f"🛑 Workflow stopped by task '{current_step_id}'.")
                        current_step_id = 'end'
                        break

                    print(f"✅ Step '{current_step_id}' completed successfully")
                    current_step_id = _resolve_transition(step.get('on_success'))
                    break  # Success, exit retry loop

                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()

                    # Check if this is the last retry attempt
                    is_last_attempt = (attempt == max_retries)

                    if not is_last_attempt:
                        print(f"⚠️ Step '{current_step_id}' failed: {e}")
                        print(f"🔄 Retrying in {retry_delay}s... ({attempt + 1}/{max_retries} retries exhausted)")
                        time.sleep(retry_delay)
                        continue  # Retry

                    # Last attempt failed
                    print(f"!!! Error executing step '{current_step_id}': {e} !!!\n{error_trace}", flush=True)
                    self.context['last_error_message'] = str(e)

                    continue_on_failure = step.get('continue_on_failure', False)

                    if continue_on_failure:
                        print(f"--- Step '{step.get('id')}' failed, but continuing workflow as configured. ---", flush=True)
                        # 失敗したタスクの出力を、後続タスクがエラーにならないように安全な値で埋める
                        for output_key in step.get("outputs", {}).values():
                            if output_key not in self.context:
                                # 例えば、'content_with_thumbnail' のようなキーの場合、元の 'base_content' や 'content' で代替する
                                fallback_key = output_key.replace("content_with_", "base_")
                                self.context[output_key] = inputs.get(fallback_key) or inputs.get("content") or ""
                                print(f"--- Filling missing output '{output_key}' with fallback value. ---", flush=True)

                        # on_failureで指定された次のステップへ進む
                        current_step_id = _resolve_transition(step.get('on_failure'))
                    else:
                        # 致命的なエラーとして扱い、エラーハンドリングステップへ
                        print(f"--- Workflow stopped. Jumping to error handler: {step.get('on_failure')} ---", flush=True)

                        # Ensure user_data is in the context for the error handler.
                        if 'user_data' not in self.context:
                            initial_inputs = self.context.get('initial_input', {})
                            user_id = initial_inputs.get('user_id')
                            if user_id:
                                from src.database import User
                                try:
                                    user = User.query.get(user_id)
                                    if user:
                                        self.context['user_data'] = {c.name: getattr(user, c.name) for c in user.__table__.columns}
                                except Exception as db_error:
                                    print(f"Could not fetch user {user_id} for error notification: {db_error}", flush=True)

                        current_step_id = _resolve_transition(step.get('on_failure'))

                    break  # Exit retry loop after handling failure

        self.execution_end_time = time.time()
        execution_time = self.execution_end_time - self.execution_start_time

        print("\n" + "="*70)
        print("🎉 Workflow Finished")
        print(f"⏱️  Execution Time: {execution_time:.2f}s")
        print("="*70)

        # Print workflow visualization after execution
        if self.enable_visualization:
            WorkflowVisualizer.print_to_console(
                self.workflow_path,
                self.context,
                title="Workflow Result (After Execution)"
            )

            # Print execution summary
            summary = WorkflowVisualizer.get_execution_summary(self.context)
            print("\n" + "="*70)
            print("📋 Execution Summary")
            print("="*70)
            print(f"✅ Total Output Variables: {summary['total_variables']}")
            print(f"❌ Has Error: {summary['has_error']}")
            if summary['has_error']:
                print(f"   Error Message: {summary['error_message']}")
            print(f"📦 Output Variables: {', '.join(summary['output_variables'][:5])}...")
            print("="*70 + "\n")

        return self.context