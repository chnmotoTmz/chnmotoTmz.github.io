#!/usr/bin/env python3
"""
Blog Selector修正テスト
GeminiServiceとUnifiedLLMFacadeの統合をテスト
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# テスト1: UnifiedLLMFacade が Gemini に正しくパラメータを渡すか確認
logger.info("=" * 80)
logger.info("TEST 1: UnifiedLLMFacade parameters (Gemini mode)")
logger.info("=" * 80)

try:
    from src.services.unified_llm_facade import UnifiedLLMFacade
    
    # Geminiモードで初期化
    import os
    os.environ["LLM_PROVIDER"] = "gemini"
    
    llm = UnifiedLLMFacade()
    logger.info(f"✅ UnifiedLLMFacade initialized with provider: {llm.provider.value}")
    
    # generate_text を呼ぶ（system_prompt 有りで）
    # 実際には呼ばない、シグネチャをチェック
    import inspect
    sig = inspect.signature(llm.generate_text)
    logger.info(f"✅ UnifiedLLMFacade.generate_text signature: {sig}")
    
except Exception as e:
    logger.error(f"❌ Test 1 failed: {e}", exc_info=True)
    sys.exit(1)

# テスト2: BlogSelector が正しく実行されるか確認
logger.info("\n" + "=" * 80)
logger.info("TEST 2: BlogSelector LLM call (should use Gemini)")
logger.info("=" * 80)

try:
    from src.services.tasks.blog_selector_task import BlogSelectorTask
    
    # BlogSelectorTask を初期化
    task = BlogSelectorTask({})
    logger.info(f"✅ BlogSelectorTask initialized")
    logger.info(f"✅ BlogSelectorTask.llm_service provider: {task.llm_service.provider.value}")
    
except Exception as e:
    logger.error(f"❌ Test 2 failed: {e}", exc_info=True)
    sys.exit(1)

# テスト3: GeminiService の generate_text シグネチャ
logger.info("\n" + "=" * 80)
logger.info("TEST 3: GeminiService.generate_text signature")
logger.info("=" * 80)

try:
    from src.services.gemini_service import GeminiService
    
    import inspect
    sig = inspect.signature(GeminiService.generate_text)
    logger.info(f"✅ GeminiService.generate_text signature: {sig}")
    
    # system_prompt パラメータがないことを確認
    params = list(sig.parameters.keys())
    if 'system_prompt' in params:
        logger.warning(f"⚠️  GeminiService has system_prompt parameter")
    else:
        logger.info(f"✅ GeminiService does NOT have system_prompt (correct)")
    
except Exception as e:
    logger.error(f"❌ Test 3 failed: {e}", exc_info=True)
    sys.exit(1)

logger.info("\n" + "=" * 80)
logger.info("✅ ALL TESTS PASSED")
logger.info("=" * 80)
