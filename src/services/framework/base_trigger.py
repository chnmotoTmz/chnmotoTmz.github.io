"""Minimal base class for workflow triggers."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class BaseTrigger(ABC):
    def __init__(self, workflow_name: str, config: Dict[str, Any]):
        self.workflow_name = workflow_name
        self.config = config
        self._workflow_runner: Optional[Callable[[Dict[str, Any]], Any]] = None

    def set_workflow_runner(self, runner: Callable[[Dict[str, Any]], Any]) -> None:
        self._workflow_runner = runner

    @abstractmethod
    def register(self, app: Any | None = None) -> None:
        """Prepare the trigger (e.g. attach routes, schedule jobs)."""
        raise NotImplementedError

    @abstractmethod
    def unregister(self) -> None:
        """Clean up any resources created during registration."""
        raise NotImplementedError

    def fire(self, initial_inputs: Dict[str, Any]) -> Any:
        if not self._workflow_runner:
            raise RuntimeError(
                f"Workflow runner not set for trigger in workflow '{self.workflow_name}'"
            )
        return self._workflow_runner(initial_inputs)

    @classmethod
    @abstractmethod
    def get_trigger_info(cls) -> Dict[str, Any]:
        """Return lightweight metadata describing the trigger type."""
        raise NotImplementedError

    def __repr__(self) -> str:
        info = self.get_trigger_info()
        return f"<{info['name']} trigger for workflow '{self.workflow_name}'>"
