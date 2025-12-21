"""
Trigger Registry - Manages discovery, registration, and execution of workflow triggers.

This module provides a central registry for all trigger types and handles
the loading of workflow definitions to automatically register their triggers.
"""

import importlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Type

from .base_trigger import BaseTrigger
from .task_runner import TaskRunner

logger = logging.getLogger(__name__)


class TriggerRegistry:
    """Discovers and manages available trigger modules."""

    def __init__(self):
        self._triggers: Dict[str, Type[BaseTrigger]] = {}
        self._active_trigger_instances: Dict[str, BaseTrigger] = {}

    def register_trigger(self, name: str, trigger_class: Type[BaseTrigger]):
        """
        Manually register a trigger module.

        Args:
            name (str): The name to register the trigger under
            trigger_class (Type[BaseTrigger]): The trigger module class

        Raises:
            ValueError: If the class is not a subclass of BaseTrigger
        """
        if not issubclass(trigger_class, BaseTrigger):
            raise ValueError(f"Trigger class must be a subclass of BaseTrigger")

        self._triggers[name] = trigger_class
        logger.debug(f"Registered trigger: {name}")

    def discover_triggers(self, trigger_paths: list[str]):
        """
        Dynamically imports and discovers trigger modules from specified paths.

        Args:
            trigger_paths (list[str]): A list of directory paths to search for trigger modules.
        """
        logger.info("🔍 Discovering trigger modules...")

        for path in trigger_paths:
            if not os.path.exists(path):
                logger.warning(f"Trigger path does not exist: {path}")
                continue

            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py") and not file.startswith("_"):
                        module_name = os.path.splitext(file)[0]

                        # Convert file path to Python module path
                        rel_path = os.path.relpath(os.path.join(root, module_name), start=os.getcwd())
                        module_path = rel_path.replace(os.sep, '.')
                        module_path = module_path.lstrip('.')

                        try:
                            module = importlib.import_module(module_path)
                            for attribute_name in dir(module):
                                attribute = getattr(module, attribute_name)
                                if (isinstance(attribute, type) and
                                        issubclass(attribute, BaseTrigger) and
                                        attribute is not BaseTrigger):
                                    trigger_info = attribute.get_trigger_info()
                                    self._triggers[trigger_info['name']] = attribute
                                    logger.info(f"✅ {trigger_info['name']} ({trigger_info['type']})")
                        except Exception as e:
                            logger.error(f"❌ Failed to load trigger module {module_path}: {e}")

        # サマリー出力
        logger.info(f"📦 Total registered triggers: {len(self._triggers)}")
        if self._triggers:
            logger.info(f"📋 Available triggers: {', '.join(self._triggers.keys())}")
        else:
            logger.warning("⚠️ No triggers were registered!")

    def get_trigger(self, name: str) -> Type[BaseTrigger]:
        """
        Retrieves a trigger class by its name.

        Args:
            name (str): The name of the trigger to retrieve.

        Returns:
            Type[BaseTrigger]: The class of the requested trigger.

        Raises:
            ValueError: If the trigger is not found in the registry.
        """
        trigger_class = self._triggers.get(name)
        if not trigger_class:
            available = ', '.join(self._triggers.keys())
            raise ValueError(
                f"Trigger '{name}' not found in the registry. "
                f"Available triggers: {available}"
            )
        return trigger_class

    def load_and_register_workflow_triggers(
        self,
        workflow_dir: str,
        app: Any = None
    ) -> int:
        """
        Loads all workflow JSON files and registers their triggers.

        Args:
            workflow_dir (str): Directory containing workflow JSON files
            app (Any, optional): Application instance (e.g., Flask app) to pass to triggers

        Returns:
            int: Number of triggers successfully registered

        Raises:
            RuntimeError: If critical errors occur during registration
        """
        logger.info(f"📂 Loading workflows from: {workflow_dir}")

        if not os.path.exists(workflow_dir):
            logger.error(f"Workflow directory does not exist: {workflow_dir}")
            return 0

        registered_count = 0
        workflow_files = list(Path(workflow_dir).glob("*.json"))

        if not workflow_files:
            logger.warning(f"No workflow JSON files found in {workflow_dir}")
            return 0

        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow_def = json.load(f)

                workflow_name = workflow_def.get('workflow_name', workflow_file.stem)
                trigger_def = workflow_def.get('trigger')

                if not trigger_def:
                    logger.warning(f"⚠️ No trigger defined in workflow: {workflow_name}")
                    continue

                # Get trigger module name
                trigger_module = trigger_def.get('module')
                if not trigger_module:
                    logger.error(f"❌ Trigger module not specified in workflow: {workflow_name}")
                    continue

                # Get trigger class
                try:
                    trigger_class = self.get_trigger(trigger_module)
                except ValueError as e:
                    logger.error(f"❌ {e} (workflow: {workflow_name})")
                    continue

                # Instantiate trigger
                trigger_config = trigger_def.get('config', {})
                trigger_instance = trigger_class(
                    workflow_name=workflow_name,
                    config=trigger_config
                )

                # Create workflow runner callback
                def create_runner(wf_path):
                    def runner(initial_inputs: Dict[str, Any]):
                        task_runner = TaskRunner(str(wf_path))
                        task_runner.run(initial_inputs)
                    return runner

                workflow_runner = create_runner(workflow_file)
                trigger_instance.set_workflow_runner(workflow_runner)

                # Register trigger with app
                trigger_instance.register(app)

                self._active_trigger_instances[workflow_name] = trigger_instance
                registered_count += 1
                logger.info(f"✅ Registered trigger for workflow: {workflow_name}")

            except Exception as e:
                logger.error(
                    f"❌ Error loading workflow {workflow_file.name}: {e}",
                    exc_info=True
                )

        logger.info(f"🎉 Successfully registered {registered_count}/{len(workflow_files)} workflow triggers")
        return registered_count

    def unregister_all(self) -> int:
        """
        Unregisters all active triggers and cleans up resources.

        Returns:
            int: Number of triggers successfully unregistered
        """
        logger.info("🧹 Unregistering all triggers...")
        unregistered_count = 0

        for workflow_name, trigger_instance in list(self._active_trigger_instances.items()):
            try:
                trigger_instance.unregister()
                unregistered_count += 1
                logger.info(f"✅ Unregistered trigger for workflow: {workflow_name}")
            except Exception as e:
                logger.error(f"❌ Error unregistering trigger for {workflow_name}: {e}")

        self._active_trigger_instances.clear()
        logger.info(f"🎉 Unregistered {unregistered_count} triggers")
        return unregistered_count

    def get_active_triggers(self) -> Dict[str, BaseTrigger]:
        """
        Returns all currently active trigger instances.

        Returns:
            Dict[str, BaseTrigger]: Dictionary of workflow names to trigger instances
        """
        return self._active_trigger_instances.copy()


# Global instance
trigger_registry = TriggerRegistry()
