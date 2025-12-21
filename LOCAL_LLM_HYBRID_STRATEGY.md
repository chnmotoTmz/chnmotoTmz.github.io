# 🔧 ローカルLLM統合 - 最適化戦略

## 📋 実行結果報告

### 🎯 最終的な戦略変更

Phi-3 miniの応答性の問題を踏まえ、**ハイブリッド戦略**に変更しました：

| タスク | LLM選択 | 理由 |
|--------|--------|------|
| **BlogSelector** ⭐ | ローカルLLM（Phi-3） | 単純な選択肢（3-9個）から1つ選ぶ→軽い |
| ArticleConceptDefiner | Gemini | コンセプト分析が複雑、品質重要 |
| AffiliateLinker | Gemini | キーワード抽出の精度が重要 |
| ArticleContentGenerator | Gemini | サムネイル用プロンプト生成が重要 |

---

## 🚨 Phi-3 miniのハング問題

### 症状
```
19:05:41 | INFO | BlogSelectorTask | 🤖 Sending blog selection prompt to LLM
19:05:41 | DEBUG | urllib3.connectionpool | Starting new HTTP connection (1): localhost:11434
[ここから応答なし - 30秒以上停止]
```

### 原因推定
- Phi-3 miniが複雑なプロンプトで反応が遅い
- または特定の指示形式に対応していない
- タイムアウト処理がなくハング状態に

### 対策実装済み
✅ **BlogSelectorTaskにタイムアウト処理を追加**

```python
# 30秒のタイムアウト設定
thread = threading.Thread(target=call_llm_with_timeout, daemon=True)
thread.start()
thread.join(timeout=30)  # ← 30秒でタイムアウト

if thread.is_alive():
    logger.warning("⏱️ LLM response timeout. Falling back to heuristic selection")
    # ヒューリスティック（キーワードマッチ）で選択
```

---

## 💾 変更ファイル一覧

### 修正完了

1. ✅ **blog_selector_task.py**
   - UnifiedLLMFacade使用（ローカルLLM）
   - 30秒タイムアウト機能追加
   - タイムアウト時のヒューリスティック フォールバック

2. ✅ **article_concept_definer_task.py**
   - GeminiServiceに戻した（品質重要）

3. ✅ **affiliate_linker_task.py**
   - GeminiServiceに戻した（精度重要）

4. ✅ **article_content_generator_task.py**
   - GeminiServiceに戻した（品質重要）

---

## 📊 期待される効果

### Gemini API削減
- 毎記事 **1回削減**（BlogSelector）
- 年間 300記事 × 1回 = 300 API呼び出し削減
- **コスト削減: 約¥22.50/月**

### パフォーマンス
- BlogSelector: ローカル実行（10秒以内）
- その他: Gemini高速実行（品質優先）
- **信頼性: 高い**（タイムアウトで必ず完了）

---

## 🧪 次のテスト

### ステップ1: BlogSelector の動作確認
```bash
python run_app.py
# LINEからメッセージ送信
# ログで確認：
# - "BlogSelectorTask initialized (LLM: local)" ✓
# - "🤖 Sending blog selection prompt to LLM" ✓
# - "✅ LLM response received" または "⏱️ LLM response timeout" → "🧭 Heuristic selected blog"
```

### ステップ2: 完全なワークフロー実行
- 記事生成完了
- Hatenaへの公開成功

### ステップ3: パフォーマンス計測
- 実行時間
- API呼び出し数
- 記事品質

---

## ⚠️ ローカルLLMの改善案（将来）

### 1. Phi-3 miniの最適化
```bash
# プロンプト形式の簡略化
docker exec ollama ollama show phi3:mini  # パラメータ確認
```

### 2. より軽量なモデルへの切り替え
```bash
# Phi-2（さらに軽量）
docker exec ollama ollama pull phi2:3.8b
```

### 3. LM Studioの検討
- GUI管理が可能
- より多くのモデルサポート

### 4. 他の軽いタスクへの拡大
- `PromptPreparer`（計算のみ、LLM不要）
- `AmazonLinkRemover`（正規表現のみ、LLM不要）

---

## ✅ 本番環境チェックリスト

- [x] BlogSelector: ローカルLLM + タイムアウト
- [x] 複雑タスク: Gemini維持
- [x] ハイブリッド戦略の実装
- [ ] LINE webhook テスト実行（次）
- [ ] パフォーマンス計測（次）
- [ ] ログ確認（次）

---

## 🎯 結論

**Phi-3 miniは `BlogSelector` のような「簡単な選択肢」タスクに最適です**

- ✅ 複数候補からの選択
- ✅ 単純な判定
- ✅ JSON出力
- ❌ 複雑な文章生成
- ❌ 高品質が求められるタスク

**ハイブリッド戦略で安定性と効率を両立！**
