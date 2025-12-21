"""
RAG (Retrieval-Augmented Generation) ユーティリティモジュール。

このモジュールは、Flaskから独立した、再利用可能なRAG機能を提供します。
TF-IDFベースの類似度検索により、テキストコーパスからの関連ドキュメント検索を実現します。

主な機能:
- モデルの学習と保存 (RAGService.train_and_save_model)
- 保存済みモデルを使用した類似検索 (RAGService.predict_with_model)
- モデルの再学習が必要かどうかの判定 (RAGService.needs_retrain)
- モデルのメタデータ管理 (RAGService.get_model_metadata)

アーキテクチャ:
- RAGService: メインサービスクラス
- TextProcessor: テキスト前処理を担当
- ModelManager: モデルの保存・読み込みを担当
- RAGConfig: 設定管理
"""

from __future__ import annotations

import os
import re
import json
import pickle
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

# --- カスタム例外クラス ---

class RAGError(Exception):
    """RAG関連の基本例外クラス"""
    pass

class ModelNotFoundError(RAGError):
    """モデルが見つからない場合の例外"""
    pass

class DependencyError(RAGError):
    """必要な依存ライブラリが利用できない場合の例外"""
    pass

class ConfigurationError(RAGError):
    """設定エラーの場合の例外"""
    pass

# --- オプショナルな依存ライブラリのインポート ---

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False

try:
    from janome.tokenizer import Tokenizer
    from janome.analyzer import Analyzer
    from janome.charfilter import UnicodeNormalizeCharFilter
    from janome.tokenfilter import POSKeepFilter, POSStopFilter, LowerCaseFilter
    _JANOME_AVAILABLE = True
except ImportError:
    _JANOME_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

# --- 設定管理 ---

@dataclass
class RAGConfig:
    """RAGサービスの設定を管理するデータクラス"""

    # モデル保存ディレクトリ
    models_dir: Path = field(default_factory=lambda: Path.cwd() / 'models')

    # TF-IDFベクトライザの設定
    max_features: int = 8000
    ngram_range: Tuple[int, int] = (1, 2)

    # 再学習判定の閾値
    retrain_threshold_ratio: float = 0.15

    # テキスト前処理設定
    min_token_length: int = 2
    keep_pos: List[str] = field(default_factory=lambda: ['名詞', '動詞', '形容詞'])
    stop_pos: List[str] = field(default_factory=lambda: ['助詞', '助動詞'])

    # ログ設定
    log_level: int = logging.INFO

    def __post_init__(self):
        """設定の検証と初期化"""
        if self.max_features <= 0:
            raise ConfigurationError("max_features must be positive")
        if not (0 < self.retrain_threshold_ratio <= 1):
            raise ConfigurationError("retrain_threshold_ratio must be between 0 and 1")
        if self.min_token_length < 1:
            raise ConfigurationError("min_token_length must be at least 1")

        # ディレクトリの作成
        self.models_dir.mkdir(parents=True, exist_ok=True)

# --- テキスト処理クラス ---

class TextProcessor:
    """テキストの前処理を担当するクラス"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self._tokenizer = None

        if _JANOME_AVAILABLE:
            self._tokenizer = Tokenizer()
        else:
            logging.warning("Janome not available, using fallback tokenization")

    def normalize_text(self, text: Any) -> str:
        """
        テキストを正規化し、不要な文字を除去します。

        Args:
            text: 入力テキスト

        Returns:
            正規化されたテキスト
        """
        if not isinstance(text, str):
            return ''

        # 日本語、英語、数字、および基本的な句読点以外の文字を除去
        pattern = r'[^a-zA-Z0-9ぁ-んァ-ヶヷ-ヺー一-龥、。！？\s.,!?]'
        return re.sub(pattern, '', text)

    def tokenize_for_vector(self, text: str) -> str:
        """
        テキストをベクトル化のためにトークンに分割します。

        Args:
            text: 入力テキスト

        Returns:
            トークン化されたテキスト
        """
        if not text:
            return ''

        if self._tokenizer and _JANOME_AVAILABLE:
            return self._tokenize_with_janome(text)
        else:
            return self._tokenize_fallback(text)

    def _tokenize_with_janome(self, text: str) -> str:
        """Janomeを使用した形態素解析"""
        char_filters = [UnicodeNormalizeCharFilter()]
        token_filters = [
            POSKeepFilter(self.config.keep_pos),
            POSStopFilter(self.config.stop_pos),
            LowerCaseFilter(),
        ]

        analyzer = Analyzer(
            char_filters=char_filters,
            tokenizer=self._tokenizer,
            token_filters=token_filters
        )

        return ' '.join([token.surface for token in analyzer.analyze(text)])

    def _tokenize_fallback(self, text: str) -> str:
        """Janomeが利用できない場合のフォールバック"""
        # 日本語と英語の単語を抽出
        pattern = r'[A-Za-z0-9ぁ-んァ-ヶ一-龥]{' + str(self.config.min_token_length) + r',}'
        return ' '.join(re.findall(pattern, text))

    def prepare_corpus(self, texts: List[str]) -> List[str]:
        """
        コーパス全体に対して前処理を適用します。

        Args:
            texts: 入力テキストのリスト

        Returns:
            前処理済みのテキストのリスト
        """
        if not texts:
            return []

        # Noneや空文字列を除外
        valid_texts = [t for t in texts if isinstance(t, str) and t.strip()]

        processed = []
        for text in valid_texts:
            normalized = self.normalize_text(text)
            tokenized = self.tokenize_for_vector(normalized)
            if tokenized:  # 空でない場合のみ追加
                processed.append(tokenized)

        return processed

# --- モデル管理クラス ---

class ModelManager:
    """モデルの保存・読み込みを担当するクラス"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_model_paths(self, model_name: str) -> Tuple[Path, Path]:
        """
        モデル名からファイルパスを生成します。

        Args:
            model_name: モデル名

        Returns:
            (モデルファイルパス, メタデータファイルパス) のタプル
        """
        pkl_path = self.config.models_dir / f'{model_name}.pkl'
        meta_path = self.config.models_dir / f'{model_name}_meta.json'
        return pkl_path, meta_path

    def save_model_metadata(self, model_name: str, metadata: Dict[str, Any]) -> None:
        """
        モデルのメタデータをJSONファイルに保存します。

        Args:
            model_name: モデル名
            metadata: メタデータ辞書
        """
        _, meta_path = self.get_model_paths(model_name)

        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise RAGError(f"Failed to save metadata for model '{model_name}': {e}")

    def load_model_metadata(self, model_name: str) -> Dict[str, Any]:
        """
        モデルのメタデータをJSONファイルから読み込みます。

        Args:
            model_name: モデル名

        Returns:
            メタデータ辞書
        """
        _, meta_path = self.get_model_paths(model_name)

        if not meta_path.exists():
            return {}

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load metadata for '{model_name}': {e}")
            return {}

    def save_model(self, model_name: str, model_data: Any) -> None:
        """
        モデルデータをpickleファイルに保存します。

        Args:
            model_name: モデル名
            model_data: 保存するモデルデータ
        """
        pkl_path, _ = self.get_model_paths(model_name)

        try:
            with open(pkl_path, 'wb') as f:
                pickle.dump(model_data, f)
        except IOError as e:
            raise RAGError(f"Failed to save model '{model_name}': {e}")

    def load_model(self, model_name: str) -> Any:
        """
        モデルデータをpickleファイルから読み込みます。

        Args:
            model_name: モデル名

        Returns:
            読み込まれたモデルデータ

        Raises:
            ModelNotFoundError: モデルファイルが存在しない場合
            RAGError: 読み込みに失敗した場合
        """
        pkl_path, _ = self.get_model_paths(model_name)

        if not pkl_path.exists():
            raise ModelNotFoundError(f"Model file not found: {pkl_path}")

        try:
            with open(pkl_path, 'rb') as f:
                return pickle.load(f)
        except (IOError, pickle.UnpicklingError) as e:
            raise RAGError(f"Failed to load model '{model_name}': {e}")

    def model_exists(self, model_name: str) -> bool:
        """
        指定されたモデルが存在するかどうかを確認します。

        Args:
            model_name: モデル名

        Returns:
            モデルが存在するかどうか
        """
        pkl_path, _ = self.get_model_paths(model_name)
        return pkl_path.exists()

# --- メインRAGサービスクラス ---

class RAGService:
    """
    RAG (Retrieval-Augmented Generation) のメインサービスクラス。

    このクラスはTF-IDFベースの類似度検索を提供し、
    テキストコーパスからの関連ドキュメント検索を実現します。
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        RAGServiceの初期化。

        Args:
            config: 設定オブジェクト。Noneの場合はデフォルト設定を使用。
        """
        self.config = config or RAGConfig()
        self.text_processor = TextProcessor(self.config)
        self.model_manager = ModelManager(self.config)
        self.logger = logging.getLogger(self.__class__.__name__)

        # 依存関係のチェック
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """必要な依存ライブラリが利用可能かをチェックします。"""
        if not _SKLEARN_AVAILABLE:
            raise DependencyError("scikit-learn is required for RAG functionality")
        if not _PANDAS_AVAILABLE:
            raise DependencyError("pandas is required for RAG functionality")

    def train_and_save_model(self, texts: List[str], model_name: str) -> Tuple[bool, str]:
        """
        与えられたテキストコーパスからTF-IDFモデルを学習し、ファイルに保存します。

        Args:
            texts: 学習用のテキストリスト
            model_name: 保存するモデル名

        Returns:
            (成功フラグ, メッセージ) のタプル
        """
        if not texts:
            return False, 'The provided corpus is empty.'

        try:
            self.logger.info(f"Starting training for model '{model_name}' with {len(texts)} documents")

            # テキストの前処理
            processed_corpus = self.text_processor.prepare_corpus(texts)
            if not processed_corpus:
                return False, 'No valid texts after preprocessing.'

            # DataFrameの作成
            raw_df = pd.DataFrame({'text': texts})

            # TF-IDFベクトライザの初期化と学習
            vectorizer = TfidfVectorizer(
                max_features=self.config.max_features,
                ngram_range=self.config.ngram_range
            )
            tfidf_matrix = vectorizer.fit_transform(processed_corpus)

            # モデルの保存
            model_data = (vectorizer, tfidf_matrix, raw_df)
            self.model_manager.save_model(model_name, model_data)

            # メタデータの作成と保存
            metadata = {
                'model': model_name,
                'docs': len(texts),
                'trained_at': datetime.utcnow().isoformat(),
                'features': len(vectorizer.get_feature_names_out()),
                'config': {
                    'max_features': self.config.max_features,
                    'ngram_range': self.config.ngram_range,
                }
            }
            self.model_manager.save_model_metadata(model_name, metadata)

            self.logger.info(f"RAG model '{model_name}' trained successfully with {len(texts)} documents.")
            return True, 'Model trained successfully.'

        except Exception as e:
            error_msg = f"Failed to train and save model '{model_name}': {str(e)}"
            self.logger.exception(error_msg)
            return False, error_msg

    def predict_with_model(self, query_text: str, model_name: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        保存されたモデルを読み込み、クエリとの類似度が高いドキュメントを返します。

        Args:
            query_text: 検索クエリ
            model_name: 使用するモデル名
            top_n: 返す結果の最大数

        Returns:
            類似度順にソートされた結果のリスト。各要素は {'similarity': float, 'text': str} の形式
        """
        if not self.model_manager.model_exists(model_name):
            self.logger.warning(f"Model '{model_name}' not found.")
            return []

        try:
            # モデルの読み込み
            vectorizer, tfidf_matrix, df = self.model_manager.load_model(model_name)

            # クエリの前処理とベクトル化
            processed_query = self.text_processor.prepare_corpus([query_text])
            if not processed_query:
                self.logger.warning("Query text became empty after preprocessing")
                return []

            query_vector = vectorizer.transform(processed_query)

            # 類似度計算
            similarities = (query_vector @ tfidf_matrix.T).toarray().ravel()

            # 類似度が高い順にインデックスを取得
            top_indices = np.argsort(similarities)[-top_n:][::-1]

            results = []
            for idx in top_indices:
                similarity_score = float(similarities[idx])
                if similarity_score > 0:  # 類似度が0より大きいもののみ
                    results.append({
                        'similarity': similarity_score,
                        'text': df.iloc[idx]['text']
                    })

            self.logger.info(f"Found {len(results)} similar documents for query")
            return results

        except ModelNotFoundError:
            raise
        except Exception as e:
            error_msg = f"An unexpected error occurred during prediction with model '{model_name}': {str(e)}"
            self.logger.exception(error_msg)
            return []

    def needs_retrain(self, model_name: str, current_docs: int) -> bool:
        """
        ドキュメント数の変化率に基づき、モデルの再学習が必要か判定します。

        Args:
            model_name: モデル名
            current_docs: 現在のドキュメント数

        Returns:
            再学習が必要かどうか
        """
        metadata = self.model_manager.load_model_metadata(model_name)
        prev_docs = metadata.get('docs', 0)

        if prev_docs == 0:
            return True  # 既存モデルがない場合は常に再学習

        delta = current_docs - prev_docs
        return delta / prev_docs >= self.config.retrain_threshold_ratio

    def get_model_metadata(self, model_name: str) -> Dict[str, Any]:
        """
        モデルのメタデータを取得します。

        Args:
            model_name: モデル名

        Returns:
            メタデータ辞書
        """
        return self.model_manager.load_model_metadata(model_name)

    def delete_model(self, model_name: str) -> bool:
        """
        指定されたモデルを削除します。

        Args:
            model_name: モデル名

        Returns:
            削除に成功したかどうか
        """
        try:
            pkl_path, meta_path = self.model_manager.get_model_paths(model_name)

            deleted = False
            if pkl_path.exists():
                pkl_path.unlink()
                deleted = True
            if meta_path.exists():
                meta_path.unlink()
                deleted = True

            if deleted:
                self.logger.info(f"Model '{model_name}' deleted successfully")
            return deleted

        except Exception as e:
            self.logger.error(f"Failed to delete model '{model_name}': {e}")
            return False

    def list_models(self) -> List[str]:
        """
        保存されているモデル名のリストを返します。

        Returns:
            モデル名のリスト
        """
        try:
            model_files = list(self.config.models_dir.glob('*.pkl'))
            return [f.stem for f in model_files]
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []

# --- 後方互換性のための関数 ---

def train_and_save_model(texts: List[str], model_name: str) -> Tuple[bool, str]:
    """
    後方互換性のための関数。RAGServiceを使用します。
    """
    service = RAGService()
    return service.train_and_save_model(texts, model_name)

def predict_with_model(query_text: str, model_name: str, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    後方互換性のための関数。RAGServiceを使用します。
    """
    service = RAGService()
    return service.predict_with_model(query_text, model_name, top_n)

def needs_retrain(model_name: str, current_docs: int, threshold_ratio: float = 0.15) -> bool:
    """
    後方互換性のための関数。RAGServiceを使用します。
    """
    config = RAGConfig(retrain_threshold_ratio=threshold_ratio)
    service = RAGService(config)
    return service.needs_retrain(model_name, current_docs)

def load_model_metadata(model_name: str) -> Dict[str, Any]:
    """
    後方互換性のための関数。RAGServiceを使用します。
    """
    service = RAGService()
    return service.get_model_metadata(model_name)

# --- 公開するAPI ---

__all__ = [
    'RAGService',
    'RAGConfig',
    'TextProcessor',
    'ModelManager',
    'RAGError',
    'ModelNotFoundError',
    'DependencyError',
    'ConfigurationError',
    'train_and_save_model',
    'predict_with_model',
    'needs_retrain',
    'load_model_metadata',
]
