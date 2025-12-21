#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to verify prompt logging in action
"""
import sys
import logging
from pathlib import Path

# Set logging to DEBUG level with UTF-8 encoding
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s | %(name)s | %(message)s',
    encoding='utf-8'
)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import services
from src.services.content_enhancer_service import ContentEnhancerLLM

def main():
    print("\n" + "="*70)
    print("[TEST] Prompt Logging Verification")
    print("="*70)
    
    # Create test instance
    try:
        print("\n[INFO] Initializing ContentEnhancerLLM...")
        enhancer = ContentEnhancerLLM()
        print("[OK] ContentEnhancerLLM initialized")
        
        # Create a simple test prompt
        test_content = "This is a test article content for debugging." * 20
        
        print(f"\n[TEST] _generate_with_llm call will trigger prompt logging...")
        print(f"[TEST] Content length: {len(test_content)} chars\n")
        
        # This would trigger the logger.debug() calls
        # Note: This will fail without valid API keys, but we want to see the DEBUG logs
        try:
            result = enhancer._generate_with_llm(content=test_content)
            print(f"\n[RESULT] {result[0][:100] if result else 'None'}...")
        except Exception as e:
            print(f"\n[EXPECTED ERROR] {type(e).__name__}: {str(e)[:100]}")
            print("[NOTE] Error is expected - we only want to verify prompt logging")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("[NOTE] Check DEBUG logs above for:")
    print("       - 【LLM プロンプト本体】")
    print("       - First 800 characters of the prompt")
    print("       - Truncation indicator if prompt > 800 chars")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
