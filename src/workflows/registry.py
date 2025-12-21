"""
Workflow Registry: Discovers and manages workflow definitions.
"""
import os
import json
import yaml
import logging
from typing import List, Dict, Any, Optional

from src.workflows.exceptions import WorkflowNotFoundError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowRegistry:
    """
    Manages the discovery and retrieval of workflow definitions from a directory.
    """
    def __init__(self, workflows_dir: str = 'workflows'):
        """
        Initializes the registry by automatically detecting JSON/YAML files
        from the specified workflows directory.

        Args:
            workflows_dir: The directory containing workflow definition files.
        """
        self.workflows_dir = workflows_dir
        self._definitions = {}
        self._workflow_files = {}
        self._load_workflows()

    def _load_workflows(self):
        """
        Loads all .json and .yaml/.yml workflow definitions from the directory.
        """
        if not os.path.isdir(self.workflows_dir):
            logger.warning(f"Workflows directory '{self.workflows_dir}' not found.")
            return

        for filename in os.listdir(self.workflows_dir):
            if filename.endswith(('.json', '.yaml', '.yml')):
                workflow_name = os.path.splitext(filename)[0]
                filepath = os.path.join(self.workflows_dir, filename)
                self._workflow_files[workflow_name] = filepath
                try:
                    definition = self._load_definition_from_file(filepath)
                    if definition:
                        self.register_workflow(workflow_name, definition)
                except Exception as e:
                    logger.error(f"Failed to load or register workflow '{workflow_name}' from {filename}: {e}")

    def _load_definition_from_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Loads a single workflow definition from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filepath.endswith('.json'):
                    return json.load(f)
                elif filepath.endswith(('.yaml', '.yml')):
                    return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            logger.error(f"Error parsing workflow file {filepath}: {e}")
        return None

    def list_workflows(self) -> List[str]:
        """
        Returns a list of available workflow names.
        
        Returns:
            A list of strings, e.g., ['article_generation', ...].
        """
        return list(self._definitions.keys())

    def get_workflow_definition(self, workflow_name: str) -> Dict[str, Any]:
        """
        Retrieves a workflow definition. Supports both JSON and YAML.

        Args:
            workflow_name: The name of the workflow.

        Returns:
            The workflow definition as a dictionary.

        Raises:
            WorkflowNotFoundError: If the workflow is not found.
        """
        if workflow_name not in self._definitions:
            raise WorkflowNotFoundError(f"Workflow '{workflow_name}' not found.")
        return self._definitions[workflow_name]

    def register_workflow(self, workflow_name: str, definition: Dict[str, Any]):
        """
        Registers a new workflow definition in memory.

        Args:
            workflow_name: The name to register the workflow under.
            definition: The workflow definition dictionary.
        """
        self._definitions[workflow_name] = definition
        logger.info(f"Successfully registered workflow: '{workflow_name}'")

    def get_workflow_info(self, workflow_name: str) -> Dict[str, Any]:
        """
        Returns metadata about a specific workflow.

        Args:
            workflow_name: The name of the workflow.

        Returns:
            A dictionary containing metadata like name, description, step count,
            and required/optional inputs.
            
        Raises:
            WorkflowNotFoundError: If the workflow is not found.
        """
        definition = self.get_workflow_definition(workflow_name)
        
        # Simplified logic to identify inputs. A more robust implementation
        # would parse all ${initial_input.*} placeholders.
        required_inputs = []
        optional_inputs = []
        
        # This is a simplistic placeholder search. A real implementation might need
        # a more sophisticated regex or parsing strategy.
        raw_def = json.dumps(definition)
        placeholders = [p for p in raw_def.split('"${initial_input.')[1:]]
        
        for p in placeholders:
            input_name = p.split('}"')[0].split('}')[0].split('"')[0]
            if 'channel_id' in input_name: # As per spec, channel_id is optional
                if input_name not in optional_inputs:
                    optional_inputs.append(input_name)
            elif input_name not in required_inputs:
                required_inputs.append(input_name)

        return {
            'name': workflow_name,
            'description': definition.get('description', 'No description provided.'),
            'steps_count': len(definition.get('steps', [])),
            'required_inputs': required_inputs,
            'optional_inputs': optional_inputs
        }
