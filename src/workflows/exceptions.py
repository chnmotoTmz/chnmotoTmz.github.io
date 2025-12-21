"""
Custom exceptions for the workflow system.
"""

class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""
    pass

class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow definition is not found."""
    pass

class WorkflowValidationError(WorkflowError):
    """Raised when a workflow definition fails validation."""
    pass

class WorkflowExecutionError(WorkflowError):
    """Raised during the execution of a workflow."""
    pass

class TaskModuleNotFoundError(WorkflowError):
    """Raised when a task module specified in a workflow is not found."""
    pass
