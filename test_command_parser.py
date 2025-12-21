#!/usr/bin/env python3
"""
Test script for CommandParser V2
Tests various command parsing scenarios
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src_v2.logic.command_parser import CommandParser, CommandContext

def test_basic_commands():
    """Test basic command parsing"""
    parser = CommandParser()

    # Test blog selection
    ctx = parser.parse("!ライフハック 記事を書いて")
    print("Test 1 - Blog selection:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Target Blog: {ctx.target_blog}")
    print(f"  Source Texts: {len(ctx.source_texts)}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "GENERATE"
    assert ctx.target_blog == "ライフハック"
    assert len(ctx.source_texts) == 1
    print("  ✅ PASSED\n")

    # Test repost
    ctx = parser.parse("@")
    print("Test 2 - Repost:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Is Repost: {ctx.is_repost}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "REPOST"
    assert ctx.is_repost == True
    print("  ✅ PASSED\n")

    # Test repost with blog
    ctx = parser.parse("@旅行 記事を書いて")
    print("Test 3 - Repost with blog:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Target Blog: {ctx.target_blog}")
    print(f"  Is Repost: {ctx.is_repost}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "REPOST"
    assert ctx.target_blog == "旅行"
    assert ctx.is_repost == True
    print("  ✅ PASSED\n")

    # Test style prompt
    ctx = parser.parse("#カジュアルな口調で 記事を書いて")
    print("Test 4 - Style prompt:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Style Prompt: {ctx.style_prompt}")
    assert ctx.type == "NORMAL"
    assert ctx.action == "GENERATE"
    assert ctx.style_prompt == "カジュアルな口調で"
    print("  ✅ PASSED\n")

    # Test combined commands
    ctx = parser.parse_multi(["!ライフハック", "@", "#推理小説風"])
    print("Test 5 - Combined commands:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Target Blog: {ctx.target_blog}")
    print(f"  Is Repost: {ctx.is_repost}")
    print(f"  Style Prompt: {ctx.style_prompt}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "REPOST"
    assert ctx.target_blog == "ライフハック"
    assert ctx.is_repost == True
    assert ctx.style_prompt == "推理小説風"
    print("  ✅ PASSED\n")

    # Test buffer operations
    ctx = parser.parse("@1")
    print("Test 6 - Buffer load:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Buffer Slot: {ctx.buffer_slot}")
    assert ctx.type == "BUFFER_OP"
    assert ctx.action == "SAVE_TO_BUFFER"
    assert ctx.buffer_slot == 1
    print("  ✅ PASSED\n")

    ctx = parser.parse("@1!旅行")
    print("Test 7 - Buffer load with blog:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Buffer Slot: {ctx.buffer_slot}")
    print(f"  Target Blog: {ctx.target_blog}")
    assert ctx.type == "BUFFER_OP"
    assert ctx.action == "GENERATE_FROM_BUFFER"
    assert ctx.buffer_slot == 1
    assert ctx.target_blog == "旅行"
    print("  ✅ PASSED\n")

def test_complex_scenarios():
    """Test complex parsing scenarios"""
    parser = CommandParser()

    # Test inline style with blog command
    ctx = parser.parse("!ライフハック #カジュアル 記事内容")
    print("Test 8 - Blog command with inline style:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Target Blog: {ctx.target_blog}")
    print(f"  Style Prompt: {ctx.style_prompt}")
    print(f"  Source Texts: {len(ctx.source_texts)}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "GENERATE"
    assert ctx.target_blog == "ライフハック"
    assert ctx.style_prompt == "カジュアル"
    assert len(ctx.source_texts) == 1
    assert ctx.source_texts[0] == "記事内容"
    print("  ✅ PASSED\n")

    # Test repost with rewrite
    ctx = parser.parse("@ #リライト 記事内容")
    print("Test 9 - Repost with rewrite:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Is Repost: {ctx.is_repost}")
    print(f"  Has Rewrite: {ctx.has_rewrite_instruction}")
    print(f"  Style Prompt: {ctx.style_prompt}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "REPOST"
    assert ctx.is_repost == True
    assert ctx.has_rewrite_instruction == True
    assert ctx.style_prompt == "リライト"
    print("  ✅ PASSED\n")

    # Test normal text
    ctx = parser.parse("普通の記事内容です。")
    print("Test 10 - Normal text:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Source Texts: {len(ctx.source_texts)}")
    assert ctx.type == "NORMAL"
    assert ctx.action == "GENERATE"
    assert len(ctx.source_texts) == 1
    assert ctx.source_texts[0] == "普通の記事内容です。"
    print("  ✅ PASSED\n")

def test_edge_cases():
    """Test edge cases"""
    parser = CommandParser()

    # Test empty input
    ctx = parser.parse("")
    print("Test 11 - Empty input:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    assert ctx.type == "NORMAL"
    assert ctx.action == "GENERATE"
    print("  ✅ PASSED\n")

    # Test whitespace only
    ctx = parser.parse("   ")
    print("Test 12 - Whitespace only:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    assert ctx.type == "NORMAL"
    assert ctx.action == "GENERATE"
    print("  ✅ PASSED\n")

    # Test multiple spaces
    ctx = parser.parse("!  ライフハック   記事")
    print("Test 13 - Multiple spaces:")
    print(f"  Type: {ctx.type}, Action: {ctx.action}")
    print(f"  Target Blog: {ctx.target_blog}")
    assert ctx.type == "COMMAND"
    assert ctx.action == "GENERATE"
    assert ctx.target_blog == "ライフハック"
    print("  ✅ PASSED\n")

def main():
    """Run all tests"""
    print("🧪 CommandParser V2 Test Suite")
    print("=" * 50)

    try:
        test_basic_commands()
        test_complex_scenarios()
        test_edge_cases()

        print("🎉 All tests passed!")
        return 0

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())