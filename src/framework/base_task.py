from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTaskModule(ABC):
    """Abstract base class for all task modules in the workflow framework."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the task module with its configuration.

        Args:
            config (Dict[str, Any]): Configuration parameters for the module.
        """
        self.config = config

    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the main logic of the task.

        Args:
            inputs (Dict[str, Any]): A dictionary of inputs for the task.
                                     These are typically outputs from previous tasks.

        Returns:
            Dict[str, Any]: A dictionary of outputs from the task.
        """
        pass

    @classmethod
    @abstractmethod
    def get_module_info(cls) -> Dict[str, Any]:
        """
        Returns metadata about the module.

        This includes its name, a description of its purpose, and definitions
        of its expected inputs and outputs.

        Returns:
            Dict[str, Any]: A dictionary containing module metadata.
        """
        pass