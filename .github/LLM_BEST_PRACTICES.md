# LLM Model Usage & Error Handling Best Practices

This document outlines the best practices for using LLM models (specifically Gemini) in this project, based on lessons learned from rate limit issues and safety filter blocks.

## 1. Model Selection Strategy

### ❌ DO NOT Hardcode Model Names
Avoid specifying a specific model name in individual tasks or services unless absolutely necessary for a specific capability (e.g., vision).

**Bad:**
```python
# src/services/tasks/some_task.py
response = self.llm_service.generate_text(
    prompt,
    model_name="gemini-2.5-flash",  # <--- DON'T DO THIS
    ...
)
```

### ✅ DO Use Dynamic Selection
Pass `model_name=None` (or omit the argument) to let the `GeminiService` select the best available model based on current rate limits and priority.

**Good:**
```python
# src/services/tasks/some_task.py
response = self.llm_service.generate_text(
    prompt,
    model_name=None,  # Let the service decide
    ...
)
```

### Centralized Priority Management
The `GeminiService` (`src/services/gemini_service.py`) manages the priority list. Update `priority_models` in `generate_text` to change the preference order (e.g., preferring `lite` models when `pro` models are rate-limited).

## 2. Safety Settings

### Avoid False Positives
Gemini's default safety filters can be overly sensitive (e.g., flagging "red light" or "nighttime" as dangerous). Always explicitly configure safety settings to `BLOCK_NONE` for trusted internal generation tasks.

**Implementation:**
```python
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]
```

## 3. Error Handling & Fallbacks

### Fail-Safe for Non-Critical Steps
For steps like "Concept Definition" or "Thumbnail Prompt Generation", a failure should **not** stop the entire workflow. Implement fallbacks.

**Example:**
If `ArticleConceptDefinerTask` fails to generate a concept via LLM, return a default/generic concept dictionary instead of raising an exception.

### Fail-Fast for Critical Steps
For the main "Article Content Generation", if the LLM fails completely (after retries), the task should raise an exception to stop the workflow, rather than producing an empty or broken article.

## 4. Rate Limit Handling

The `GeminiService` implements automatic rotation and exclusion:
- If a model returns `429 Resource Exhausted`, it is added to a global exclusion list for the session.
- The service automatically retries with the next available model in the priority list.
- If all models fail, it rotates to the next API key.

**Action Item:**
When adding new tasks, ensure they use the shared `GeminiService` instance or initialization logic to benefit from this centralized rate limit handling.
