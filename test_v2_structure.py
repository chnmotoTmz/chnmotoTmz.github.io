import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from src_v2.tasks.command_parser_task import CommandParserTask
from src_v2.tasks.blog_selector_v2_task import BlogSelectorTaskV2

def test_v2_flow():
    print("=== Testing V2 Workflow Structure ===")
    
    # 1. Test Normal Flow
    print("\n--- Test 1: Normal Flow ---")
    inputs = {"initial_input": "こんにちは、Pythonについて書きたいです。", "user_id": "test_user"}
    
    parser_task = CommandParserTask()
    parser_result = parser_task.execute(inputs)
    print(f"Parser Result: {parser_result}")
    
    selector_task = BlogSelectorTaskV2()
    selector_inputs = {**inputs, **parser_result}
    selector_result = selector_task.execute(selector_inputs)
    print(f"Selector Result: {selector_result}")

    # 2. Test Command Flow (!Keyword)
    print("\n--- Test 2: Command Flow (!Engineer) ---")
    inputs = {"initial_input": "!Engineer #Write about Python", "user_id": "test_user"}
    
    parser_result = parser_task.execute(inputs)
    print(f"Parser Result: {parser_result}")
    
    selector_inputs = {**inputs, **parser_result}
    selector_result = selector_task.execute(selector_inputs)
    print(f"Selector Result: {selector_result}")

    # 3. Test Buffer Save (@1)
    print("\n--- Test 3: Buffer Save (@1) ---")
    inputs = {"initial_input": "@1", "user_id": "test_user"} # Saving empty text effectively? Or should we pass text?
    # In real scenario, @1 might save the *previous* article. 
    # But here CommandParserTask saves 'initial_input' if action is SAVE_TO_BUFFER.
    # Let's say we want to save a draft.
    inputs = {"initial_input": "@1 This is a draft text.", "user_id": "test_user"}
    
    parser_result = parser_task.execute(inputs)
    print(f"Parser Result: {parser_result}")
    
    # 4. Test Buffer Load & Post (@1!Engineer)
    print("\n--- Test 4: Buffer Load & Post (@1!Engineer) ---")
    inputs = {"initial_input": "@1!Engineer", "user_id": "test_user"}
    
    parser_result = parser_task.execute(inputs)
    print(f"Parser Result: {parser_result}")
    
    selector_inputs = {**inputs, **parser_result}
    selector_result = selector_task.execute(selector_inputs)
    print(f"Selector Result: {selector_result}")

if __name__ == "__main__":
    test_v2_flow()
