"""
Passthrough Task - Simply passes through inputs to outputs unchanged.

Used for error handling and fallback scenarios where we want to use previous step outputs.
"""

import logging
from typing import Dict, Any

from src.framework.base_task import BaseTaskModule

logger = logging.getLogger(__name__)


class PassthroughTask(BaseTaskModule):
    """Passes through inputs to outputs unchanged."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simply pass through all inputs to outputs.
        
        Args:
            inputs: Dictionary of input values
        
        Returns:
            Same dictionary as output
        """
        logger.info("PassthroughTask: passing through inputs unchanged")
        return inputs
    
    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        """Returns metadata about the module."""
        return {
            "name": "PassthroughTask",
            "description": "Passes through inputs to outputs unchanged. Used for error handling and fallback.",
            "inputs": {},
            "outputs": {}
        }
