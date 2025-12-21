"""
This module provides shared prompt templates and utility functions for generating prompts.
"""

# Common rules to be used across multiple tasks
COMMON_RULES = [
    "Use Markdown formatting.",
    "Ensure the output is concise and clear.",
    "Avoid redundant or contradictory instructions.",
    "Adhere to the specified character limits.",
    "Provide JSON output when requested, ensuring it is valid and well-formed."
]

def create_prompt(task_name, additional_rules=None, constraints=None):
    """
    Create a prompt by combining common rules with task-specific rules and constraints.

    Args:
        task_name (str): The name of the task for context.
        additional_rules (list of str): Task-specific rules to include.
        constraints (dict): Key-value pairs specifying constraints (e.g., {"max_chars": 200}).

    Returns:
        str: The generated prompt.
    """
    prompt = [f"Task: {task_name}"]
    prompt.extend(COMMON_RULES)

    if additional_rules:
        prompt.extend(additional_rules)

    if constraints:
        for key, value in constraints.items():
            prompt.append(f"Constraint: {key} = {value}")

    return "\n".join(prompt)