"""Similarity utilities (TF-IDF based) unified module.

Provides lightweight ad-hoc similarity scoring for short text lists without
requiring a persisted model file. Falls back to naive overlap scoring when
scikit-learn is unavailable or vectorization fails.

Usage:
    from src.similarity import tfidf_top_k
    results = tfidf_top_k(query, candidate_texts, top_k=5)
    # -> List[{'text': str, 'score': float}]

Design:
 - Internal in-memory cache keyed by hash of candidate corpus + params to avoid
   rebuilding the vectorizer each call within the process lifetime.
 - Does NOT mutate input. Thread-safe for read (simple dict cache without locks
   acceptable for this small scale; collisions benign => recomputation).
"""
from __future__ import annotations
import hashlib
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

try:  # optional dependency
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    _SK_AVAILABLE = True
except Exception:  # pragma: no cover
    _SK_AVAILABLE = False

_CACHE: Dict[str, Tuple['TfidfVectorizer', any, List[str]]] = {}


def _make_corpus_key(texts: List[str], max_features: int, ngram_range: Tuple[int,int]) -> str:
    h = hashlib.sha1()
    for t in texts:
        h.update(t.encode('utf-8'))
        h.update(b'\0')
    h.update(f"{max_features}-{ngram_range}".encode())
    return h.hexdigest()


def tfidf_top_k(query: str,
                candidates: List[str],
                top_k: int = 5,
                max_features: int = 4000,
                ngram_range: Tuple[int,int] = (1,2),
                min_score: float = 0.0) -> List[Dict]:
    """Return top_k similar candidate texts.

    Fallback: naive token overlap scoring if sklearn not available or fails.
    """
    if not query or not candidates:
        return []
    if _SK_AVAILABLE:
        try:
            key = _make_corpus_key(candidates, max_features, ngram_range)
            if key in _CACHE:
                vect, tfidf_mat, stored = _CACHE[key]
            else:
                vect = TfidfVectorizer(max_features=max_features, ngram_range=ngram_range)
                tfidf_mat = vect.fit_transform(candidates)
                stored = candidates
                _CACHE[key] = (vect, tfidf_mat, stored)
            q_vec = vect.transform([query])
            sims = (tfidf_mat @ q_vec.T).toarray().ravel()
            ranked = sorted(zip(stored, sims), key=lambda x: x[1], reverse=True)
            out = [ {'text': t, 'score': float(s)} for t,s in ranked if s >= min_score ]
            return out[:top_k]
        except Exception as e:  # pragma: no cover
            logger.warning(f"TF-IDF similarity failed, fallback used: {e}")
    # Fallback naive
    q_tokens = {tok for tok in query.split() if tok}
    scored = []
    for cand in candidates:
        c_tokens = set(cand.split())
        overlap = len(q_tokens & c_tokens)
        if overlap > 0:
            scored.append({'text': cand, 'score': float(overlap)})
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]

__all__ = [ 'tfidf_top_k' ]
